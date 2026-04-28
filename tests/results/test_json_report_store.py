import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models.attack_result import AttackResult
from core.results.json_report_store import JsonReportStore


class JsonReportStoreTests(unittest.TestCase):
    def test_store_uses_runtime_reports_dir_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"JSON_REPORTS_DIR": tmp_dir}, clear=True):
                store = JsonReportStore()

            self.assertEqual(store.reports_dir, Path(tmp_dir))

    def test_save_batch_writes_json_reports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JsonReportStore(tmp_dir)
            fixed_time = datetime(2026, 4, 27, 12, 30, 45)

            results = [
                AttackResult(
                    framework="pyrit",
                    attack_name="Crescendo Attack",
                    target_url="http://localhost:8000/api/chat",
                    timestamp=fixed_time,
                ),
                AttackResult(
                    framework="garak",
                    attack_name="Dataset / Prompt 01",
                    target_url="http://localhost:8000/api/chat",
                    timestamp=fixed_time,
                ),
            ]

            paths = store.save_batch(results)

            self.assertEqual(len(paths), 2)
            self.assertTrue(all(path.exists() for path in paths))
            self.assertEqual(paths[0].name, "pyrit_crescendo_attack_20260427_123045_00.json")
            self.assertEqual(paths[1].name, "garak_dataset_prompt_01_20260427_123045_01.json")

            first_payload = json.loads(paths[0].read_text(encoding="utf-8"))
            second_payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(first_payload["framework"], "pyrit")
            self.assertEqual(second_payload["framework"], "garak")


if __name__ == "__main__":
    unittest.main()

