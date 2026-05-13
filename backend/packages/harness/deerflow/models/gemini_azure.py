"""Gemini Azure via an Azure-hosted Google GenerateContent endpoint.

Custom LangChain BaseChatModel that calls the native Gemini generateContent
endpoint for multi-turn thinking with thoughtSignature passback.

Native Gemini API differences from OpenAI format
-------------------------------------------------
- Uses "contents" (role/parts) instead of "messages".
- Thinking parts have {"thought": true} and are separate from text parts.
- Tool calls are {"functionCall": {name, args}} inside parts.
- Tool results are {"functionResponse": {name, response}} in a "user" turn.
- thoughtSignature on function call parts must be passed back verbatim.

State carried in AIMessage.additional_kwargs
--------------------------------------------
reasoning_content       : str   - thinking text (shown in DeerFlow UI)
gemini_parts            : list  - full raw parts from the model turn
                                  (includes thought parts + thoughtSignature)
gemini_call_id_to_name  : dict  - maps generated call_id → function name
                                  (used to reconstruct functionResponse turns)
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from typing import Any, Optional

import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import ConfigDict, Field

_session_pool: dict[str, requests.Session] = {}
_session_lock = threading.Lock()


def _get_http_session(api_key: str) -> requests.Session:
    with _session_lock:
        if api_key not in _session_pool:
            _session_pool[api_key] = requests.Session()
        return _session_pool[api_key]

logger = logging.getLogger(__name__)


class ChatGeminiAzure(BaseChatModel):
    """Gemini via the Azure-hosted Gemini endpoint with multi-turn thinking."""

    model_config = ConfigDict(extra="ignore")

    api_key: str
    model: str = "gemini-3-pro-preview-new"
    # Endpoint of the Gemini Azure proxy. Configure via config.yaml's
    # `gemini_base_url:` field (or $AZURE_GEMINI_BASE_URL env var) — no built-in default.
    gemini_base_url: str = ""
    max_output_tokens: int = 8192
    temperature: Optional[float] = None
    session_id: str = Field(default_factory=lambda: f"deerflow-{uuid.uuid4().hex[:16]}")

    @property
    def _llm_type(self) -> str:
        return "gemini-azure"

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
        contents, system_instruction = self._messages_to_contents(messages)
        tools = _openai_tools_to_gemini(kwargs.get("tools", []))

        gen_config: dict = {
            "maxOutputTokens": self.max_output_tokens,
            "thinkingConfig": {"includeThoughts": True},
        }
        if self.temperature is not None:
            gen_config["temperature"] = self.temperature

        payload: dict = {
            "contents": contents,
            "generationConfig": gen_config,
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if tools:
            payload["tools"] = [{"functionDeclarations": tools}]
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

        url = f"{self.gemini_base_url}/{self.model}:generateContent"
        safe_sid = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.session_id)[:120]
        session = _get_http_session(self.api_key)
        resp = session.post(
            url,
            headers={
                "X-Goog-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "extra": json.dumps({"session_id": safe_sid}, ensure_ascii=True),
                "X-TT-logid": safe_sid,
                "x-tt-logid": safe_sid,
            },
            json=payload,
            timeout=300,
        )
        if not resp.ok:
            logger.error("Gemini API %d: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        return _parse_gemini_response(resp.json())

    # ------------------------------------------------------------------
    # Message → contents
    # ------------------------------------------------------------------

    def _messages_to_contents(self, messages: list[BaseMessage]):
        contents: list[dict] = []
        system_text: str | None = None

        i = 0
        while i < len(messages):
            msg = messages[i]

            if isinstance(msg, SystemMessage):
                system_text = _as_str(msg.content)

            elif isinstance(msg, HumanMessage):
                contents.append({"role": "user", "parts": [{"text": _as_str(msg.content)}]})

            elif isinstance(msg, AIMessage):
                # Prefer stored raw parts (includes thought + thoughtSignature)
                gemini_parts = msg.additional_kwargs.get("gemini_parts")
                if gemini_parts:
                    contents.append({"role": "model", "parts": gemini_parts})
                else:
                    parts: list[dict] = []
                    text = _as_str(msg.content)
                    if text:
                        parts.append({"text": text})
                    for tc in (msg.tool_calls or []):
                        parts.append({"functionCall": {"name": tc["name"], "args": tc.get("args", {})}})
                    if parts:
                        contents.append({"role": "model", "parts": parts})

            elif isinstance(msg, ToolMessage):
                # Collect all consecutive ToolMessages into one user turn
                tool_parts: list[dict] = []
                while i < len(messages) and isinstance(messages[i], ToolMessage):
                    tmsg = messages[i]
                    fn_name = tmsg.name or self._resolve_fn_name(messages, i, tmsg.tool_call_id)
                    tool_parts.append({
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"result": _as_str(tmsg.content)},
                        }
                    })
                    i += 1
                contents.append({"role": "user", "parts": tool_parts})
                continue  # already incremented i

            i += 1

        system_instruction = None
        if system_text:
            system_instruction = {"parts": [{"text": system_text}], "role": "user"}

        return contents, system_instruction

    @staticmethod
    def _resolve_fn_name(messages: list[BaseMessage], tool_msg_idx: int, call_id: str) -> str:
        """Walk backwards to find the function name for a given call_id."""
        for msg in reversed(messages[:tool_msg_idx]):
            if isinstance(msg, AIMessage):
                mapping = msg.additional_kwargs.get("gemini_call_id_to_name", {})
                if call_id in mapping:
                    return mapping[call_id]
                for tc in (msg.tool_calls or []):
                    if tc.get("id") == call_id:
                        return tc.get("name", call_id)
                break
        return call_id


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _openai_tools_to_gemini(tools: list) -> list[dict]:
    result = []
    for t in tools:
        if isinstance(t, dict) and "function" in t:
            fn = t["function"]
            result.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parametersJsonSchema": fn.get("parameters", {}),
            })
    return result


def _parse_gemini_response(data: dict) -> ChatResult:
    candidates = data.get("candidates", [])
    if not candidates:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])

    parts = candidates[0].get("content", {}).get("parts", [])

    text = " ".join(p["text"] for p in parts if p.get("text") and not p.get("thought"))
    thinking = " ".join(p["text"] for p in parts if p.get("thought") and p.get("text"))

    tool_calls: list[dict] = []
    call_id_to_name: dict[str, str] = {}
    for idx, p in enumerate(parts):
        if "functionCall" in p:
            fc = p["functionCall"]
            call_id = f"gemini_call_{idx}"
            tool_calls.append({
                "id": call_id,
                "name": fc.get("name", ""),
                "args": fc.get("args", {}),
                "type": "tool_call",
            })
            call_id_to_name[call_id] = fc.get("name", "")

    additional_kwargs: dict = {}
    if thinking:
        additional_kwargs["reasoning_content"] = thinking
    if parts:
        # Store full parts so next turn can pass them back verbatim
        # (critical for thoughtSignature on function call parts)
        additional_kwargs["gemini_parts"] = parts
    if call_id_to_name:
        additional_kwargs["gemini_call_id_to_name"] = call_id_to_name

    message = AIMessage(content=text, tool_calls=tool_calls, additional_kwargs=additional_kwargs)
    usage = data.get("usageMetadata", {})
    return ChatResult(
        generations=[ChatGeneration(message=message, generation_info={"usage": usage} if usage else None)]
    )


def _as_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)
