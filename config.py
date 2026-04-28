import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────
# .env loading — deferred, called explicitly before settings access
# ─────────────────────────────────────────────────────────────────
_env_loaded = False


def ensure_env_loaded() -> None:
	"""Load .env file from project root (idempotent, no-op if already loaded)."""
	global _env_loaded
	if not _env_loaded:
		load_dotenv(Path(__file__).resolve().parent / ".env")
		_env_loaded = True


# ─────────────────────────────────────────────────────────────────
# Settings dataclass
# ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RuntimeSettings:
	# ── PyRIT Attacker LLM ────────────────────────────────────
	pyrit_attacker_endpoint: str
	pyrit_attacker_model: str
	pyrit_attacker_api_key: str

	# ── PyRIT Scorer LLM ─────────────────────────────────────
	pyrit_scorer_endpoint: str
	pyrit_scorer_model: str
	pyrit_scorer_api_key: str

	# ── PyRIT Runtime ─────────────────────────────────────────
	pyrit_db_path: str
	pyrit_loop_shutdown_delay: float
	pyrit_dataset_max_concurrency: int

	# ── Target ────────────────────────────────────────────────
	default_target_url: str

	# ── Reports ───────────────────────────────────────────────
	json_reports_dir: str

	# ── Garak ─────────────────────────────────────────────────
	garak_reports_dir: str
	garak_config_path: str
	garak_request_timeout: int
	garak_default_report_prefix: str


# ─────────────────────────────────────────────────────────────────
# Env helpers
# ─────────────────────────────────────────────────────────────────

def _require_env(name: str) -> str:
	"""Require an environment variable, raise error if missing."""
	value = os.getenv(name)
	if value is None:
		raise ValueError(f"Missing required environment variable: {name}")
	return value


def _get_env(name: str, default: str) -> str:
	return os.getenv(name, default)


def _get_float_env(name: str, default: float) -> float:
	value = os.getenv(name)
	if value is None:
		return default
	return float(value)


def _get_int_env(name: str, default: int) -> int:
	value = os.getenv(name)
	if value is None:
		return default
	return int(value)


# ─────────────────────────────────────────────────────────────────
# Settings builder — called lazily, NOT at import time
# ─────────────────────────────────────────────────────────────────

def get_runtime_settings(frameworks: set[str] | None = None) -> RuntimeSettings:
	"""Build RuntimeSettings from .env.

	Parameters
	----------
	frameworks : set[str] | None
		If provided, only validate env vars needed by those frameworks.
		Example: {"pyrit"}, {"garak"}, {"pyrit", "garak"}.
		If None, all vars are required (backward compat).
	"""
	ensure_env_loaded()

	need_pyrit = frameworks is None or "pyrit" in frameworks
	need_garak = frameworks is None or "garak" in frameworks

	# ── PyRIT vars: required only if pyrit is used ────────────
	if need_pyrit:
		pyrit_attacker_endpoint = _require_env("PYRIT_ATTACKER_ENDPOINT")
		pyrit_attacker_model = _require_env("PYRIT_ATTACKER_MODEL")
		pyrit_attacker_api_key = _require_env("PYRIT_ATTACKER_API_KEY")
		pyrit_scorer_endpoint = _require_env("PYRIT_SCORER_ENDPOINT")
		pyrit_scorer_model = _require_env("PYRIT_SCORER_MODEL")
		pyrit_scorer_api_key = _require_env("PYRIT_SCORER_API_KEY")
		pyrit_db_path = _require_env("PYRIT_DB_PATH")
	else:
		pyrit_attacker_endpoint = _get_env("PYRIT_ATTACKER_ENDPOINT", "")
		pyrit_attacker_model = _get_env("PYRIT_ATTACKER_MODEL", "")
		pyrit_attacker_api_key = _get_env("PYRIT_ATTACKER_API_KEY", "")
		pyrit_scorer_endpoint = _get_env("PYRIT_SCORER_ENDPOINT", "")
		pyrit_scorer_model = _get_env("PYRIT_SCORER_MODEL", "")
		pyrit_scorer_api_key = _get_env("PYRIT_SCORER_API_KEY", "")
		pyrit_db_path = _get_env("PYRIT_DB_PATH", "")

	# ── Garak vars: required only if garak is used ────────────
	if need_garak:
		garak_reports_dir = _require_env("GARAK_REPORTS_DIR")
		garak_config_path = _require_env("GARAK_CONFIG_PATH")
	else:
		garak_reports_dir = _get_env("GARAK_REPORTS_DIR", "")
		garak_config_path = _get_env("GARAK_CONFIG_PATH", "")

	# ── Always required ───────────────────────────────────────
	default_target_url = _require_env("DEFAULT_TARGET_URL")
	json_reports_dir = _require_env("JSON_REPORTS_DIR")

	# ── Technical vars with sensible defaults ─────────────────
	pyrit_loop_shutdown_delay = _get_float_env("PYRIT_LOOP_SHUTDOWN_DELAY", 0.3)
	pyrit_dataset_max_concurrency = _get_int_env("PYRIT_DATASET_MAX_CONCURRENCY", 5)
	garak_request_timeout = _get_int_env("GARAK_REQUEST_TIMEOUT", 60)
	garak_default_report_prefix = _get_env("GARAK_DEFAULT_REPORT_PREFIX", "reports/run")

	return RuntimeSettings(
		pyrit_attacker_endpoint=pyrit_attacker_endpoint,
		pyrit_attacker_model=pyrit_attacker_model,
		pyrit_attacker_api_key=pyrit_attacker_api_key,
		pyrit_scorer_endpoint=pyrit_scorer_endpoint,
		pyrit_scorer_model=pyrit_scorer_model,
		pyrit_scorer_api_key=pyrit_scorer_api_key,
		pyrit_db_path=pyrit_db_path,
		pyrit_loop_shutdown_delay=pyrit_loop_shutdown_delay,
		pyrit_dataset_max_concurrency=pyrit_dataset_max_concurrency,
		default_target_url=default_target_url,
		json_reports_dir=json_reports_dir,
		garak_reports_dir=garak_reports_dir,
		garak_config_path=garak_config_path,
		garak_request_timeout=garak_request_timeout,
		garak_default_report_prefix=garak_default_report_prefix,
	)


# ─────────────────────────────────────────────────────────────────
# PyRIT config helpers (called lazily by runners)
# ─────────────────────────────────────────────────────────────────

def build_pyrit_attacker_config() -> dict[str, str]:
	settings = get_runtime_settings(frameworks={"pyrit"})
	return {
		"attacker_endpoint": settings.pyrit_attacker_endpoint,
		"attacker_model": settings.pyrit_attacker_model,
		"attacker_api_key": settings.pyrit_attacker_api_key,
	}


def build_pyrit_scorer_config() -> dict[str, str]:
	settings = get_runtime_settings(frameworks={"pyrit"})
	return {
		"scorer_endpoint": settings.pyrit_scorer_endpoint,
		"scorer_model": settings.pyrit_scorer_model,
		"scorer_api_key": settings.pyrit_scorer_api_key,
	}


def resolve_pyrit_attacker_config(attack_config: Mapping[str, str] | None = None) -> dict[str, str]:
	resolved_config = build_pyrit_attacker_config()
	if not attack_config:
		return resolved_config

	for key in ("attacker_endpoint", "attacker_model", "attacker_api_key"):
		value = attack_config.get(key)
		if value:
			resolved_config[key] = value

	return resolved_config


def pyrit_attacker_config(attack_config: Mapping[str, str] | None = None) -> dict[str, str]:
	return resolve_pyrit_attacker_config(attack_config)


__all__ = [
	"RuntimeSettings",
	"ensure_env_loaded",
	"get_runtime_settings",
	"build_pyrit_attacker_config",
	"build_pyrit_scorer_config",
	"resolve_pyrit_attacker_config",
	"pyrit_attacker_config",
]
