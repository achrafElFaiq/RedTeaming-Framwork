import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models.attack import Attack
from core.models.attack_result import AttackResult, PromptResult
from core.models.attack_target import AttackTarget
from core.orchestration.attack_orchestrator import AttackOrchestrator


class DummyAttack(Attack):
    def __init__(self, intent: str, results: list[AttackResult]):
        super().__init__(intent=intent, framework="dummy", config={})
        self._results = results
        self.executed_targets: list[AttackTarget] = []

    def execute(self, target: AttackTarget) -> list[AttackResult]:
        self.executed_targets.append(target)
        return self._results


class FailingAttack(Attack):
    def __init__(self, intent: str, error: Exception):
        super().__init__(intent=intent, framework="dummy", config={})
        self.error = error
        self.executed_targets: list[AttackTarget] = []

    def execute(self, target: AttackTarget) -> list[AttackResult]:
        self.executed_targets.append(target)
        raise self.error


class AttackOrchestratorTests(unittest.TestCase):
    def test_orchestrator_has_empty_state_by_default(self):
        target = AttackTarget("Test target", "http://localhost:8000/api/chat")
        orchestrator = AttackOrchestrator(target=target, use_case_doc_path="dummy.md")

        self.assertEqual(orchestrator.result_count, 0)
        self.assertEqual(orchestrator.executed_attack_names, [])
        self.assertFalse(orchestrator.has_failures)
        self.assertFalse(orchestrator.has_execution_errors)
        self.assertEqual(
            orchestrator.summary(),
            {
                "attack_count": 0,
                "result_count": 0,
                "failure_count": 0,
                "has_failures": False,
                "technical_failure_count": 0,
                "has_execution_errors": False,
                "executed_attack_names": [],
                "technical_failures": [],
            },
        )

    def test_execute_attacks_aggregates_normalized_results_in_order(self):
        target = AttackTarget("Test target", "http://localhost:8000/api/chat")
        orchestrator = AttackOrchestrator(target=target, use_case_doc_path="dummy.md")

        result_a = AttackResult(
            framework="dummy",
            attack_name="attack-a",
            target_url=target.url,
        )
        result_b = AttackResult(
            framework="dummy",
            attack_name="attack-b",
            target_url=target.url,
        )
        result_c = AttackResult(
            framework="dummy",
            attack_name="attack-c",
            target_url=target.url,
        )

        attack_a = DummyAttack("a", [result_a, result_b])
        attack_b = DummyAttack("b", [result_c])

        orchestrator.add_attack(attack_a)
        orchestrator.add_attack(attack_b)

        results = orchestrator.execute_attacks()

        self.assertEqual(results, [result_a, result_b, result_c])
        self.assertEqual(orchestrator.results, [result_a, result_b, result_c])
        self.assertEqual(orchestrator.result_count, 3)
        self.assertEqual(orchestrator.executed_attack_names, [attack_a.name, attack_b.name])
        self.assertFalse(orchestrator.has_failures)
        self.assertFalse(orchestrator.has_execution_errors)
        self.assertEqual(
            orchestrator.summary(),
            {
                "attack_count": 2,
                "result_count": 3,
                "failure_count": 0,
                "has_failures": False,
                "technical_failure_count": 0,
                "has_execution_errors": False,
                "executed_attack_names": [attack_a.name, attack_b.name],
                "technical_failures": [],
            },
        )
        self.assertEqual(attack_a.executed_targets, [target])
        self.assertEqual(attack_b.executed_targets, [target])

    def test_has_failures_detects_failed_prompt_results(self):
        target = AttackTarget("Test target", "http://localhost:8000/api/chat")
        orchestrator = AttackOrchestrator(target=target, use_case_doc_path="dummy.md")

        failed_result = AttackResult(
            framework="dummy",
            attack_name="attack-failed",
            target_url=target.url,
            prompts=[
                PromptResult(
                    prompt="prompt",
                    response="response",
                    passed=False,
                )
            ],
        )

        attack = DummyAttack("failed", [failed_result])
        orchestrator.add_attack(attack)

        orchestrator.execute_attacks()

        self.assertTrue(orchestrator.has_failures)
        self.assertEqual(orchestrator.summary()["failure_count"], 1)

    def test_execute_attacks_collects_technical_failures_and_continues(self):
        target = AttackTarget("Test target", "http://localhost:8000/api/chat")
        orchestrator = AttackOrchestrator(target=target, use_case_doc_path="dummy.md")

        success_result = AttackResult(
            framework="dummy",
            attack_name="attack-success",
            target_url=target.url,
        )

        failing_attack = FailingAttack("boom", RuntimeError("runner failed"))
        success_attack = DummyAttack("success", [success_result])

        orchestrator.add_attack(failing_attack)
        orchestrator.add_attack(success_attack)

        results = orchestrator.execute_attacks()

        self.assertEqual(results, [success_result])
        self.assertEqual(orchestrator.results, [success_result])
        self.assertTrue(orchestrator.has_execution_errors)
        self.assertEqual(orchestrator.summary()["technical_failure_count"], 1)
        self.assertEqual(
            orchestrator.technical_failures,
            [
                {
                    "attack_name": failing_attack.name,
                    "error_type": "RuntimeError",
                    "message": "runner failed",
                }
            ],
        )
        self.assertEqual(failing_attack.executed_targets, [target])
        self.assertEqual(success_attack.executed_targets, [target])


if __name__ == "__main__":
    unittest.main()


