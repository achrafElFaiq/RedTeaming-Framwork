# 1. Standard Python Libraries
import asyncio
from pathlib import Path
from datetime import datetime

# 2. Third-Party Libraries (PyRIT)
from pyrit.executor.attack import (
    AttackAdversarialConfig,
    AttackScoringConfig,
    ConsoleAttackResultPrinter,
    RedTeamingAttack,
    CrescendoAttack,
)

from pyrit.prompt_target.openai.openai_chat_target import OpenAIChatTarget
from pyrit.memory.central_memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.score.true_false.self_ask_true_false_scorer import SelfAskTrueFalseScorer

# 3. Internal/Custom Modules (Your Core logic)
from core.entities.attack_target import AttackTarget
from core.attacks.attack import Attack
from core.runners.runner import Runner
from core.adapters.pyrit_adapter import PyritAdapter

class PyritRunner(Runner):


    DB_PATH = str(Path.home() / "Library/Application Support/dbdata/pyrit.db")

    def run(self, target: AttackTarget, attack: Attack) -> any:
        CentralMemory.set_memory_instance(SQLiteMemory())
        return asyncio.run(self._run_async(target, attack))

    async def _run_async(self, target: AttackTarget, attack: Attack) -> any:
        

        print("[PyritRunner] Wrapping target with PyRIT adapter...")
        objective_target = PyritAdapter().wrap(target)


        # --- DEBUG CAPABILITIES ---
        print("\n" + "="*40)
        print("🔍 VERIFICATION TECHNIQUE")

        # 1. Vérifie la propriété publique
        print(f"Propriété .supports_multi_turn : {objective_target.supports_multi_turn}")

        # 2. Vérifie l'objet interne que PyRIT utilise pour la DB
        # PyRIT range le contenu de 'custom_capabilities' dans '_capabilities'
        caps = getattr(objective_target, '_capabilities', None)
        if caps:
            print(f"Capacité interne détectée : True (Multi-turn: {caps.supports_multi_turn})")
        else:
            print(" L'objet n'a pas chargé les capabilities !")
        print("="*40 + "\n")

        print("[PyritRunner] Setting up attacker LLM and scoring configuration...")
        attacker_llm = OpenAIChatTarget(
            endpoint=attack.config.get("attacker_endpoint"),
            model_name=attack.config.get("attacker_model"),
            api_key=attack.config.get("attacker_api_key")
            #extra_body_parameters={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
        )


        

        print("[PyritRunner] Initializing scorer...")

        # scorer uses same attacker LLM to judge if objective was achieved
        scorer = SelfAskTrueFalseScorer(
            chat_target=attacker_llm,
            true_false_question=attack.config.get("scoring_question"),
        )
        

        orchestrator_type = attack.config.get("orchestrator", "red_teaming")

        if orchestrator_type == "red_teaming":
            result = await self._run_red_teaming(attack, objective_target, attacker_llm, scorer)
        elif orchestrator_type == "crescendo":
            result = await self._run_crescendo(attack, objective_target, attacker_llm, scorer)
        else:
            raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")

        #await ConsoleAttackResultPrinter().print_result_async(result=result, include_auxiliary_scores=True)
        """
        print("[PyritRunner] Attack execution completed. Result:")
        print("main:", result.conversation_id)
        print("active:", result.get_active_conversation_ids())
        print("all:", result.get_all_conversation_ids())
        """

        # normalize and save
        from core.results.pyrit_normalizer import PyritNormalizer
        normalizer = PyritNormalizer(
            pyrit_result=result,
            db_path=self.DB_PATH,
            target_url=target.url,
            attack_name=attack.name
        )
        attack_result = normalizer.normalize()
        Path("reports").mkdir(exist_ok=True)
        attack_result.save(f"reports/pyrit_{attack.intent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print(f"[PyritRunner] Report saved.")

        return result
    

    async def _run_red_teaming(self, attack, objective_target, attacker_llm, scorer):
        """Ton orchestrateur existant — inchangé."""
        adversarial_config = AttackAdversarialConfig(
            target=attacker_llm,
            system_prompt_path=attack.config.get("strategy_path", None),
        )
        scoring_config = AttackScoringConfig(objective_scorer=scorer)
        red_team = RedTeamingAttack(
            objective_target=objective_target,
            attack_adversarial_config=adversarial_config,
            attack_scoring_config=scoring_config,
            max_turns=attack.config.get("max_turns", 5),
        )
        return await red_team.execute_async(objective=attack.config.get("objective"))


    async def _run_crescendo(self, attack, objective_target, attacker_llm, scorer):
        adversarial_config = AttackAdversarialConfig(
            target=attacker_llm,
            system_prompt_path=attack.config.get("strategy_path", None),
        )
        scoring_config = AttackScoringConfig(objective_scorer=scorer)
        
        crescendo = CrescendoAttack(
            objective_target=objective_target,
            attack_adversarial_config=adversarial_config,
            attack_scoring_config=scoring_config,
            max_turns=attack.config.get("max_turns", 6),
        )
        return await crescendo.execute_async(
            objective=attack.config.get("objective")
        )