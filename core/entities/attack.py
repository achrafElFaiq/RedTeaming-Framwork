

from abc import ABC, abstractmethod
from .attack_target import AttackTarget

class Attack(ABC):
    
    @abstractmethod
    def execute(self, target: AttackTarget):
        pass

