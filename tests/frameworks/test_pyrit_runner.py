import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models.attack import Attack
from core.models.attack_target import AttackTarget
from frameworks.pyrit.pyrit_runner import PyritRunner


class DummyTarget(AttackTarget):
    def __init__(self):
        super().__init__("PyRIT test target", "http://localhost:8000/api/chat")


class DummyAttack(Attack):
    def __init__(self, config: dict | None = None):
        super().__init__(intent="test", framework="pyrit", config=config or {})

    def execute(self, target: AttackTarget):  # pragma: no cover - not used in this test
        raise NotImplementedError


class PyritRunnerTests(unittest.TestCase):
    def test_run_drains_pending_asyncio_tasks_before_closing_loop(self):
        runner = PyritRunner()
        target = DummyTarget()
        attack = DummyAttack()
        background_tasks = []

        async def fake_run_async(_target, _attack):
            async def delayed_cleanup():
                await asyncio.sleep(0.01)

            task = asyncio.create_task(delayed_cleanup())
            background_tasks.append(task)
            return []

        with patch.object(runner, "_run_async", fake_run_async):
            results = runner.run(target, attack)

        self.assertEqual(results, [])
        self.assertEqual(len(background_tasks), 1)
        self.assertTrue(background_tasks[0].done())
        self.assertFalse(background_tasks[0].cancelled())

    def test_build_dataset_attack_name_includes_index_and_prompt_preview(self):
        runner = PyritRunner()

        attack_name = runner._build_dataset_attack_name(
            "pyrit - dataset",
            "A" * 80,
            1,
        )

        self.assertEqual(attack_name, f"pyrit - dataset | [02] {'A' * 60}")

    def test_execute_orchestrator_dispatches_dataset_mode(self):
        runner = PyritRunner()
        attack = DummyAttack(
            {
                "orchestrator": "dataset",
                "prompts": ["one", "two"],
                "scoring_question": "safe?",
            }
        )

        async def run_test():
            with patch.object(runner, "_build_scorer_llm", return_value=object()), \
                 patch.object(runner, "_build_scorer", return_value="scorer") as scorer_mock, \
                 patch.object(runner, "_run_dataset", new_callable=AsyncMock, return_value=["dataset-result"]) as dataset_mock, \
                 patch("frameworks.pyrit.pyrit_runner.build_pyrit_scorer_config", return_value={"scorer_endpoint": "e", "scorer_model": "m", "scorer_api_key": "k"}):
                result = await runner._execute_orchestrator(attack, object(), {"attacker_endpoint": "e", "attacker_model": "m", "attacker_api_key": "k"})

            self.assertEqual(result, ["dataset-result"])
            scorer_mock.assert_called_once()
            dataset_mock.assert_called_once_with(attack, unittest.mock.ANY, "scorer")

        asyncio.run(run_test())

    def test_execute_orchestrator_rejects_unknown_mode(self):
        runner = PyritRunner()
        attack = DummyAttack({"orchestrator": "unknown"})

        async def run_test():
            with patch.object(runner, "_build_attacker_llm", return_value=object()), \
                 patch.object(runner, "_build_scorer_llm", return_value=object()), \
                 patch.object(runner, "_build_scorer", return_value="scorer"), \
                 patch("frameworks.pyrit.pyrit_runner.build_pyrit_scorer_config", return_value={"scorer_endpoint": "e", "scorer_model": "m", "scorer_api_key": "k"}):
                with self.assertRaisesRegex(ValueError, "Unknown orchestrator type"):
                    await runner._execute_orchestrator(
                        attack,
                        object(),
                        {"attacker_endpoint": "e", "attacker_model": "m", "attacker_api_key": "k"},
                    )

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()


