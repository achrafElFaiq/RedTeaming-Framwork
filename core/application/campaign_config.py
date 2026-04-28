from dataclasses import dataclass
from pathlib import Path

from core.models.attack import Attack


@dataclass(frozen=True)
class CampaignConfig:
    """
    Configuration object for an attack campaign.

    This structure defines what is required to execute a campaign:
    - `target_name`: human-readable name of the target
    - `target_url`: HTTP/HTTPS endpoint of the target under test
    - `active_attacks`: list of attacks to execute against the target
    - `use_case_doc_path`: optional path to a campaign tracking/use-case document
    """
    target_name: str
    target_url: str
    active_attacks: tuple[Attack, ...]
    campaign_name: str = ""
    use_case_doc_path: str = ""

    def __post_init__(self):
        if not self.target_name.strip():
            raise ValueError("Campaign target_name must not be empty")
        if not self.target_url.startswith(("http://", "https://")):
            raise ValueError("Campaign target_url must start with http:// or https://")
        if self.use_case_doc_path and not Path(self.use_case_doc_path).exists():
            raise ValueError(f"Use case document not found: {self.use_case_doc_path}")
        if not self.active_attacks:
            raise ValueError("Campaign active_attacks must not be empty")
