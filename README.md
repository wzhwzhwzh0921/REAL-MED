# REAL-MED

Evaluation harness for **REAL-MED: Benchmarking LLM Agents on Real-World Medical Tasks**.
The benchmark contains 405 tasks across four categories and ten task types. Agents
use a shared DeerFlow harness to process materials, operate scenario tools, and
submit medical workflow deliverables.

| Category | Task type | Tasks | Deliverable |
|---|---|---:|---|
| Clinical Support | SOAP Documentation | 50 | PDF |
| Clinical Support | Complex Case Review | 44 | PDF |
| Clinical Support | Surgery Planning | 38 | DOCX |
| Patient Management | Chronic Disease Management | 39 | HIS submission (`his_result.jsonl`) |
| Patient Management | Pharmacy-Aware Medication Management | 39 | DOCX |
| Pharmacy Management | Pharmacy Inventory Management | 39 | DOCX + XLSX |
| Pharmacy Management | Dosage Calculation | 46 | DOCX |
| Medical Education & Research | Medical PPT Presentation | 41 | PPTX |
| Medical Education & Research | Medical Literature Review | 39 | DOCX |
| Medical Education & Research | Medication Formulary Design | 30 | XLSX |

Deliverables follow the concrete task examples in the paper and each case's
`[Answer Format]`. Template, layout, and file-format criteria remain part of evaluation.

## Data and file placement

Dataset: [Hugging Face — nips2026123user/Real-Med](https://huggingface.co/datasets/nips2026123user/Real-Med)
([JSONL download](https://huggingface.co/datasets/nips2026123user/Real-Med/resolve/main/data/real_med.jsonl)).
The runnable reference dataset is already included in this repository; no separate
download is needed for the commands below. Keep these paths under the repository root:

| Content | Path |
|---|---|
| Question prompt and attachment references | `evals/registry/cases/<task_slug>/<case_id>/case.yaml` |
| Input documents, templates, and spreadsheets | `evals/registry/attachments/<task_slug>/<case_id>/` |
| Expert rubric items | `rubrics/<task_slug>.jsonl` |
| Task defaults, expected output formats, and MCP wiring | `evals/registry/task_types/` |
| Pharmacy MCP workbooks | `evals/registry/mcp_data/pharmacy-operations/questions/` |
| Experiment model list and case selectors | `evals/experiments/exp_realmed_405case_11model.yaml` |

For a separate data disk or Kubernetes PVC, mount the dataset's registry directory
at `<checkout>/evals/registry` and its rubric directory at `<checkout>/rubrics`,
retaining the layout above. Run commands from `<checkout>`.

For example, `complex_case_review/complex_case_review_001` uses:

```text
evals/registry/cases/complex_case_review/complex_case_review_001/case.yaml
evals/registry/attachments/complex_case_review/complex_case_review_001/01_case_file.docx
rubrics/complex_case_review.jsonl
```

In `case.yaml`, attachment paths are relative to `evals/registry/attachments/`:

```yaml
attachments:
  - complex_case_review/complex_case_review_001/01_case_file.docx
```

When adding a case, put its YAML and attachments in the matching directories and
add a rubric row whose `question` matches the case's final ID segment. Include the
case in the experiment's `case_selectors`. The runner copies attachments into each
run's uploads directory automatically.

The HF snapshot includes the later 210-case medical-content revision; the bundled
YAML registry is the reference dataset. HF JSONL/JSON exports require conversion
to the registry layout before evaluation. Keep dataset revisions separate when
comparing results; `--case` selects a registry ID, not a downloaded JSONL file.

## Setup

Requires Python 3.12+, uv, and a sandbox provisioner connected to Kubernetes.

```bash
git clone https://github.com/wzhwzhwzh0921/REAL-MED.git
cd REAL-MED
make config
uv sync --project backend --group dev

# Keep the runner and sandbox provisioner on the same thread-data directory.
export DEER_FLOW_HOME="$PWD/backend/.deer-flow"
mkdir -p "$DEER_FLOW_HOME/threads"
```

If already cloned, start with `cd` into your checkout and skip `git clone`.
Run the remaining commands from the repository root. `make config` preserves
existing `.env` and `config.yaml` files.

Set `OPENROUTER_API_KEY` in `.env`. All candidate models, judges, image understanding,
and image generation use OpenRouter. Set `SERPER_API_KEY` and `JINA_API_KEY` for
web search. Point `SANDBOX_PROVISIONER_URL` at your provisioner; agent commands and file
creation run in sandbox Pods. See [sandbox setup](docker/provisioner/README.md).

For Kubernetes, the provisioner's `SKILLS_HOST_PATH` must point to the checkout's
`skills/`, and `THREADS_HOST_PATH` must equal `$DEER_FLOW_HOME/threads`. These
directories must be accessible at the configured paths on the sandbox nodes
(use shared storage for multiple nodes). Inside each sandbox they appear as:

| Sandbox path | Purpose |
|---|---|
| `/mnt/skills` | Shared skills |
| `/mnt/user-data/uploads` | This case's input attachments |
| `/mnt/user-data/workspace` | Intermediate files |
| `/mnt/user-data/outputs` | Final deliverables |

If you do not already have a provisioner, start one in another terminal from the
same checkout with a working kubeconfig:

```bash
export DEER_FLOW_HOME="$PWD/backend/.deer-flow"
export SKILLS_HOST_PATH="$PWD/skills"
export THREADS_HOST_PATH="$DEER_FLOW_HOME/threads"
export KUBECONFIG_PATH="$HOME/.kube/config"
export NODE_HOST=127.0.0.1  # Use the reachable node IP for a remote cluster.
mkdir -p "$THREADS_HOST_PATH"
uv run --project backend uvicorn app:app --app-dir docker/provisioner \
  --host 127.0.0.1 --port 8002
```

Set `SANDBOX_PROVISIONER_URL=http://localhost:8002` in `.env` for this setup.
Check readiness with `curl -fsS http://localhost:8002/health`. The coordinator and
judge run wherever their Python commands are launched; launch them in your
Kubernetes worker as well if their processing must run on cluster CPUs.

## Evaluation

Start with one model and one case. This first command only checks selection and
expands the run specification; it makes no model calls:

```bash
uv run --project backend python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml \
  --model minimax-m2.7 \
  --case complex_case_review/complex_case_review_001 --dry-run
```

Remove `--dry-run` to generate the deliverable. `--no-judge` keeps this step
generation-only; actual generation and subsequent judging use paid APIs:

```bash
uv run --project backend python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml \
  --model minimax-m2.7 \
  --case complex_case_review/complex_case_review_001 \
  --max-parallel 1 --max-parallel-cases 1 --no-judge

# Replace RUN_ID_FROM_OUTPUT with the run ID printed above.
uv run --project backend python scripts/run_judge_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml --run-id RUN_ID_FROM_OUTPUT
uv run --project backend python scripts/aggregate_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
```

For the full benchmark:

```bash
# Inspect the 405 × 11 matrix without model calls.
uv run --project backend python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml --dry-run

# Generate at up to 16 concurrent model/case runs; resume successful cases.
uv run --project backend python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml \
  --max-parallel 4 --max-parallel-cases 4 --skip-done --no-judge

# Score unjudged runs, then combine text and visual rubric scores.
uv run --project backend python scripts/run_judge_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
uv run --project backend python scripts/aggregate_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
```

Without `--no-judge`, the reference experiment automatically starts judging after
generation. Use `--run-id` to limit manual judging to a single run.

Results are saved under `evals/runs/exp_realmed_405case_11model/`:

| Path relative to the experiment directory | Content |
|---|---|
| `<run_id>/run.json`, `<run_id>/summary.json` | Resolved configuration and run status |
| `<run_id>/outputs/` | Submitted files |
| `<run_id>/judge/score.json`, `<run_id>/judge/score_image.json` | Text and visual rubric scores |
| `aggregate/leaderboard.json`, `aggregate/leaderboard.csv` | Aggregated results |

Live per-run working files are under `$DEER_FLOW_HOME/threads/<run_id>/user-data/`.
Judge-wide rubric summaries are written to `evals/reports/<experiment_id>/`.

The reference registry includes GPT-5.5, Claude-Opus-4.7, DeepSeek-V3.2, Gemini-3.1,
Qwen3.6-Plus, GLM-5.1, Kimi-K2.6, MiniMax-M2.7, Grok-4.20, MiMo-V2.5-Pro, and
HY3-Preview. Candidate runs enable thinking, planning, and up to three subagents.
Context summarization uses `max(floor(C / 2), 98,304)` and retains the latest 32K
tokens, following Appendix C. Reference context capacities are pinned in the model
registry; provider capacities may change.

Both text and visual judges use **GPT-5.4-mini with medium reasoning effort**, as
specified in Appendix D.2. Each rubric item receives a binary score supported by
the submitted artifact. Visual criteria are evaluated against rendered pages.
Missing required deliverables receive zero credit. File deliverables must be
submitted through `present_files`; HIS tasks submit through the scenario system.

## Layout

- `evals/registry/`: cases, attachments, task settings, and judge profiles.
- `rubrics/`: expert rubric items grouped by task type.
- `mcp_servers/`: chronic-disease HIS, medical calculator, and pharmacy tools.
- `skills/`: shared code, search, office, and image skills.
- `scripts/`: batch execution, judging, aggregation, and usage estimates.
- `backend/`, `frontend/`: DeerFlow harness and optional web interface.

Run `make test` for offline backend tests. Code retains its upstream [MIT license](LICENSE).
