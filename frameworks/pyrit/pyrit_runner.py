# 1. Standard Python Libraries
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any

# 2. Third-Party Libraries (PyRIT)
from pyrit.executor.attack import (
    AttackAdversarialConfig,
    AttackScoringConfig,
    ConsoleAttackResultPrinter,
    RedTeamingAttack,
    CrescendoAttack,
    MultiPromptSendingAttack,
    MultiPromptSendingAttackParameters,
    AttackScoringConfig,
)
from core.utils import slugify

from pyrit.executor.attack import (
            MultiPromptSendingAttack,
            MultiPromptSendingAttackParameters,
            AttackScoringConfig,
        )

from pyrit.models import SeedDataset, SeedPrompt, Message, MessagePiece

from pyrit.prompt_target.openai.openai_chat_target import OpenAIChatTarget
from pyrit.memory.central_memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.score.true_false.self_ask_true_false_scorer import SelfAskTrueFalseScorer

# 3. Internal/Custom Modules (Your Core logic)
from core.models.attack_target import AttackTarget
from core.models.attack import Attack
from core.models.attack_result import AttackResult
from core.contracts.runner import Runner
from .pyrit_adapter import PyritAdapter

class PyritRunner(Runner):


    DB_PATH = str(Path.home() / "Library/Application Support/dbdata/pyrit.db")

    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        CentralMemory.set_memory_instance(SQLiteMemory())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._run_async(target, attack))
        finally:
            loop.run_until_complete(asyncio.sleep(0.3))
            loop.close()

    async def _run_async(self, target: AttackTarget, attack: Attack) -> Any:

        print("\n" + "="*40)
        print(f"[PyritRunner] Starting PyRIT attack '{attack.name}' execution...")
        print("="*40 + "\n")

        print("[PyritRunner] Wrapping target with PyRIT adapter...")
        objective_target = PyritAdapter().wrap(target)

        # --- DEBUG CAPABILITIES ---
        print(f"[PyritRunner] Verification technique: .supports_multi_turn = {objective_target.supports_multi_turn}")
        caps = getattr(objective_target, '_capabilities', None)
        if caps:
            print(f"[PyritRunner] Capacité interne détectée : True (Multi-turn: {caps.supports_multi_turn})")
        else:
            print("[PyritRunner] L'objet n'a pas chargé les capabilities !")

        orchestrator_type = attack.config.get("orchestrator", "red_teaming")
        print(f"[PyritRunner] Orchestrator type: {orchestrator_type}")

        if orchestrator_type == "dataset":
            print("[PyritRunner] Dataset mode — no attacker LLM needed.")
            print("[PyritRunner] Initializing scorer with dedicated LLM...")
            scorer = SelfAskTrueFalseScorer(
                chat_target=OpenAIChatTarget(
                    endpoint=attack.config.get("attacker_endpoint"),
                    model_name=attack.config.get("attacker_model"),
                    api_key=attack.config.get("attacker_api_key"),
                ),
                true_false_question=attack.config.get("scoring_question"),
            )
            prompts = attack.config.get("prompts", [])
            print(f"[PyritRunner] Dataset loaded: {len(prompts)} prompts.")
            result = await self._run_dataset(attack, objective_target, scorer)

        else:
            print("[PyritRunner] Setting up attacker LLM and scoring configuration...")
            attacker_llm = OpenAIChatTarget(
                endpoint=attack.config.get("attacker_endpoint"),
                model_name=attack.config.get("attacker_model"),
                api_key=attack.config.get("attacker_api_key"),
                # extra_body_parameters={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
            )

            print("[PyritRunner] Initializing scorer...")
            scorer = SelfAskTrueFalseScorer(
                chat_target=attacker_llm,
                true_false_question=attack.config.get("scoring_question"),
            )

            if orchestrator_type == "red_teaming":
                print("[PyritRunner] Running RedTeaming attack...")
                result = await self._run_red_teaming(attack, objective_target, attacker_llm, scorer)
            elif orchestrator_type == "crescendo":
                print("[PyritRunner] Running Crescendo attack...")
                result = await self._run_crescendo(attack, objective_target, attacker_llm, scorer)
            else:
                raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")

        # DEBUG
        from pyrit.executor.attack.core.attack_executor import AttackExecutorResult

        if not isinstance(result, AttackExecutorResult):
            memory = CentralMemory.get_memory_instance()
            pieces = memory.get_message_pieces(conversation_id=result.conversation_id)
            print(f"[DEBUG] {len(pieces)} pieces dans la conversation principale")
            for p in pieces:
                print(f"  role={p.role} | seq={p.sequence} | value={p.original_value[:60]}")
            print(f"[DEBUG] outcome: {result.outcome}")
            print(f"[DEBUG] executed_turns: {result.executed_turns}")
            print(f"[DEBUG] last_score: {result.last_score}")
        else:
            print(f"[DEBUG] Dataset: {len(result.completed_results)} results")
            for i, r in enumerate(result.completed_results):
                print(f"  [{i}] outcome={r.outcome} | conv={r.conversation_id[:8]}")

        # normalize and save
        print("[PyritRunner] Normalizing and saving results...")
        from .pyrit_normalizer import PyritNormalizer
        from pyrit.executor.attack.core.attack_executor import AttackExecutorResult

        normalized_results: list[AttackResult] = []

        if isinstance(result, AttackExecutorResult):
            print(f"[PyritRunner] Dataset result: {len(result.completed_results)} completed, "
                  f"{len(result.incomplete_objectives)} failed.")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            intent_slug = slugify(attack.intent)

            for i, individual_result in enumerate(result.completed_results):
                # Nom unique par prompt — le prompt devient partie intégrante du nom
                prompt_preview = individual_result.objective[:60]
                unique_attack_name = f"{attack.name} | [{i + 1:02d}] {prompt_preview}"

                normalizer = PyritNormalizer(
                    pyrit_result=individual_result,
                    db_path=self.DB_PATH,
                    target_url=target.url,
                    attack_name=unique_attack_name,  # ← nom unique ici
                )
                attack_result = normalizer.normalize()
                normalized_results.append(attack_result)
                Path("reports").mkdir(exist_ok=True)

                prompt_slug = slugify(individual_result.objective)[:40]
                attack_result.save(
                    f"reports/pyrit_{orchestrator_type}_{intent_slug}_"
                    f"{timestamp}_{i:02d}_{prompt_slug}.json"
                )
                print(f"[PyritRunner] Report saved for prompt {i + 1}/{len(result.completed_results)}.")

        else:
            # Crescendo / RedTeaming — un seul AttackResult
            normalizer = PyritNormalizer(
                pyrit_result=result,
                db_path=self.DB_PATH,
                target_url=target.url,
                attack_name=attack.name,
            )
            attack_result = normalizer.normalize()
            normalized_results.append(attack_result)
            Path("reports").mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            intent_slug = slugify(attack.intent)
            attack_result.save(
                f"reports/pyrit_{orchestrator_type}_{intent_slug}_{timestamp}.json"
            )
            print(f"[PyritRunner] Report saved.")

        print(f"[PyritRunner] Reseting target memory.")
        target.reset_history()
        print(f"[PyritRunner] Reseting target memory. Done")

        print(f"[PyritRunner] Attack execution finished. Returning result.")
        return normalized_results


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

    async def _run_dataset(self, attack, objective_target, scorer):
        from pyrit.executor.attack import (
            PromptSendingAttack,
            AttackExecutor,
            AttackScoringConfig,
        )

        prompts = attack.config.get("prompts", [])
        if not prompts:
            raise ValueError("Dataset mode requires 'prompts' in attack config")

        scoring_config = AttackScoringConfig(objective_scorer=scorer)

        single_attack = PromptSendingAttack(
            objective_target=objective_target,
            attack_scoring_config=scoring_config,
        )

        executor = AttackExecutor(max_concurrency=5)

        print(f"[PyritRunner] Executing {len(prompts)} independent prompts in parallel (max 5 concurrent)...")

        return await executor.execute_multi_objective_attack_async(
            attack=single_attack,
            objectives=prompts,
        )
