from core.entities.attack_target import AttackTarget
from core.attacks.garak_attacks import GarakAttack
from core.entities.attack_orchestrator import AttackOrchestrator

target = AttackTarget("CustomerBot", "http://localhost:8000/api/chat")
    
attack = GarakAttack(
    intent="jailbreak test",
    config={
        "probe": "dan.DanInTheWild",
        "report_prefix": "reports/dan_run"
    }
)

orchestrator = AttackOrchestrator(target=target)
orchestrator.add_attack(attack)
orchestrator.execute_attacks()