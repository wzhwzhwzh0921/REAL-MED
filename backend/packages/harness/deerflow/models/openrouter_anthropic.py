"""Claude via OpenRouter's Anthropic Skin (/v1/messages).

Mirrors what `ChatOpenRouterResponses` does for GPT-5.x: subclass the official
LangChain integration and only swap the default endpoint. langchain_anthropic
already preserves thinking / redacted_thinking / signature blocks across
multi-turn tool calls, so no manual reasoning-detail plumbing is needed here.

OpenRouter's Anthropic Skin behaves like the Anthropic API and accepts the
OpenRouter key in the standard `x-api-key` header (which is what the Anthropic
SDK sends by default). The Anthropic SDK appends `/v1/messages` to the base
URL, so the final endpoint becomes https://openrouter.ai/api/v1/messages —
do not include a `/v1` suffix in `base_url` or it will be doubled.

Prompt caching: this adapter injects `cache_control: {"type":"ephemeral"}` on
the system block and the last tool definition so that repeated calls in a
multi-agent flow read from cache (cache_read_input_tokens > 0) instead of
re-billing the system prompt + tool defs cold every turn. Anthropic's caching
requires ≥1024 tokens of cacheable prefix; smaller prompts will silently fall
back to no-cache.
"""

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic


class ChatOpenRouterAnthropic(ChatAnthropic):
    """Claude via OpenRouter's Anthropic Skin endpoint, with prompt caching."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("base_url", "https://openrouter.ai/api")
        super().__init__(**kwargs)

    @property
    def _llm_type(self) -> str:
        return "openrouter-anthropic"

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        _inject_cache_control(payload)
        import json as _j
        import os
        if os.environ.get("DEERFLOW_DEBUG_CACHE"):
            sys_field = payload.get("system")
            tools = payload.get("tools") or []
            sys_dump = _j.dumps(sys_field, ensure_ascii=False, default=str)[:600] if not isinstance(sys_field, str) else f"<str len={len(sys_field)}>"
            tools_dump = [{"name": t.get("name"), "cache_control": t.get("cache_control")} for t in tools if isinstance(t, dict)]
            print(f"[DEBUG cache] payload.system = {sys_dump}", flush=True)
            print(f"[DEBUG cache] payload.tools  = {tools_dump}", flush=True)
        return payload


def _inject_cache_control(payload: dict) -> None:
    """Mark system + last tool with cache_control: ephemeral.

    Anthropic accepts up to 4 cache breakpoints. We use 2:
      1. End of system prompt
      2. End of tools list
    Anything before each breakpoint is cached. We do NOT cache messages —
    those change every turn (new user input, new tool results) and would
    create a new cache entry every call, which costs more than it saves.
    """
    EPH = {"type": "ephemeral"}

    sys = payload.get("system")
    if isinstance(sys, str) and sys.strip():
        # langchain often sends system as a string; convert to typed-block list
        # so we can attach cache_control.
        payload["system"] = [{"type": "text", "text": sys, "cache_control": EPH}]
    elif isinstance(sys, list) and sys:
        for block in reversed(sys):
            if isinstance(block, dict) and block.get("type") == "text":
                block.setdefault("cache_control", EPH)
                break

    tools = payload.get("tools")
    if isinstance(tools, list) and tools:
        last = tools[-1]
        if isinstance(last, dict):
            last.setdefault("cache_control", EPH)
