import subprocess
import json
from pathlib import Path
from core.entities.attack_target import AttackTarget
from core.runners.runner import Runner
from core.attacks.attack import Attack

class GarakRunner(Runner):
    
    GARAK_REPORTS_DIR = Path.home() / ".local/share/garak/garak_runs/reports"
    CONFIG_PATH = Path("configs/garak_config.json")

    def run(self, target: AttackTarget, attack: Attack) -> int:
        self._write_generator_config(target)
        self.GARAK_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
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
        return result.returncode

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