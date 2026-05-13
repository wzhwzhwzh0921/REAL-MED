# Real-Med Eval Platform (DeerFlow English Fork)

DeerFlow-based evaluation harness for the **Real-Med** benchmark:
**405 medical cases × 10 task types × any number of models**, with LLM-as-judge
scoring per rubric and a router that automatically splits text vs. visual
rubrics across two judges.

This repo is a cleaned, English release fork of an internal DeerFlow eval
platform. All credentials are placeholders (`.env.example` / `.env`); fill
them in before running.

---

## Repo layout

| Path | Purpose |
|---|---|
| `evals/registry/cases/<slug>/<case_id>/case.yaml` | One per question: prompt, attachments, MCP question_id (where applicable). 405 cases total across 10 slugs. |
| `evals/registry/attachments/<slug>/<case_id>/` | Per-case binary attachments (docx, pdf, pptx, xlsx) referenced by `case.yaml`. |
| `evals/registry/task_types/<slug>.yaml` | Per-task-type defaults: skills, MCP wiring, expected outputs, judge profile. |
| `evals/registry/task_types/extensions_configs/<slug>.json` | DeerFlow extensions config (MCP servers + skill toggles) for MCP-bound slugs. |
| `evals/registry/judges/*.yaml` | Judge profiles (`junxiu_rubric_judge`, `junxiu_rubric_judge_vision`). |
| `evals/registry/mcp_data/<server>/` | Bulky per-question data served by an MCP server (e.g. pharmacy-operations xlsx workbooks). Kept here so all large attachments live under `evals/registry/`. |
| `evals/experiments/exp_*.yaml` | Experiment definitions: models × case selectors × runtime knobs. |
| `evals/runs/<exp_id>/<run_id>/` | Output of each (model, case) run: `summary.json`, `outputs/`, later `judge/score.json` + `judge/score_image.json`. |
| `rubrics/<slug>.jsonl` | Aggregated rubrics for the judge to look up by `question` key (= case_id last segment). |
| `mcp_servers/{chronic-disease-his, medcal, pharmacy-operations}/` | Stdio MCP servers used by the 3 MCP-bound task types. |
| `scripts/run_batch_eval.py` | Expands an experiment YAML and runs each (model, case) as a subprocess. |
| `scripts/run_judge_eval.py` | Scores completed runs: per-rubric router → text or vision judge → `judge/score*.json`. |
| `scripts/aggregate_eval.py` | Aggregates per-run judge scores into an experiment-level leaderboard / Excel. |
| `scripts/compute_usage_cost.py` | Computes API token usage and cost per experiment. |
| `scripts/render_artifacts.py` | Renders submitted `.docx`/`.pptx` to PNG for the vision judge. |
| `run_client_test.py` | Single-case runner. Called by `run_batch_eval.py` as a subprocess. |
| `backend/` | DeerFlow Python workspace (`uv` managed). Source for the `deerflow` package. |
| `backend/pyproject.toml` / `backend/uv.lock` | Canonical backend dependency metadata and lock file. Use these to recreate `backend/.venv`. |
| `requirements.txt` | Human-readable summary of direct backend dependencies. |
| `requirements.lock.txt` | Fully resolved pip-style requirements exported from `uv.lock`, including transitive dependencies. |
| `config.yaml` / `config.example.yaml` | DeerFlow model registry (LLM names → provider/endpoint/$env-key). |
| `.env` / `.env.example` | API keys + endpoints (placeholders by default). |

---

## Quickstart

### 1. Fill in `.env`

Copy `.env.example` if you don't already have `.env`, then populate:

```env
OPENROUTER_API_KEY=your-openrouter-key       # all OpenRouter-routed models
OPENROUTER_API_BASE=https://openrouter.ai/api/v1

AZURE_OPENAI_API_KEY=your-azure-key          # judge + Azure-hosted models
AZURE_OPENAI_ENDPOINT=https://...            # your Azure / proxy endpoint
AZURE_OPENAI_API_VERSION=2024-03-01-preview

ARK_API_KEY=your-ark-key                     # for ARK vision endpoints (web-search-mm)
ARK_API_BASE=https://...

SERPER_API_KEY=your-serper-key               # Google search via Serper
JINA_API_KEY=your-jina-key                   # Jina page reader
```

### 2. Set up the Python workspace

The checked-out repo does not need to include `backend/.venv`. Recreate it
from the lock file when needed:

```bash
cd backend
uv sync                  # builds backend/.venv from uv.lock
cd ..
```

For pip-based environments, `requirements.txt` lists the direct
dependencies, while `requirements.lock.txt` is the fully resolved
export from `uv.lock`.

### 3. Dry-run the experiment to see the matrix

```bash
python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml --dry-run
```

This expands 11 models × 405 cases = **4,455 runs** without invoking any LLMs.
Inspect the output to make sure each case is resolved.

### 4. Real run

```bash
python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
```

Per-run outputs land in `evals/runs/exp_realmed_405case_11model/<run_id>/`,
each containing:

- `run.json` — the resolved run spec (model, case, prompt, paths)
- `summary.json` — completion status, tool errors, elapsed time, output files
- `outputs/...` — the model's delivered artifacts (`.docx`, `.pdf`, `.pptx`, `.xlsx`, `his_result.jsonl`)
- `<run_id>.jsonl` — the full DeerFlow streaming log

Useful flags on `run_batch_eval.py`:

| Flag | Effect |
|---|---|
| `--dry-run` | Expand the matrix, don't actually run |
| `--model <name>` | Restrict to one model |
| `--case <pattern>` | Restrict to cases matching a glob |
| `--run-id <id>` | Re-run a specific run id |
| `--force` | Re-run even if `summary.json` already exists |

### 5. Judge

```bash
python scripts/run_judge_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
```

For every completed run, the judge:

1. Looks up the case's rubric list via `lookup_rubric` → `rubrics/<slug>.jsonl`.
2. For each rubric, calls a **router LLM** (`router_model` in the judge yaml,
   defaults to the same model as `judge_model`) to classify it as `TEXT` or
   `VISUAL`.
3. Sends TEXT rubrics to the text judge → writes `judge/score.json`.
4. Sends VISUAL rubrics to the vision judge (with rendered PNGs of the
   submitted artifact) → writes `judge/score_image.json`.

Useful flags on `run_judge_eval.py`:

| Flag | Effect |
|---|---|
| `--run-id <id>` | Judge only this run |
| `--force` | Re-score even if `judge/score.json` already exists |
| `--judge-model <name>` | Override the model from the profile |
| `JUDGE_ITEM_WORKERS=N` (env) | Per-run parallel rubric scoring (default 8) |
| `JUDGE_ROUTER_WORKERS=N` (env) | Per-run parallel router classification (default 8) |

### 6. Aggregate

```bash
python scripts/aggregate_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
```

Produces an experiment-level leaderboard (Excel + JSON) at
`evals/reports/exp_realmed_405case_11model/`.

---

## Task types

10 task types, all sharing identical runtime defaults (`thinking: on`,
`reasoning_effort: high`, `plan_mode: true`, `subagent: true`,
`recursion_limit: 4000`) and the same `junxiu_rubric_judge` judge profile.

| Slug | Cases | Output | MCP server | Skills |
|---|---:|---|---|---|
| `soap_documentation` | 50 | `.pdf` | — | `code`, `pdf`, `docx`, `web-search` |
| `complex_case_review` | 44 | `.pdf` | — | `code`, `pdf`, `docx`, `web-search` |
| `surgery_planning` | 38 | `.docx` | — | `code`, `docx`, `web-search` |
| `chronic_disease_management` | 39 | `his_result.jsonl` | **chronic-disease-his** | `docx` |
| `pharmacy_aware_medication_management` | 39 | `.docx` | — | `code`, `docx`, `xlsx`, `web-search` |
| `pharmacy_inventory_management` | 39 | `.docx` + `.xlsx` | **pharmacy-operations** | `code`, `docx`, `xlsx`, `web-search` |
| `dosage_calculation` | 46 | `.docx` | **medcal** | `code`, `docx` |
| `medical_ppt_presentation` | 41 | `.pptx` | — | `code`, `pptx`, `pptx-design`, `docx`, `web-search`, `web-search-mm`, `nano-banana-pro` |
| `medical_literature_review` | 39 | `.docx` | — | `code`, `docx`, `web-search`, `web-search-mm`, `nano-banana-pro` |
| `medication_formulary_design` | 30 | `.xlsx` | — | `code`, `xlsx`, `docx`, `web-search` |

For the 3 MCP-bound slugs, `extensions_config:` in the task-type YAML points at
a JSON under `evals/registry/task_types/extensions_configs/` that wires the
stdio MCP server (with `${REPO_ROOT}` and `$OUTPUTS_DIR` placeholders resolved
at run time).

### MCP servers

- **chronic-disease-his** (`mcp_servers/chronic-disease-his/server.py`) — 8
  fake HIS tools (`update_diagnosis`, `create_prescription`, `order_lab_test`,
  `order_imaging`, `create_follow_up_plan`, `submit_referral`,
  `get_pending_orders`, `submit_orders`). Final state flushed to
  `$OUTPUTS_DIR/his_result.jsonl` on `submit_orders`.
- **medcal** (`mcp_servers/medcal/`) — 82 medical calculation formulas
  (renal, body metrics, pharmacokinetics, vancomycin, cardiac, hemodynamics,
  respiratory, acid-base, osmolality, fluid/electrolyte, hepatology,
  valvular, echocardiography, burn, endocrine, toxicology, oncology,
  neurology, dialysis, nutrition, hematology, nuclear medicine, diuretics).
- **pharmacy-operations** (`mcp_servers/pharmacy-operations/server.py`) —
  drug-catalog/inventory tools backed by **per-question Excel workbooks**
  under `evals/registry/mcp_data/pharmacy-operations/questions/v5_*.xlsx`.
  `initialize_session(question_id="v5_xxx")` loads that question's drug
  universe. Real-Med `pharmacy_inventory_management` case files carry an
  `mcp_question_id` field mapping to `v5_xxx` (1:1).

---

## Models

The reference experiment (`evals/experiments/exp_realmed_405case_11model.yaml`)
runs these 11 models, each with `thinking: on` and `reasoning_effort: high`:

`gpt-5.5`, `claude-opus-4.7`, `deepseek-v3.2`, `gemini-3.1`, `qwen3.6-plus`,
`glm-5.1`, `kimi-k2.6`, `minimax-m2.7`, `grok-4.20`, `mimo-v2.5-pro`,
`hy3-preview`.

Each name must be registered in `config.yaml` with a provider, endpoint and an
`api_key: $ENV_VAR` reference. See `config.example.yaml` for the registration
schema.

---

## Judge architecture

Two profiles ship in `evals/registry/judges/`:

- **`junxiu_rubric_judge`** — text judge, default model `gpt-5.2-azure`.
  Scores each rubric independently as 0/1 against the submitted text content
  (extracted from `.docx`/`.pdf`/`.pptx`, or the `records` field of
  `his_result.jsonl` for HIS tasks). Output: `judge/score.json`.
- **`junxiu_rubric_judge_vision`** — vision judge, default model
  `gemini-3.1-p-azure`. Scores each visual rubric against rendered PNGs of
  the artifact (`scripts/render_artifacts.py` produces these). Output:
  `judge/score_image.json`.

At judge time, `run_judge_eval.py:_split_rubrics_by_visual` calls the router
LLM on every rubric to decide which judge handles it, then dispatches each
group in parallel. Default router = same model as `judge_model`; override
via `router_model:` in the judge YAML.

---

## Data origin

- Real-Med dataset was imported from `hf_upload/Real-Med` (HuggingFace-ready
  dataset directory) into this repo's `evals/registry/{cases,attachments}/`.
- Rubrics were aggregated per slug into `rubrics/<slug>.jsonl` (each line:
  `{"question": "<case_id>", "rubrics": ["...", ...]}`). The judge's
  `lookup_rubric()` keys by the last path segment of `case_id`, so the
  in-repo case dirs (`<slug>/<case_id>/case.yaml`) and the rubrics file
  stay automatically aligned.
- Pharmacy-operations MCP holds 47 per-question Excels in
  `evals/registry/mcp_data/pharmacy-operations/questions/`. The 39 Real-Med
  `pharmacy_inventory_management` cases are the `v5_001`–`v5_010` slice
  (ward dispensing); each `case.yaml` carries the `mcp_question_id` so the
  harness can `initialize_session(question_id=...)` automatically.

---

## CLI reference

| Command | Purpose |
|---|---|
| `python scripts/run_batch_eval.py <exp.yaml> [--dry-run] [--model M] [--case G] [--run-id ID] [--force]` | Run experiment matrix |
| `python scripts/run_judge_eval.py <exp.yaml> [--run-id ID] [--force] [--judge-model M]` | Judge completed runs |
| `python scripts/aggregate_eval.py <exp.yaml>` | Build leaderboard Excel |
| `python scripts/compute_usage_cost.py <exp.yaml>` | Compute token + dollar cost |
| `python scripts/render_artifacts.py <run_dir> [--force] [--dpi 144]` | Render docx/pptx to PNG for the vision judge (called automatically by the judge) |

Environment knobs:

- `OUTPUTS_DIR` — where per-run artifacts go (set by `run_batch_eval.py` per run)
- `DEER_FLOW_HOME` — per-run isolated home dir
- `DEER_FLOW_EXTENSIONS_CONFIG_PATH` — resolved extensions config for the run
- `JUDGE_ITEM_WORKERS` (default 8) — parallel rubric scoring per run
- `JUDGE_ROUTER_WORKERS` (default 8) — parallel router classification per run
- `NO_PROXY` — both `run_batch_eval.py` and `run_judge_eval.py` strip IPv6
  CIDRs from `NO_PROXY` before importing httpx, because httpx mis-parses
  them.
