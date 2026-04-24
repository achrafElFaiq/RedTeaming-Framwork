from abc import ABC, abstractmethod
from core.models.attack_result import AttackResult

class Normalizer(ABC):

    @abstractmethod
    def normalize(self) -> AttackResult:
        pass
