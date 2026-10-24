# REAL-MED web interface

Optional interface for the DeerFlow-based REAL-MED harness. It displays model
conversations, tools, uploaded materials, and submitted artifacts. The benchmark
protocol is defined in the [main README](../README.md).

Requires Node.js 22+ and pnpm 10.26.2.

```bash
pnpm install --frozen-lockfile
pnpm check
pnpm dev
```

The development server runs on port 3000. Start the backend LangGraph and gateway
services separately, or use the root Docker setup. API URLs can be configured with
`NEXT_PUBLIC_LANGGRAPH_BASE_URL` and `NEXT_PUBLIC_BACKEND_BASE_URL`.
OpenRouter credentials belong in the server's root `.env`.
