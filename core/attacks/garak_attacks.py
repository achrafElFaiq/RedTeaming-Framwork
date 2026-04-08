from core.runners.garak_runner import GarakRunner
from core.entities.attack_target import AttackTarget
from core.attacks.attack import Attack

class GarakAttack(Attack):

    def __init__(self, intent: str, config: dict = None):
        super().__init__(intent=intent, framework="garak", config=config)

    
    def execute(self, target: AttackTarget):
        runner = GarakRunner()
        runner.run(target, self)