from abc import ABC, abstractmethod

from core.models.attack import Attack
from core.models.attack_result import AttackResult
from core.models.attack_target import AttackTarget


class Runner(ABC):
    """Abstract base class for attack runners."""

    @abstractmethod
    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        pass

