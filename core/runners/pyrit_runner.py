import asyncio
from pyrit.executor.attack.multi_turn.red_teaming import RedTeamingAttack
from pyrit.executor.attack.core.attack_config import AttackAdversarialConfig
from pyrit.prompt_target.openai.openai_chat_target import OpenAIChatTarget
from core.entities.attack_target import AttackTarget
from core.attacks.attack import Attack
from core.runners.runner import Runner
from core.adapters.pyrit_adapter import PyritAdapter
from pyrit.memory.central_memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.executor.attack.core.attack_config import AttackAdversarialConfig, AttackScoringConfig
from pyrit.score.true_false.self_ask_true_false_scorer import SelfAskTrueFalseScorer

class PyritRunner(Runner):

    def run(self, target: AttackTarget, attack: Attack) -> any:
        CentralMemory.set_memory_instance(SQLiteMemory())
        return asyncio.run(self._run_async(target, attack))

    async def _run_async(self, target: AttackTarget, attack: Attack) -> any:
        

        print("[PyritRunner] Wrapping target with PyRIT adapter...")
        objective_target = PyritAdapter().wrap(target)

        print("[PyritRunner] Setting up attacker LLM and scoring configuration...")
        attacker_llm = OpenAIChatTarget(
            endpoint=attack.config.get("attacker_endpoint"),
            model_name=attack.config.get("attacker_model"),
            api_key=attack.config.get("attacker_api_key")
            #extra_body_parameters={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
        )


        print("[PyritRunner] Configuring adversarial attack and scorer...")
        adversarial_config = AttackAdversarialConfig(
            target=attacker_llm,
            system_prompt_path=attack.config.get("strategy_path", None),
        )

        print("[PyritRunner] Initializing scorer...")

        # scorer uses same attacker LLM to judge if objective was achieved
        scorer = SelfAskTrueFalseScorer(
            chat_target=attacker_llm,
            true_false_question=attack.config.get("scoring_question"),
        )

        print("[PyritRunner] Setting up attack scoring configuration...")
        scoring_config = AttackScoringConfig(
            objective_scorer=scorer
        )

        print("[PyritRunner] Initializing Red Teaming attack...")

        red_team = RedTeamingAttack(
            objective_target=objective_target,
            attack_adversarial_config=adversarial_config,
            attack_scoring_config=scoring_config,
            max_turns=attack.config.get("max_turns", 5),
        )

        print("[PyritRunner] Executing Red Teaming attack...")

        result = await red_team.execute_async(
            objective=attack.config.get("objective")
        )
        
        print("[PyritRunner] Attack execution completed. Result:")

        return result