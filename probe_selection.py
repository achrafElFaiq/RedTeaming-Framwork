import requests
import importlib
import pkgutil
import garak.probes
from garak.probes.base import Probe
from collections import defaultdict


# =========================================================
# Ollama wrapper
# =========================================================
class OllamaLLM:
    def __init__(self, model="gemma4:e4b"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/chat"

    def chat(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        r = requests.post(self.url, json=payload)
        if r.status_code != 200:
            raise Exception(r.text)

        return r.json()["message"]["content"]


# =========================================================
# Load use case file
# =========================================================
def load_use_case(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================================================
# Extract probes directly from Garak
# =========================================================
def load_probes():
    probes = []
    seen = set()

    for _, modname, _ in pkgutil.iter_modules(garak.probes.__path__):
        try:
            mod = importlib.import_module(f"garak.probes.{modname}")

            for name in dir(mod):
                cls = getattr(mod, name)
                key = f"{modname}.{name}"

                if (
                    isinstance(cls, type)
                    and issubclass(cls, Probe)
                    and cls is not Probe
                    and not name.endswith("Mixin")
                    and key not in seen
                ):
                    desc = getattr(cls, "description", None) or (cls.__doc__ or "").strip()

                    probes.append({
                        "probe": key,
                        "description": desc
                    })
                    seen.add(key)

        except:
            pass

    return probes


# =========================================================
# Step 1 — Build THREAT MODEL (important upgrade)
# =========================================================
def build_threat_model(llm, use_case):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a security threat modeling engine.\n"
                "Extract a precise testing objective from the system.\n\n"
                "Return ONLY JSON:\n"
                "{\n"
                "  \"core_risks\": [...],\n"
                "  \"attack_surface\": [...],\n"
                "  \"interaction_mode\": \"single|multi|both\",\n"
                "  \"strict_focus\": \"what must be tested exactly\"\n"
                "}"
            )
        },
        {
            "role": "user",
            "content": use_case
        }
    ]

    res = llm.chat(messages)

    import json
    try:
        return json.loads(res)
    except:
        start = res.find("{")
        end = res.rfind("}")
        return json.loads(res[start:end+1])


# =========================================================
# Step 2 — STRICT probe filtering per module
# =========================================================
def select_probes(llm, probes, model):

    modules = defaultdict(list)
    for p in probes:
        modules[p["probe"].split(".")[0]].append(p)

    selected = []
    reasons = {}

    for module, plist in modules.items():

        probe_text = "\n".join(
            f"- {p['probe']}: {p['description']}"
            for p in plist
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict security filter.\n"
                    "Select ONLY probes that are ESSENTIAL.\n\n"
                    "Rules:\n"
                    "- Prefer selecting fewer probes\n"
                    "- Do NOT include similar/duplicate attack types\n"
                    "- Only keep probes that test DISTINCT failure modes\n"
                    "- If uncertain → reject\n\n"
                    "Return format:\n"
                    "PROBES: p1,p2\n"
                    "REASONS:\n"
                    "- p1: reason\n"
                    "- p2: reason\n"
                    "If none: PROBES: none"
                )
            },
            {
                "role": "user",
                "content": f"""
SYSTEM THREAT MODEL:
{model}

MODULE: {module}

PROBES:
{probe_text}

IMPORTANT:
Select only NON-REDUNDANT probes that test different failure modes.
"""
            }
        ]

        print(f"[+] Analyzing module {module}...")
        res = llm.chat(messages)

        for line in res.split("\n"):
            if line.startswith("PROBES:"):
                raw = line.replace("PROBES:", "").strip()
                if raw.lower() != "none":
                    selected.extend([x.strip() for x in raw.split(",") if x.strip()])

            elif line.startswith("- "):
                parts = line[2:].split(":", 1)
                if len(parts) == 2:
                    reasons[parts[0].strip()] = parts[1].strip()

    return selected, reasons


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    path = input("Use case file path: ").strip()
    use_case = load_use_case(path)

    llm = OllamaLLM()

    print("[1] Building threat model...")
    model = build_threat_model(llm, use_case)

    print("[2] Loading Garak probes...")
    probes = load_probes()

    print(f"[+] Total probes: {len(probes)}")

    print("[3] Selecting probes...")
    selected, reasons = select_probes(llm, probes, model)

    print("\n==================== RESULT ====================")
    print(f"Selected probes: {len(selected)}")

    for p in selected:
        print(f"\n- {p}")
        print(f"  → {reasons.get(p, 'No reason')}")

    print("\n==================== RUN COMMAND ====================")
    print("python -m garak --probes " + ",".join(selected))