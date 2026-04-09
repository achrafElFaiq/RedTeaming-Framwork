from core.attacks.attack import Attack
from core.entities.attack_target import AttackTarget
from core.runners.pyrit_runner import PyritRunner

class PyritAttack(Attack):
    
    def __init__(self, intent: str, config: dict = None):
        super().__init__(intent=intent, framework="pyrit", config=config)

    def execute(self, target: AttackTarget):
        runner = PyritRunner()
        runner.run(target, self)