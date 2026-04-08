from core.entities.attack_target import AttackTarget
from core.attacks.attack import Attack

class AttackOrchestrator:
    
    def __init__(self, target: AttackTarget, attacks: list[Attack] = None):
        self.attacks = attacks or []
        self.target = target

    
    def add_attack(self, attack: Attack):
        self.attacks.append(attack)

    def execute_attacks(self):
        for attack in self.attacks:
            attack.execute(self.target)



