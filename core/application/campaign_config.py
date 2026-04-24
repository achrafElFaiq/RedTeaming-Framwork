from dataclasses import dataclass
from pathlib import Path

from core.models.attack import Attack


@dataclass(frozen=True)
class CampaignConfig:
    target_name: str
    target_url: str
    use_case_doc_path: str
    active_attacks: tuple[Attack, ...]

    def __post_init__(self):
        if not self.target_name.strip():
            raise ValueError("Campaign target_name must not be empty")
        if not self.target_url.startswith(("http://", "https://")):
            raise ValueError("Campaign target_url must start with http:// or https://")
        if not self.use_case_doc_path:
            raise ValueError("Campaign use_case_doc_path must not be empty")
        if not Path(self.use_case_doc_path).exists():
            raise ValueError(f"Use case document not found: {self.use_case_doc_path}")
        if not self.active_attacks:
            raise ValueError("Campaign active_attacks must not be empty")


__all__ = ["CampaignConfig"]

