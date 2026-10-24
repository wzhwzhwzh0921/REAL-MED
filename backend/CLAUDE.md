# Backend development

REAL-MED uses a DeerFlow/LangGraph harness. `packages/harness/deerflow/` contains
agent orchestration, models, sandbox, MCP, skills, and configuration. `app/`
contains the optional FastAPI gateway and Slack/Telegram channels. App imports
harness; harness must not import app. Keep the boundary test passing.

## Models and benchmark protocol

- Use `deerflow.models.openrouter:ChatOpenRouter` and `OPENROUTER_API_KEY`.
- Preserve complete `reasoning_details`, including opaque signatures, across tool turns.
- Model `context_window` is harness metadata, never an API request parameter.
- Explicit runtime settings override registry defaults.
- Resolve summarization models through the factory; use the agent's model unless
  a separate model is explicitly configured.
- Appendix C: trigger `max(floor(C/2), 98304)`, retain 32768 recent tokens,
  and allow at most three concurrent subagents.
- Appendix D.2: text and vision judges use GPT-5.4-mini, medium reasoning effort.
- The shared skills and scenario-specific MCP configuration live in the task registry.
- Per-case answer-format contracts follow the paper's concrete task examples.
  Required file deliverables must be presented; missing submissions receive zero
  credit before any judge calls. HIS tasks use scenario-system submission.

## Commands

```bash
uv sync --group dev
uv run pytest tests/ -q
uv run ruff check .
uv run langgraph dev --no-browser --allow-blocking --no-reload
PYTHONPATH=. uv run uvicorn app.gateway.app:app --port 8001
```

Add meaningful unit coverage for behavior changes and run the backend suite before
and after changes. Update the main README and this file when behavior changes.
Tests must mock model and external service calls. Do not commit credentials,
local configuration, run artifacts, or environment-specific cluster settings.

The example config is versioned. Add fields to the Pydantic schema and bump
`config_version` when changing it. Environment references use `$VARIABLE`.
Model construction belongs in `models/factory.py`; middleware assembly belongs
in `agents/lead_agent/agent.py`. Sandbox paths visible to agents are
`/mnt/user-data/{uploads,workspace,outputs}` and `/mnt/skills`.
