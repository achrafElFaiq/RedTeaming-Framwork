import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import build_pyrit_attacker_config, get_runtime_settings, resolve_pyrit_attacker_config


class RuntimeSettingsTests(unittest.TestCase):
    def test_runtime_settings_use_project_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_runtime_settings()

        self.assertEqual(settings.pyrit_attacker_endpoint, "http://127.0.0.1:11434/v1")
        self.assertEqual(settings.pyrit_attacker_model, "gemma4:e4b")
        self.assertEqual(settings.pyrit_attacker_api_key, "ollama")
        self.assertEqual(settings.pyrit_db_path, str(Path.home() / "Library/Application Support/dbdata/pyrit.db"))
        self.assertEqual(settings.pyrit_loop_shutdown_delay, 0.3)
        self.assertEqual(settings.pyrit_dataset_max_concurrency, 5)
        self.assertEqual(settings.default_target_url, "http://localhost:8000/api/chat")
        self.assertEqual(settings.json_reports_dir, "reports")
        self.assertEqual(settings.garak_reports_dir, str(Path.home() / ".local/share/garak/garak_runs/reports"))
        self.assertEqual(settings.garak_config_path, "configs/garak_config.json")
        self.assertEqual(settings.garak_python_executable, sys.executable)
        self.assertEqual(settings.garak_request_timeout, 60)
        self.assertEqual(settings.garak_default_report_prefix, "reports/run")

    def test_runtime_settings_can_be_overridden_with_environment_variables(self):
        with patch.dict(
            os.environ,
            {
                "PYRIT_ATTACKER_ENDPOINT": "https://llm.example.test/v1",
                "PYRIT_ATTACKER_MODEL": "gpt-test",
                "PYRIT_ATTACKER_API_KEY": "secret",
                "PYRIT_DB_PATH": "/tmp/pyrit-test.db",
                "PYRIT_LOOP_SHUTDOWN_DELAY": "1.5",
                "PYRIT_DATASET_MAX_CONCURRENCY": "9",
                "DEFAULT_TARGET_URL": "https://target.example.test/api/chat",
                "JSON_REPORTS_DIR": "/tmp/json-reports",
                "GARAK_REPORTS_DIR": "/tmp/garak-runs",
                "GARAK_CONFIG_PATH": "/tmp/garak-config.json",
                "GARAK_PYTHON_EXECUTABLE": "/opt/custom/bin/python",
                "GARAK_REQUEST_TIMEOUT": "90",
                "GARAK_DEFAULT_REPORT_PREFIX": "custom/reports/prefix",
            },
            clear=True,
        ):
            settings = get_runtime_settings()
            attacker_config = build_pyrit_attacker_config()

        self.assertEqual(settings.pyrit_attacker_endpoint, "https://llm.example.test/v1")
        self.assertEqual(settings.pyrit_attacker_model, "gpt-test")
        self.assertEqual(settings.pyrit_attacker_api_key, "secret")
        self.assertEqual(settings.pyrit_db_path, "/tmp/pyrit-test.db")
        self.assertEqual(settings.pyrit_loop_shutdown_delay, 1.5)
        self.assertEqual(settings.pyrit_dataset_max_concurrency, 9)
        self.assertEqual(settings.default_target_url, "https://target.example.test/api/chat")
        self.assertEqual(settings.json_reports_dir, "/tmp/json-reports")
        self.assertEqual(settings.garak_reports_dir, "/tmp/garak-runs")
        self.assertEqual(settings.garak_config_path, "/tmp/garak-config.json")
        self.assertEqual(settings.garak_python_executable, "/opt/custom/bin/python")
        self.assertEqual(settings.garak_request_timeout, 90)
        self.assertEqual(settings.garak_default_report_prefix, "custom/reports/prefix")
        self.assertEqual(
            attacker_config,
            {
                "attacker_endpoint": "https://llm.example.test/v1",
                "attacker_model": "gpt-test",
                "attacker_api_key": "secret",
            },
        )

    def test_resolve_pyrit_attacker_config_uses_global_runtime_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            attacker_config = resolve_pyrit_attacker_config()

        self.assertEqual(
            attacker_config,
            {
                "attacker_endpoint": "http://127.0.0.1:11434/v1",
                "attacker_model": "gemma4:e4b",
                "attacker_api_key": "ollama",
            },
        )

    def test_resolve_pyrit_attacker_config_accepts_legacy_attack_overrides(self):
        with patch.dict(os.environ, {}, clear=True):
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

