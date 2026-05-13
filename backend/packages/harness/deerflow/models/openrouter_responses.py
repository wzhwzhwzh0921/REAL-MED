"""OpenAI reasoning models via OpenRouter's /responses endpoint.

OpenRouter proxies OpenAI's Responses API at https://openrouter.ai/api/v1/responses,
which is required for multi-turn encrypted reasoning passback on GPT-5.x.

This adapter reuses the Responses ↔ LangChain conversion logic from
`gpt52_azure.ChatGPT52Azure` and only swaps out the HTTP call:
  - URL: OpenRouter /responses instead of the Azure proxy
  - Auth: `Authorization: Bearer <key>` instead of `?ak=<key>` query param
  - model: OpenRouter-style ids like `openai/gpt-5.4` or `openai/gpt-5.1`

See gpt52_azure.py for the Responses API protocol details (typed input items,
encrypted reasoning blocks, function_call items for tool invocations).
"""
from __future__ import annotations

import logging

import requests
from langchain_core.outputs import ChatResult

from deerflow.models.gpt52_azure import (
    ChatGPT52Azure,
    _get_http_session,
    _parse_responses_api,
)

logger = logging.getLogger(__name__)


class ChatOpenRouterResponses(ChatGPT52Azure):
    """OpenAI reasoning model via OpenRouter's Responses API endpoint."""

    responses_url: str = "https://openrouter.ai/api/v1/responses"

    @property
    def _llm_type(self) -> str:
        return "openrouter-responses"

    def _call_responses_api(self, input_items: list[dict], tools: list[dict], *, include_encrypted: bool = True) -> ChatResult:
        # OpenRouter's /responses isn't behind a multi-instance ALB so encrypted
        # reasoning passback works reliably across turns. Keep include_encrypted
        # default True; accept the keyword for signature parity with the parent
        # class (ChatGPT52Azure) whose -4003 latch can flip it to False.
        payload: dict = {
            "model": self.model,
            "input": input_items,
            "reasoning": {
                "effort": self.reasoning_effort,
                "summary": self.reasoning_summary_mode,
            },
            "max_output_tokens": self.max_output_tokens,
        }
        if include_encrypted:
            payload["include"] = ["reasoning.encrypted_content"]
        if tools:
            payload["tools"] = tools

        session = _get_http_session(self.api_key)
        resp = session.post(
            self.responses_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json=payload,
            timeout=600,
        )
        if not resp.ok:
            logger.error("OpenRouter Responses %d: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        return _parse_responses_api(resp.json())
