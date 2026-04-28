"""
Campaign Loader
===============
Parse a YAML campaign file and return a ready-to-run CampaignConfig.

Attacks are defined in separate YAML files (the attack catalog)
and referenced by path in the campaign file.

Usage::

    from core.application.campaign_loader import load_campaign

    config = load_campaign("examples/campaign.yaml")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from core.application.campaign_config import CampaignConfig
from core.models.attack import Attack
from frameworks.garak.garak_attack import GarakAttack
from frameworks.pyrit.pyrit_attack import PyritAttack

logger = logging.getLogger(__name__)

# ── Public API ───────────────────────────────────────────────────

def load_campaign(yaml_path: str | Path) -> CampaignConfig:
    """Load a YAML campaign file and return a validated CampaignConfig.

    Each entry in the ``attacks`` list must be a file path (string)
    pointing to a standalone attack YAML file.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Campaign file not found: {path}")

    raw = _read_yaml(path)
    _validate_top_level_keys(raw, path)

    target_cfg = raw["target"]
    _validate_target(target_cfg, path)

    attacks_raw = raw.get("attacks") or []
    if not attacks_raw:
        raise ValueError(f"{path}: 'attacks' list must not be empty")

    attacks = tuple(
        _load_attack_from_file(entry, index, path)
        for index, entry in enumerate(attacks_raw)
    )

    campaign_meta = raw.get("campaign", {})
    use_case_doc = target_cfg.get("use_case_doc", "")

    logger.info(
        "Loaded campaign '%s' — %d attack(s) targeting '%s'",
        campaign_meta.get("name", path.stem),
        len(attacks),
        target_cfg["name"],
    )

    return CampaignConfig(
        campaign_name=campaign_meta.get("name", path.stem),
        target_name=target_cfg["name"],
        target_url=target_cfg["url"],
        use_case_doc_path=use_case_doc,
        active_attacks=attacks,
    )


def load_attack(yaml_path: str | Path) -> Attack:
    """Load a single attack from its own YAML file."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Attack file not found: {path}")
    entry = _read_yaml(path)
    return _build_attack(entry, 0, path)


# ── YAML reading ─────────────────────────────────────────────────

def _read_yaml(path: Path) -> dict:
    """Read and parse a YAML file, returning the top-level dict."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level, got {type(data).__name__}")
    return data


# ── Validation helpers ───────────────────────────────────────────

_REQUIRED_TOP_KEYS = {"target", "attacks"}
_VALID_TOP_KEYS = {"campaign", "target", "attacks"}

def _validate_top_level_keys(raw: dict, path: Path) -> None:
    missing = _REQUIRED_TOP_KEYS - raw.keys()
    if missing:
        raise ValueError(f"{path}: missing required top-level key(s): {', '.join(sorted(missing))}")
    unknown = set(raw.keys()) - _VALID_TOP_KEYS
    if unknown:
        raise ValueError(
            f"{path}: unknown top-level key(s): {', '.join(sorted(unknown))}. "
            f"Valid keys: {', '.join(sorted(_VALID_TOP_KEYS))}"
        )


def _validate_target(target_cfg: dict, path: Path) -> None:
    for key in ("name", "url"):
        if key not in target_cfg:
            raise ValueError(f"{path}: target.{key} is required")
    url = target_cfg["url"]
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"{path}: target.url must start with http:// or https://")


# ── Attack loading ───────────────────────────────────────────────

_VALID_FRAMEWORKS = {"pyrit", "garak"}

def _load_attack_from_file(ref: Any, index: int, campaign_path: Path) -> Attack:
    """Load an attack from an external YAML file referenced in the campaign."""
    if not isinstance(ref, str):
        raise ValueError(
            f"{campaign_path}: attacks[{index}] must be a file path (string), "
            f"got {type(ref).__name__}"
        )

    attack_path = Path(ref)
    if not attack_path.exists():
        attack_path = campaign_path.parent / ref
    if not attack_path.exists():
        raise FileNotFoundError(
            f"{campaign_path}: attacks[{index}] references '{ref}' — file not found. "
            f"Looked in: '{Path(ref).resolve()}' and '{(campaign_path.parent / ref).resolve()}'"
        )

    logger.debug("Loading attack[%d] from file: %s", index, attack_path)
    entry = _read_yaml(attack_path)
    return _build_attack(entry, index, attack_path)


# ── Attack builders ──────────────────────────────────────────────

def _build_attack(entry: dict[str, Any], index: int, path: Path) -> Attack:
    """Build a single Attack instance from a parsed YAML dict."""
    fw = entry.get("framework", "")
    if fw not in _VALID_FRAMEWORKS:
        raise ValueError(
            f"{path}: attacks[{index}].framework must be one of {sorted(_VALID_FRAMEWORKS)}, got '{fw}'"
        )
    intent = entry.get("intent", "")
    if not intent:
        raise ValueError(f"{path}: attacks[{index}].intent is required")

    if fw == "pyrit":
        return _build_pyrit_attack(entry, index, path)
    else:
        return _build_garak_attack(entry, index, path)


def _build_pyrit_attack(entry: dict[str, Any], index: int, path: Path) -> PyritAttack:
    """Build a PyritAttack from YAML fields."""
    orchestrator = entry.get("orchestrator", "")
    if not orchestrator:
        raise ValueError(f"{path}: attacks[{index}].orchestrator is required for pyrit attacks")

    objective = entry.get("objective", "")
    if not objective:
        raise ValueError(f"{path}: attacks[{index}].objective is required for pyrit attacks")

    config: dict[str, Any] = {
        "orchestrator": orchestrator,
        "objective": objective.strip(),
    }

    if "max_turns" in entry:
        config["max_turns"] = int(entry["max_turns"])

    if "prompts" in entry:
        prompts = entry["prompts"]
        if not isinstance(prompts, list) or not prompts:
            raise ValueError(f"{path}: attacks[{index}].prompts must be a non-empty list")
        config["prompts"] = prompts

    scoring = entry.get("scoring")
    if scoring:
        config["scoring_question"] = _build_scoring_question(scoring, index, path)

    return PyritAttack(intent=entry["intent"], config=config)


def _build_garak_attack(entry: dict[str, Any], index: int, path: Path) -> GarakAttack:
    """Build a GarakAttack from YAML fields."""
    probe = entry.get("probe", "")
    if not probe:
        raise ValueError(f"{path}: attacks[{index}].probe is required for garak attacks")

    config: dict[str, Any] = {"probe": probe}

    if "report_prefix" in entry:
        config["report_prefix"] = entry["report_prefix"]

    return GarakAttack(intent=entry["intent"], config=config)


def _build_scoring_question(scoring: dict[str, str], index: int, path: Path):
    """Build a TrueFalseQuestion from the YAML scoring block."""
    for key in ("true_description", "false_description", "category"):
        if key not in scoring:
            raise ValueError(f"{path}: attacks[{index}].scoring.{key} is required")

    from pyrit.score.true_false.self_ask_true_false_scorer import TrueFalseQuestion

    return TrueFalseQuestion(
        true_description=scoring["true_description"].strip(),
        false_description=scoring["false_description"].strip(),
        category=scoring["category"].strip(),
    )


__all__ = ["load_campaign", "load_attack"]
