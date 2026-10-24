# REAL-MED backend

The DeerFlow-based harness provides model calls, planning, up to three concurrent
subagents, context summarization, sandbox file operations, and scenario MCP tools.
Benchmark settings and task deliverables are described in the [main README](../README.md).

```bash
uv sync --group dev
uv run pytest tests/ -q
uv run ruff check .
```

Copy the root `.env.example` and `config.example.yaml` before running evaluations.
`deerflow.models.openrouter:ChatOpenRouter` is the shared OpenRouter model adapter.
It preserves structured reasoning across tool turns. The optional Responses adapter
uses SDK authentication, retries, and encrypted reasoning support.

The LangGraph server runs on port 2024 and the optional FastAPI gateway on port 8001:

```bash
uv run langgraph dev --no-browser --allow-blocking --no-reload
PYTHONPATH=. uv run uvicorn app.gateway.app:app --port 8001
```

The `deerflow.*` harness lives under `packages/harness/`; `app.*` contains the web
API and optional Slack/Telegram integrations. Harness code must not import `app.*`.
Task commands execute through the configured Kubernetes sandbox provisioner.
