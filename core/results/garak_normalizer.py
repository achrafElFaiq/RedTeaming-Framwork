import json
from datetime import datetime
from pathlib import Path
from core.results.normalizer import Normalizer
from core.results.attack_result import AttackResult, PromptResult

class GarakNormalizer(Normalizer):

    def __init__(self, report_path: str, target_url: str):
        self.report_path = Path(report_path)
        self.target_url = target_url

    def normalize(self) -> AttackResult:
        prompts = []
        attack_name = None
        timestamp = datetime.now()

        with open(self.report_path, "r") as f:
            for line in f:
                entry = json.loads(line.strip())
                if not entry:
                    continue

                # grab timestamp from init entry
                if entry.get("entry_type") == "init":
                    timestamp = datetime.fromisoformat(entry.get("start_time"))
                    continue

                # skip non-attempt entries
                if entry.get("entry_type") != "attempt":
                    continue

                attack_name = entry.get("probe_classname")
                prompt_text = entry["prompt"]["turns"][0]["content"]["text"]
                detector_results = entry.get("detector_results", {})

                for output in entry.get("outputs", []):
                    response_text = output.get("text", "")

                    # get score from detector results if available
                    scores = list(detector_results.values())
                    score = scores[0][0] if scores and scores[0] else None
                    passed = (score == 0.0) if score is not None else True

                    prompts.append(PromptResult(
                        prompt=prompt_text,
                        response=response_text,
                        passed=passed,
                        score=score,
                        detector=list(detector_results.keys())[0] if detector_results else None
                    ))

        return AttackResult(
            framework="garak",
            attack_name=attack_name or "unknown",
            target_url=self.target_url,
            timestamp=timestamp,
            prompts=prompts
        )