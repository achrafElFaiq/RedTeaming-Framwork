from pathlib import Path

from core.application.campaign_config import CampaignConfig
from core.models.attack_target import AttackTarget
from core.orchestration.attack_orchestrator import AttackOrchestrator
from orange_use_cases import attack_catalog

TARGET_NAME = "SMOKE TEST SIA"
TARGET_URL = "http://localhost:8000/api/chat"
USE_CASE_DOC_PATH = str(
    Path(__file__).resolve().parents[1]
    / "orange_use_cases"
    / "use_cases_orange_description"
    / "usecase1.md"
)

SMOKE_ATTACKS = (
    attack_catalog.pyrit_dataset_scoring_scan_fr,
    attack_catalog.pyrit_redteaming_discount_fr,
    attack_catalog.pyrit_discount_retention_fr,
)

DEFAULT_SMOKE_CAMPAIGN = CampaignConfig(
    target_name=TARGET_NAME,
    target_url=TARGET_URL,
    use_case_doc_path=USE_CASE_DOC_PATH,
    active_attacks=SMOKE_ATTACKS,
)


def run_smoke_campaign(config: CampaignConfig = DEFAULT_SMOKE_CAMPAIGN) -> AttackOrchestrator:
    target = AttackTarget(config.target_name, config.target_url)
    orchestrator = AttackOrchestrator(
        target=target,
        use_case_doc_path=config.use_case_doc_path,
    )

    for attack in config.active_attacks:
        orchestrator.add_attack(attack)

    orchestrator.execute_attacks()
    return orchestrator


if __name__ == "__main__":
    orchestrator = run_smoke_campaign()
    print(orchestrator.summary())

