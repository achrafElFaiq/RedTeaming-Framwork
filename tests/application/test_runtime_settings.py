import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import build_pyrit_attacker_config, get_runtime_settings, resolve_pyrit_attacker_config


# Minimal env vars always required
_BASE_ENV = {
    "DEFAULT_TARGET_URL": "http://localhost:8000/api/chat",
    "JSON_REPORTS_DIR": "reports",
}

# PyRIT-specific env vars
_PYRIT_ENV = {
    "PYRIT_ATTACKER_ENDPOINT": "http://127.0.0.1:11434/v1",
    "PYRIT_ATTACKER_MODEL": "gemma4:e4b",
    "PYRIT_ATTACKER_API_KEY": "ollama",
    "PYRIT_SCORER_ENDPOINT": "http://127.0.0.1:11434/v1",
    "PYRIT_SCORER_MODEL": "gemma4:e4b",
    "PYRIT_SCORER_API_KEY": "ollama",
    "PYRIT_DB_PATH": "/tmp/pyrit.db",
}

# Garak-specific env vars
_GARAK_ENV = {
    "GARAK_REPORTS_DIR": "/tmp/garak",
    "GARAK_CONFIG_PATH": "configs/garak_config.json",
}

# All env vars combined
_FULL_ENV = {**_BASE_ENV, **_PYRIT_ENV, **_GARAK_ENV}


class RuntimeSettingsTests(unittest.TestCase):
    def test_runtime_settings_raise_when_env_vars_are_missing(self):
        """Calling get_runtime_settings() with no env and no framework filter should crash."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing required environment variable"):
                get_runtime_settings()

    def test_pyrit_only_campaign_does_not_require_garak_vars(self):
        """A PyRIT-only campaign should NOT require GARAK_ vars."""
        env = {**_BASE_ENV, **_PYRIT_ENV}
        with patch.dict(os.environ, env, clear=True):
            settings = get_runtime_settings(frameworks={"pyrit"})
        self.assertEqual(settings.pyrit_attacker_endpoint, "http://127.0.0.1:11434/v1")
        self.assertEqual(settings.garak_reports_dir, "")  # empty default, not required

    def test_garak_only_campaign_does_not_require_pyrit_vars(self):
        """A Garak-only campaign should NOT require PYRIT_ vars."""
        env = {**_BASE_ENV, **_GARAK_ENV}
        with patch.dict(os.environ, env, clear=True):
            settings = get_runtime_settings(frameworks={"garak"})
        self.assertEqual(settings.garak_reports_dir, "/tmp/garak")
        self.assertEqual(settings.pyrit_attacker_endpoint, "")  # empty default, not required

    def test_pyrit_only_campaign_raises_if_pyrit_vars_missing(self):
        """A PyRIT campaign should fail if PYRIT_ vars are missing."""
        with patch.dict(os.environ, {**_BASE_ENV, **_GARAK_ENV}, clear=True):
            with self.assertRaisesRegex(ValueError, "PYRIT_ATTACKER_ENDPOINT"):
                get_runtime_settings(frameworks={"pyrit"})

    def test_garak_only_campaign_raises_if_garak_vars_missing(self):
        """A Garak campaign should fail if GARAK_ vars are missing."""
        with patch.dict(os.environ, {**_BASE_ENV, **_PYRIT_ENV}, clear=True):
            with self.assertRaisesRegex(ValueError, "GARAK_REPORTS_DIR"):
                get_runtime_settings(frameworks={"garak"})

    def test_technical_vars_have_sensible_defaults(self):
        """PYRIT_LOOP_SHUTDOWN_DELAY, PYRIT_DATASET_MAX_CONCURRENCY, GARAK_REQUEST_TIMEOUT
        should use defaults when not explicitly set."""
        with patch.dict(os.environ, _FULL_ENV, clear=True):
            settings = get_runtime_settings()
        self.assertEqual(settings.pyrit_loop_shutdown_delay, 0.3)
        self.assertEqual(settings.pyrit_dataset_max_concurrency, 5)
        self.assertEqual(settings.garak_request_timeout, 60)
        self.assertEqual(settings.garak_default_report_prefix, "reports/run")

    def test_technical_vars_can_be_overridden(self):
        """Technical defaults can be overridden via env vars."""
        env = {**_FULL_ENV, "PYRIT_LOOP_SHUTDOWN_DELAY": "1.5", "GARAK_REQUEST_TIMEOUT": "90"}
        with patch.dict(os.environ, env, clear=True):
            settings = get_runtime_settings()
        self.assertEqual(settings.pyrit_loop_shutdown_delay, 1.5)
        self.assertEqual(settings.garak_request_timeout, 90)

    def test_runtime_settings_load_all_values(self):
        env = {
            **_FULL_ENV,
            "PYRIT_ATTACKER_ENDPOINT": "https://llm.example.test/v1",
            "PYRIT_ATTACKER_MODEL": "gpt-test",
            "PYRIT_ATTACKER_API_KEY": "secret",
            "PYRIT_SCORER_ENDPOINT": "https://scorer.example.test/v1",
            "PYRIT_SCORER_MODEL": "scorer-model",
            "PYRIT_SCORER_API_KEY": "scorer-secret",
            "PYRIT_DB_PATH": "/tmp/pyrit-test.db",
            "DEFAULT_TARGET_URL": "https://target.example.test/api/chat",
            "JSON_REPORTS_DIR": "/tmp/json-reports",
            "GARAK_REPORTS_DIR": "/tmp/garak-runs",
            "GARAK_CONFIG_PATH": "/tmp/garak-config.json",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = get_runtime_settings()
            attacker_config = build_pyrit_attacker_config()

        self.assertEqual(settings.pyrit_attacker_endpoint, "https://llm.example.test/v1")
        self.assertEqual(settings.pyrit_attacker_model, "gpt-test")
        self.assertEqual(settings.pyrit_attacker_api_key, "secret")
        self.assertEqual(settings.pyrit_scorer_endpoint, "https://scorer.example.test/v1")
        self.assertEqual(settings.pyrit_scorer_model, "scorer-model")
        self.assertEqual(settings.pyrit_scorer_api_key, "scorer-secret")
        self.assertEqual(settings.pyrit_db_path, "/tmp/pyrit-test.db")
        self.assertEqual(settings.default_target_url, "https://target.example.test/api/chat")
        self.assertEqual(settings.json_reports_dir, "/tmp/json-reports")
        self.assertEqual(settings.garak_reports_dir, "/tmp/garak-runs")
        self.assertEqual(settings.garak_config_path, "/tmp/garak-config.json")
        self.assertEqual(
            attacker_config,
            {
                "attacker_endpoint": "https://llm.example.test/v1",
                "attacker_model": "gpt-test",
                "attacker_api_key": "secret",
            },
        )

    def test_resolve_pyrit_attacker_config_uses_env_values(self):
        with patch.dict(os.environ, _FULL_ENV, clear=True):
            attacker_config = resolve_pyrit_attacker_config()
        self.assertEqual(
            attacker_config,
            {
                "attacker_endpoint": "http://127.0.0.1:11434/v1",
                "attacker_model": "gemma4:e4b",
                "attacker_api_key": "ollama",
            },
        )

    def test_resolve_pyrit_attacker_config_accepts_overrides(self):
        with patch.dict(os.environ, _FULL_ENV, clear=True):
            attacker_config = resolve_pyrit_attacker_config(
                {
                    "attacker_endpoint": "https://override.example.test/v1",
                    "attacker_model": "override-model",
                    "attacker_api_key": "override-key",
                }
            )
        self.assertEqual(
            attacker_config,
            {
                "attacker_endpoint": "https://override.example.test/v1",
                "attacker_model": "override-model",
                "attacker_api_key": "override-key",
            },
        )


if __name__ == "__main__":
    unittest.main()

