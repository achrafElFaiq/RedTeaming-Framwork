from abc import ABC, abstractmethod
from core.entities.attack_target import AttackTarget

class Attack(ABC): 
    def __init__(self, intent: str, framework: str, config: dict = None):
        self.intent = intent
        self.framework = framework
        self.config = config or {}
        self.name = f"{self.framework} - {self.intent}"

    @abstractmethod
    def execute(self, target: AttackTarget):
        pass