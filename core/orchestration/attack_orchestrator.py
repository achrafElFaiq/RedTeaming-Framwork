from core.models.attack_target import AttackTarget
from core.models.attack import Attack
from core.models.attack_result import AttackResult

class AttackOrchestrator:

    def __init__(self, target: AttackTarget, use_case_doc_path: str = None, attacks: list[Attack] = None):
        self.attacks = attacks or []
        self.target = target
        self.use_case_doc_path = use_case_doc_path
        self.results: list[AttackResult] = []
        self.technical_failures: list[dict[str, str]] = []

    def add_attack(self, attack: Attack):
        self.attacks.append(attack)

    @property
    def result_count(self) -> int:
        return len(self.results)

    @property
    def executed_attack_names(self) -> list[str]:
        return [attack.name for attack in self.attacks]

    @property
    def has_failures(self) -> bool:
        return any(self._result_has_failure(result) for result in self.results)

    @property
    def has_execution_errors(self) -> bool:
        return bool(self.technical_failures)

    def summary(self) -> dict[str, object]:
        failure_count = sum(1 for result in self.results if self._result_has_failure(result))
        return {
            "attack_count": len(self.attacks),
            "result_count": self.result_count,
            "failure_count": failure_count,
            "has_failures": failure_count > 0,
            "technical_failure_count": len(self.technical_failures),
            "has_execution_errors": self.has_execution_errors,
            "executed_attack_names": self.executed_attack_names,
            "technical_failures": self.technical_failures,
        }

    def execute_attacks(self) -> list[AttackResult]:
        self.results = []
        self.technical_failures = []
        for attack in self.attacks:
            try:
                self.results.extend(attack.execute(self.target))
            except Exception as exc:
                self._record_execution_error(attack, exc)
        return self.results

    @staticmethod
    def _result_has_failure(result: AttackResult) -> bool:
        if result.conversation is not None:
            return result.conversation.achieved
        if result.prompts:
            return any(not prompt.passed for prompt in result.prompts)
        return False

    def _record_execution_error(self, attack: Attack, exc: Exception) -> None:
        self.technical_failures.append(
            {
                "attack_name": attack.name,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )




