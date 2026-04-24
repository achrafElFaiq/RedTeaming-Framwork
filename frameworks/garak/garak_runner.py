import subprocess
import json
from pathlib import Path
from core.models.attack_target import AttackTarget
from core.contracts.runner import Runner
from core.models.attack import Attack
from core.models.attack_result import AttackResult
from .garak_normalizer import GarakNormalizer

from datetime import datetime


class GarakRunner(Runner):

    GARAK_REPORTS_DIR = Path.home() / ".local/share/garak/garak_runs/reports"
    CONFIG_PATH = Path("configs/garak_config.json")


    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        self._write_generator_config(target)
        self.GARAK_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_prefix = attack.config.get("report_prefix", "reports/run")
        result = subprocess.run(
            [
                "python", "-m", "garak",
                "--target_type", "rest",
                "--target_name", target.url,
                "--config", str(self.CONFIG_PATH),
                "--probes", attack.config.get("probe"),
                "--report_prefix", attack.config.get("report_prefix", "reports/run")
            ],
            capture_output=False,
            text=True
        )


        print(f"[GarakRunner] Reseting target memory.")
        target.reset_history()
        print(f"[GarakRunner] Reseting target memory. Done")

        # normalize and save
        # Garak puts the report in its own dir, extract just the stem
        stem = Path(report_prefix).name  # "blank" from "reports/blank"
        report_path = self.GARAK_REPORTS_DIR / f"{stem}.report.jsonl"

        if report_path.exists():
            normalizer = GarakNormalizer(
                report_path=str(report_path),
                target_url=target.url
            )
            attack_result = normalizer.normalize()
            Path("reports").mkdir(exist_ok=True)
            attack_result.save(
                f"reports/garak_{attack.intent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            print(f"[GarakRunner] Report saved.")
            return [attack_result]
        else:
            print(f"[GarakRunner] Report file not found at {report_path}")

        return []

    def _write_generator_config(self, target: AttackTarget) -> None:
        self.CONFIG_PATH.parent.mkdir(exist_ok=True)
        config = {
            "plugins": {
                "generators": {
                    "rest": {
                        "RestGenerator": {
                            "uri": target.url,
                            "req_template": '{"prompt": "$INPUT"}',
                            "response_json": True,
                            "response_json_field": "response",
                            "request_timeout": 60,
                            "headers": {
                                "Content-Type": "application/json"
                            }
                        }
                    }
                }
            }
        }
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

