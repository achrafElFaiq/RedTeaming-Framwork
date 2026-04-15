from abc import ABC, abstractmethod
from core.results.attack_result import AttackResult

class Normalizer(ABC):
    
    @abstractmethod
    def normalize(self) -> AttackResult:
        pass