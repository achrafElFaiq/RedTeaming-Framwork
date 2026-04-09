from abc import ABC, abstractmethod
from core.entities.attack_target import AttackTarget


class Adapter(ABC):
    """Abstract base class for attack adaptors. Takes an attackTarget and returns a format that can be used by the runner.
    the adapter takes the target and implments a new method that return the correct object that the runner must use
    
    """
    
    @abstractmethod
    def wrap(self) -> any:
        pass