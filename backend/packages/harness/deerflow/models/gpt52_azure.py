"""GPT-5.2 Azure via an Azure Responses-style proxy.

Custom LangChain BaseChatModel that calls the Responses API for multi-turn
encrypted reasoning passback.  The Responses API is fundamentally different
from Chat Completions:

- Input  : list of typed items (user, assistant, reasoning, function_call,
           function_call_output) rather than messages[].
- Output : list of typed output items (reasoning, message, function_call).
- Multi-turn reasoning: pass back {type:"reasoning", id, summary,
           encrypted_content} so the model can decrypt its prior thoughts.

State carried in AIMessage.additional_kwargs
--------------------------------------------
reasoning_content        : str   - summary text (shown in DeerFlow UI)
encrypted_content        : str   - opaque blob passed back next turn
reasoning_item_id        : str   - item id of the reasoning output
reasoning_item_summary   : list  - summary list for the reasoning item
function_call_items      : list  - raw function_call items to re-inject
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from typing import Any

import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai.chat_models.base import _create_usage_metadata_responses
from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import ConfigDict, Field

# Persistent session pool keyed by API key so the same TCP connection is
# reused across turns, helping with server-side routing affinity.
_session_pool: dict[str, requests.Session] = {}
_session_lock = threading.Lock()


def _get_http_session(api_key: str) -> requests.Session:
    with _session_lock:
        if api_key not in _session_pool:
            _session_pool[api_key] = requests.Session()
        return _session_pool[api_key]

logger = logging.getLogger(__name__)


class ChatGPT52Azure(BaseChatModel):
    """GPT-5.2 via an Azure Responses-style proxy with encrypted multi-turn reasoning."""

    model_config = ConfigDict(extra="ignore")

    api_key: str
    model: str = "gpt-5.2-2025-12-11"
    # Endpoint of the GPT /responses-style proxy. Configure via config.yaml's
    # `responses_url:` field (or $AZURE_RESPONSES_URL env var) — no built-in default.
    responses_url: str = ""
    max_output_tokens: int = 8192
    reasoning_effort: str = "high"
    reasoning_summary_mode: str = "detailed"
    # Stable per-instance session ID for upstream ALB routing affinity.
    # Ensures all turns within one thread hit the same backend, preventing -4003.
    session_id: str = Field(default_factory=lambda: f"deerflow-{uuid.uuid4().hex[:16]}")

    @property
    def _llm_type(self) -> str:
        return "gpt-5.2-azure"

    @property
    def model_name(self) -> str:
        return self.model

    # ------------------------------------------------------------------
    # Tool binding
    # ------------------------------------------------------------------

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        formatted = []
        for t in tools:
            try:
                fn = convert_to_openai_function(t)
                formatted.append({"type": "function", "function": fn})
            except Exception:
                if isinstance(t, dict):
                    formatted.append(t)
        return self.bind(tools=formatted, **kwargs)

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        input_items = self._messages_to_input(messages)
        tools = _openai_tools_to_responses(kwargs.get("tools", []))

        # Per-instance routing-mismatch latch:
        # The upstream /responses ALB can route a follow-up turn to a different
        # backend instance than the one that produced the previous turn's
        # encrypted_content, causing -4003 invalid_encrypted_content. Once we hit
        # that, we know this thread's traffic is being load-balanced across
        # instances and there is no way to recover the encrypted state — the
        # SAFE behaviour is to keep encrypted reasoning OFF for the rest of this
        # thread so we don't pay the cost of failing-then-retrying every single
        # turn. A fresh thread (new model instance) gets a fresh chance: if its
        # traffic happens to stick to one instance, encrypted reasoning runs
        # normally end-to-end.
        if getattr(self, "_encrypted_reasoning_disabled", False):
            input_items = [i for i in input_items if not (i.get("type") == "reasoning" and i.get("encrypted_content"))]
            return self._call_responses_api(input_items, tools, include_encrypted=False)

        try:
            return self._call_responses_api(input_items, tools, include_encrypted=True)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 400:
                body = exc.response.json() if exc.response.content else {}
                if body.get("error", {}).get("code") == "-4003":
                    logger.warning(
                        "invalid_encrypted_content (routing mismatch) — disabling encrypted "
                        "reasoning for the rest of this thread, retrying without it"
                    )
                    # Latch so subsequent turns in this thread skip the doomed retry.
                    object.__setattr__(self, "_encrypted_reasoning_disabled", True)
                    stripped = [i for i in input_items if not (i.get("type") == "reasoning" and i.get("encrypted_content"))]
                    return self._call_responses_api(stripped, tools, include_encrypted=False)
            raise

    def _call_responses_api(self, input_items: list[dict], tools: list[dict], *, include_encrypted: bool = True) -> ChatResult:
        payload: dict = {
            "model": self.model,
            "input": input_items,
            "reasoning": {
                "effort": self.reasoning_effort,
                "summary": self.reasoning_summary_mode,
            },
            "max_output_tokens": self.max_output_tokens,
            "parallel_tool_calls": False,
        }
        # Only ask the server to return encrypted_content if we still intend to
        # pass it back. Once the per-thread latch (_encrypted_reasoning_disabled)
        # has flipped, there's no value in continuing to fetch fresh blobs.
        if include_encrypted:
            payload["include"] = ["reasoning.encrypted_content"]
        if tools:
            payload["tools"] = tools

        # Session stickiness headers: tell the upstream ALB to route all turns from
        # this thread to the same backend instance, preventing -4003 errors.
        safe_sid = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.session_id)[:120]
        url = f"{self.responses_url}?ak={self.api_key}"
        session = _get_http_session(self.api_key)
        resp = session.post(
            url,
            headers={
                "Content-Type": "application/json",
                "extra": json.dumps({"session_id": safe_sid}, ensure_ascii=True),
                "X-TT-logid": safe_sid,
                "x-tt-logid": safe_sid,
            },
            json=payload,
            timeout=600,
        )
        if not resp.ok:
            logger.error("Responses API %d: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        return _parse_responses_api(resp.json())

    # ------------------------------------------------------------------
    # Message → input items
    # ------------------------------------------------------------------

    @staticmethod
    def _messages_to_input(messages: list[BaseMessage]) -> list[dict]:
        items: list[dict] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                items.append({"role": "developer", "content": _as_str(msg.content)})

            elif isinstance(msg, HumanMessage):
                items.append({"role": "user", "content": _as_str(msg.content)})

            elif isinstance(msg, AIMessage):
                # 1. Encrypted reasoning from previous turn
                ec = msg.additional_kwargs.get("encrypted_content")
                if ec:
                    items.append({
                        "type": "reasoning",
                        "id": msg.additional_kwargs.get("reasoning_item_id", ""),
                        "summary": msg.additional_kwargs.get("reasoning_item_summary", []),
                        "encrypted_content": ec,
                    })
                # 2. Function call items (model-side tool invocations)
                for fc_item in msg.additional_kwargs.get("function_call_items", []):
                    items.append(fc_item)
                # 3. Text response (if any)
                text = _as_str(msg.content)
                if text:
                    items.append({
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": text}],
                    })

            elif isinstance(msg, ToolMessage):
                items.append({
                    "type": "function_call_output",
                    "call_id": msg.tool_call_id,
                    "output": _as_str(msg.content),
                })
        return items


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _openai_tools_to_responses(tools: list) -> list[dict]:
    result = []
    for t in tools:
        if isinstance(t, dict) and "function" in t:
            fn = t["function"]
            result.append({
                "type": "function",
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            })
    return result


def _parse_responses_api(data: dict) -> ChatResult:
    output_items = data.get("output", [])

    text = ""
    reasoning_summary = ""
    encrypted_content = ""
    reasoning_item_id = ""
    reasoning_item_summary: list = []
    function_call_items: list = []
    tool_calls: list = []

    for item in output_items:
        itype = item.get("type")
        if itype == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    text = part.get("text", "")
                    break
        elif itype == "reasoning":
            reasoning_item_id = item.get("id", "")
            reasoning_item_summary = item.get("summary", [])
            encrypted_content = item.get("encrypted_content", "")
            reasoning_summary = " ".join(
                s.get("text", "") for s in reasoning_item_summary if s.get("type") == "summary_text"
            )
        elif itype == "function_call":
            call_id = item.get("call_id") or item.get("id", "")
            args_str = item.get("arguments", "{}")
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {"raw": args_str}
            tool_calls.append({
                "id": call_id,
                "name": item.get("name", ""),
                "args": args,
                "type": "tool_call",
            })
            function_call_items.append({
                "type": "function_call",
                "id": item.get("id", call_id),
                "call_id": call_id,
                "name": item.get("name", ""),
                "arguments": args_str,
            })

    additional_kwargs: dict = {}
    if reasoning_summary:
        additional_kwargs["reasoning_content"] = reasoning_summary
    if encrypted_content:
        additional_kwargs["encrypted_content"] = encrypted_content
        additional_kwargs["reasoning_item_id"] = reasoning_item_id
        additional_kwargs["reasoning_item_summary"] = reasoning_item_summary
    if function_call_items:
        additional_kwargs["function_call_items"] = function_call_items

    usage = data.get("usage", {})
    usage_metadata = _create_usage_metadata_responses(usage) if usage else None
    message = AIMessage(
        content=text,
        tool_calls=tool_calls,
        additional_kwargs=additional_kwargs,
        usage_metadata=usage_metadata,
    )
    return ChatResult(
        generations=[ChatGeneration(message=message, generation_info={"usage": usage} if usage else None)]
    )


def _as_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)
