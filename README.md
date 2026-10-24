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

## Setup

Requires Python 3.12+, uv, and a sandbox provisioner connected to Kubernetes.

```bash
cp .env.example .env
cp config.example.yaml config.yaml
uv sync --project backend --group dev
```

Set `OPENROUTER_API_KEY` in `.env`. All candidate models, judges, image understanding,
and image generation use OpenRouter. Set `SERPER_API_KEY` and `JINA_API_KEY` for
web search. Point `SANDBOX_PROVISIONER_URL` at your provisioner; agent commands and file
creation run in sandbox Pods. See [sandbox setup](docker/provisioner/README.md).

## Evaluation

```bash
# Inspect the 405 × 11 matrix without model calls.
uv run --project backend python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml --dry-run

# Generate deliverables, judge them, then aggregate scores.
uv run --project backend python scripts/run_batch_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
uv run --project backend python scripts/run_judge_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
uv run --project backend python scripts/aggregate_eval.py \
  evals/experiments/exp_realmed_405case_11model.yaml
```

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
