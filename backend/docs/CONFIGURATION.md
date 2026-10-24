# REAL-MED configuration

Copy the root `config.example.yaml` to `config.yaml` and `.env.example` to `.env`.
The root example is the reference model and harness configuration.

```yaml
models:
  - name: gpt-5.4-mini
    use: deerflow.models.openrouter:ChatOpenRouter
    model: openai/gpt-5.4-mini
    api_key: $OPENROUTER_API_KEY
    base_url: $OPENROUTER_API_BASE
    context_window: 400000
    supports_vision: true
    supports_thinking: true
    supports_reasoning_effort: true
    reasoning_effort: medium
```

Model names are registry aliases; `model` is the OpenRouter identifier.
`context_window` determines the harness summarization threshold and is never sent
to the provider. The reference capacities follow paper Appendix C, Table 7.
Explicit per-call settings override registry values. Reasoning is sent through
OpenRouter's unified `reasoning` parameter, and complete reasoning blocks are
preserved across tool turns.

`SANDBOX_PROVISIONER_URL` points to the Kubernetes sandbox provisioner. The public
sandbox image is `ghcr.io/agent-infra/sandbox:latest`; use `SANDBOX_IMAGE` to select
a locally built or pinned image. Skills run inside the sandbox and use the same
OpenRouter environment variables.

`evals/registry/task_types/` defines shared skills, scenario-specific MCP services,
deliverables, and judge profiles. Both judges use GPT-5.4-mini with medium reasoning.
`DEER_FLOW_CONFIG_PATH` selects an alternative model/harness configuration.
`DEER_FLOW_EXTENSIONS_CONFIG_PATH` selects an MCP/skills configuration.
