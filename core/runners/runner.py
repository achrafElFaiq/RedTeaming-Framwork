from abc import ABC, abstractmethod
from core.entities.attack_target import AttackTarget


class Runner(ABC):
    """Abstract base class for attack runners."""

    @abstractmethod
    def run(self, target: AttackTarget, config: dict) -> any:
        pass