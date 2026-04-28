import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

# Auto-load .env from project root (no-op if file absent)
load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class RuntimeSettings:
	# ── PyRIT Attacker LLM ────────────────────────────────────
	pyrit_attacker_endpoint: str
	pyrit_attacker_model: str
	pyrit_attacker_api_key: str
	# ── PyRIT Scorer LLM (falls back to attacker if not set) ──
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
	garak_python_executable: str
	garak_request_timeout: int
	garak_default_report_prefix: str


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


def get_runtime_settings() -> RuntimeSettings:
	attacker_endpoint = os.getenv("PYRIT_ATTACKER_ENDPOINT", "http://127.0.0.1:11434/v1")
	attacker_model = os.getenv("PYRIT_ATTACKER_MODEL", "gemma4:e4b")
	attacker_api_key = os.getenv("PYRIT_ATTACKER_API_KEY", "ollama")

	return RuntimeSettings(
		pyrit_attacker_endpoint=attacker_endpoint,
		pyrit_attacker_model=attacker_model,
		pyrit_attacker_api_key=attacker_api_key,
		# Scorer defaults to attacker if not explicitly set
		pyrit_scorer_endpoint=os.getenv("PYRIT_SCORER_ENDPOINT", attacker_endpoint),
		pyrit_scorer_model=os.getenv("PYRIT_SCORER_MODEL", attacker_model),
		pyrit_scorer_api_key=os.getenv("PYRIT_SCORER_API_KEY", attacker_api_key),
		pyrit_db_path=os.getenv(
			"PYRIT_DB_PATH",
			str(Path.home() / "Library/Application Support/dbdata/pyrit.db"),
		),
		pyrit_loop_shutdown_delay=_get_float_env("PYRIT_LOOP_SHUTDOWN_DELAY", 0.3),
		pyrit_dataset_max_concurrency=_get_int_env("PYRIT_DATASET_MAX_CONCURRENCY", 5),
		default_target_url=os.getenv("DEFAULT_TARGET_URL", "http://localhost:8000/api/chat"),
		json_reports_dir=os.getenv("JSON_REPORTS_DIR", "reports"),
		garak_reports_dir=os.getenv(
			"GARAK_REPORTS_DIR",
			str(Path.home() / ".local/share/garak/garak_runs/reports"),
		),
		garak_config_path=os.getenv("GARAK_CONFIG_PATH", "configs/garak_config.json"),
		garak_python_executable=os.getenv("GARAK_PYTHON_EXECUTABLE", sys.executable),
		garak_request_timeout=_get_int_env("GARAK_REQUEST_TIMEOUT", 60),
		garak_default_report_prefix=os.getenv("GARAK_DEFAULT_REPORT_PREFIX", "reports/run"),
	)


def build_pyrit_attacker_config() -> dict[str, str]:
	settings = get_runtime_settings()
	return {
		"attacker_endpoint": settings.pyrit_attacker_endpoint,
		"attacker_model": settings.pyrit_attacker_model,
		"attacker_api_key": settings.pyrit_attacker_api_key,
	}


def build_pyrit_scorer_config() -> dict[str, str]:
	settings = get_runtime_settings()
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


RUNTIME_SETTINGS = get_runtime_settings()
PYRIT_ATTACKER_CONFIG = build_pyrit_attacker_config()
PYRIT_SCORER_CONFIG = build_pyrit_scorer_config()
DEFAULT_TARGET_URL = RUNTIME_SETTINGS.default_target_url


__all__ = [
	"RuntimeSettings",
	"RUNTIME_SETTINGS",
	"DEFAULT_TARGET_URL",
	"PYRIT_ATTACKER_CONFIG",
	"PYRIT_SCORER_CONFIG",
	"get_runtime_settings",
	"build_pyrit_attacker_config",
	"build_pyrit_scorer_config",
	"resolve_pyrit_attacker_config",
	"pyrit_attacker_config",
]

