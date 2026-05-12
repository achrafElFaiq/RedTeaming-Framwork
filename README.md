# RedTeaming Framework

RedTeaming Framework is a Python-based red teaming toolkit for evaluating chatbot and LLM targets through YAML campaigns.

It currently supports:

- **PyRIT** for dataset, crescendo, and red-teaming style attacks
- **Garak** for probe-based attacks
- **HTTP targets** configurable through campaign YAML files
- **JSON reports** plus a **Streamlit dashboard** for analysis

---

## 1. What the framework does

The framework lets you describe a campaign like this:

1. define the **target** to attack
2. define a list of **attack YAML files**
3. run the campaign with `main.py`
4. execute PyRIT and/or Garak attacks against the target
5. normalize outputs into a common report format
6. save reports to `reports/`
7. inspect the results in the dashboard

In practice, the flow is:

```text
campaign YAML
→ target config
→ attack YAML files
→ PyRIT / Garak execution
→ normalized AttackResult JSON files
→ dashboard view
```

---

## 2. Project structure

```text
.
├── main.py                  # CLI entrypoint
├── requirements.txt         # Python dependencies
├── src/                     # source code
│   ├── settings.py          # runtime settings loaded from .env
│   ├── core/                # campaign loading, orchestration, reporting
│   └── frameworks/          # PyRIT and Garak integrations
├── examples/                # example campaigns, attacks, templates
│   ├── attacks/             # attack YAML catalog (R1–R5)
│   ├── campaigns/           # ready-to-run campaign YAMLs
│   └── templates/           # skeletons for new campaigns and attacks
├── config/                  # runtime config files (e.g. generated Garak config)
├── reports/                 # generated JSON reports (gitignored)
├── tests/                   # test suite
├── .env.example             # environment variable template
└── README.md
```

---

## 3. Prerequisites

You need:

- **Python ≥ 3.11**
- a virtual environment
- a target HTTP endpoint to test
- PyRIT if you want to run PyRIT campaigns
- Garak if you want to run Garak campaigns

---

## 4. Setup

### Create and activate a virtual environment

```zsh
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```zsh
pip install -r requirements.txt
```

PyRIT and Garak are optional — uncomment them in `requirements.txt` or install separately:

```zsh
pip install pyrit   # for PyRIT campaigns
pip install garak   # for Garak campaigns
```

### Copy the environment template

```zsh
cp .env.example .env
```

Then edit `.env` for your setup.

The main variables are:

- **PyRIT attacker LLM**
  - `PYRIT_ATTACKER_ENDPOINT`
  - `PYRIT_ATTACKER_MODEL`
  - `PYRIT_ATTACKER_API_KEY`
- **PyRIT scorer LLM**
  - `PYRIT_SCORER_ENDPOINT`
  - `PYRIT_SCORER_MODEL`
  - `PYRIT_SCORER_API_KEY`
- **PyRIT runtime**
  - `PYRIT_DB_PATH` (default: `pyrit.db`)
- **Reports**
  - `JSON_REPORTS_DIR` (default: `reports`)
- **Garak**
  - `GARAK_REPORTS_DIR`
  - `GARAK_CONFIG_PATH`

See `.env.example` for comments and defaults.

### Dynamic API key resolution (enterprise)

If your environment requires refreshing API tokens at runtime (e.g., JWT via an
identity provider), set the `*_API_KEY_COMMAND` variables instead of — or in
addition to — the static `*_API_KEY` ones:

```dotenv
PYRIT_ATTACKER_API_KEY_COMMAND="python scripts/get_token.py"
PYRIT_SCORER_API_KEY_COMMAND="python scripts/get_token.py"
```

When a `*_COMMAND` variable is set, the framework executes the command and uses
its stdout as the API key, ignoring the static value.

---

## 5. Quick start

Run an example campaign:

```zsh
python main.py examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml
```

Useful variants:

```zsh
python main.py examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --log-level DEBUG
python main.py examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --skip-checks
python main.py examples/campaigns/R1-prompt-leakage/prompt_leakage.yaml --no-dashboard
```

To launch the dashboard independently on existing reports:

```zsh
streamlit run src/core/results/report_viewer.py
```

By default, after a campaign run:

- reports are written to `reports/`
- the Streamlit dashboard is launched automatically unless `--no-dashboard` is used

---

## 6. Campaign format

A campaign defines:

- metadata
- one target
- an ordered list of attacks

Use `examples/templates/campaign.yaml` as the reference template.

### Campaign skeleton

```yaml
campaign:
  name: "My campaign"
  description: "What this campaign is testing"

target:
  name: "CustomerBot"
  model: "gpt-4.1-nano"
  architecture_type: "System Prompt + Context Injected"
  chat_url: "http://localhost:8000/api/chat"
  reset_memory_url: "http://localhost:8000/api/reset"
  input_field: "prompt"
  output_field: "response"

attacks:
  - examples/attacks/R1-prompt-leakage/r1_pyrit_direct_request.yaml
  - examples/attacks/R3-jailbreaking-guardrail-bypass/r3_pyrit_fictional_world.yaml
```

### Target fields

- `name`: human-readable target name
- `model`: model name shown in logs and dashboard
- `architecture_type`: target architecture category shown in logs and dashboard
- `chat_url`: endpoint that receives the input message
- `reset_memory_url`: optional endpoint used to reset target memory/context
- `input_field`: JSON field used to send the prompt to the target
- `output_field`: JSON field read from the target response

### Attack paths

Each item in `attacks:` is a path to an attack YAML file.

Paths are expected relative to the **project root**.

### Attack templates

See `examples/templates/` for editable attack skeletons:

- `attack_pyrit_dataset.yaml` — single-shot prompt list
- `attack_pyrit_crescendo.yaml` — multi-turn crescendo
- `attack_pyrit_red_teaming.yaml` — objective-driven red teaming
- `attack_garak.yaml` — Garak probe

---

## 7. Supported attack modes

### PyRIT dataset

- executes a list of prompts
- treats prompts as independent objectives
- resets target memory between each prompt when `reset_memory_url` is configured

### PyRIT crescendo

- multi-turn attack
- keeps conversational context across turns
- does **not** reset between turns

### PyRIT red teaming

- multi-turn objective-driven adversarial interaction
- uses attacker and scorer LLMs

### Garak

- probe-based scanning
- uses the configured REST generator against the target HTTP API

---

## 8. Outputs

The framework stores normalized JSON results in `reports/`.

Those reports are used by the dashboard and include metadata such as:

- framework
- attack name
- campaign name
- target URL
- target model
- target architecture type
- timestamp

Depending on the framework, a result contains either:

- `prompts` for Garak-style probe results
- `conversation` for PyRIT conversation-style results

---

## 9. Dashboard

The dashboard is implemented in:

- `src/core/results/report_viewer.py`

It provides three main views:

- **Overview**
- **Campaigns**
- **Attacks**

The dashboard shows campaign-level information such as:

- campaign name
- breach rate
- target model
- target architecture type

---

## 10. Testing

Run the test suite with:

```zsh
pytest
```

Or run a subset, for example:

```zsh
pytest tests/frameworks/test_pyrit_runner.py
pytest tests/application/test_campaign_loader.py
```

---

## 11. Current assumptions and limitations

- targets are currently modeled as HTTP chat endpoints
- the framework expects text input/output fields in JSON
- campaign attack paths are root-relative
- the dashboard reads normalized JSON reports, not live campaign YAML files
- PyRIT and Garak have different execution models, but both are normalized into the same reporting layer

---

## 12. Where to extend the project

- add new example campaigns under `examples/campaigns/`
- add new attacks under `examples/attacks/`
- add framework logic under `src/frameworks/`
- add orchestration or reporting logic under `src/core/`
- add regression tests under `tests/`

---

## 13. Recommended reading order for a new contributor

If you are new to the repo, start with:

1. `README.md`
2. `main.py`
3. `examples/templates/campaign.yaml`
4. `src/core/application/campaign_loader.py`
5. `src/frameworks/pyrit/pyrit_runner.py`
6. `src/frameworks/garak/garak_runner.py`

That gives a good end-to-end view of how campaigns are loaded, executed, normalized, and reported.
