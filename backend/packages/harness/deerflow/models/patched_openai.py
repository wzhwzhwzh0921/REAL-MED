"""Patched ChatOpenAI adapter for OpenAI reasoning output via OpenRouter.

OpenAI models (GPT-5.4 etc.) return reasoning content in ``message.reasoning``
(non-streaming) and ``delta.reasoning`` / ``delta.reasoning_details`` (streaming)
when ``reasoning.effort`` is set.  ``langchain_openai.ChatOpenAI`` ignores these
fields, so DeerFlow never receives reasoning content.

This adapter:
1. Injects ``reasoning`` into the request ``extra_body`` when thinking is enabled.
2. Extracts ``message.reasoning`` from non-streaming responses and stores it in
   ``additional_kwargs.reasoning_content``.
3. Extracts ``delta.reasoning`` from streaming chunks similarly.
4. Preserves ``reasoning_content`` in multi-turn payloads (like PatchedChatDeepSeek).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_openai.chat_models.base import (
    _convert_delta_to_message_chunk,
    _create_usage_metadata,
)


def _with_reasoning(
    message: AIMessage | AIMessageChunk,
    reasoning: str | None,
    *,
    preserve_whitespace: bool = False,
) -> AIMessage | AIMessageChunk:
    """Attach reasoning text to ``additional_kwargs.reasoning_content``."""
    if not reasoning:
        return message
    additional_kwargs = dict(message.additional_kwargs)
    if preserve_whitespace:
        existing = additional_kwargs.get("reasoning_content")
        additional_kwargs["reasoning_content"] = (
            f"{existing}{reasoning}" if isinstance(existing, str) else reasoning
        )
    else:
        existing = additional_kwargs.get("reasoning_content")
        if existing and isinstance(existing, str):
            parts = [existing.strip(), reasoning.strip()]
            additional_kwargs["reasoning_content"] = "\n\n".join(p for p in parts if p)
        else:
            additional_kwargs["reasoning_content"] = reasoning
    return message.model_copy(update={"additional_kwargs": additional_kwargs})


class PatchedChatOpenAI(ChatOpenAI):
    """ChatOpenAI adapter that captures OpenAI / OpenRouter reasoning output."""

    # ------------------------------------------------------------------
    # Request: inject reasoning config & preserve reasoning_content
    # ------------------------------------------------------------------

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        # Get original messages for reasoning_content preservation
        original_messages = self._convert_input(input_).to_messages()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        # Preserve reasoning_content on assistant messages (multi-turn)
        payload_messages = payload.get("messages", [])
        if len(payload_messages) == len(original_messages):
            for payload_msg, orig_msg in zip(payload_messages, original_messages):
                if payload_msg.get("role") == "assistant" and isinstance(orig_msg, AIMessage):
                    rc = orig_msg.additional_kwargs.get("reasoning_content")
                    if rc is not None:
                        payload_msg["reasoning_content"] = rc
        else:
            ai_messages = [m for m in original_messages if isinstance(m, AIMessage)]
            assistant_payloads = [(i, m) for i, m in enumerate(payload_messages) if m.get("role") == "assistant"]
            for (idx, payload_msg), ai_msg in zip(assistant_payloads, ai_messages):
                rc = ai_msg.additional_kwargs.get("reasoning_content")
                if rc is not None:
                    payload_messages[idx]["reasoning_content"] = rc

        return payload

    # ------------------------------------------------------------------
    # Non-streaming: extract message.reasoning
    # ------------------------------------------------------------------

    def _create_chat_result(
        self,
        response: dict | Any,
        generation_info: dict | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump()
        choices = response_dict.get("choices", [])

        generations: list[ChatGeneration] = []
        for index, generation in enumerate(result.generations):
            choice = choices[index] if index < len(choices) else {}
            message = generation.message
            if isinstance(message, AIMessage):
                choice_message = choice.get("message", {}) if isinstance(choice, Mapping) else {}
                # OpenAI/OpenRouter returns reasoning as a plain string
                reasoning_text = choice_message.get("reasoning")
                if isinstance(reasoning_text, str) and reasoning_text.strip():
                    message = _with_reasoning(message, reasoning_text)
                    generation = ChatGeneration(
                        message=message,
                        generation_info=generation.generation_info,
                    )
            generations.append(generation)

        return ChatResult(generations=generations, llm_output=result.llm_output)

    # ------------------------------------------------------------------
    # Streaming: extract delta.reasoning
    # ------------------------------------------------------------------

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        # Skip Responses-API style deltas
        if chunk.get("type") == "content.delta":
            return None

        token_usage = chunk.get("usage")
        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
        usage_metadata = (
            _create_usage_metadata(token_usage, chunk.get("service_tier"))
            if token_usage
            else None
        )

        if len(choices) == 0:
            generation_chunk = ChatGenerationChunk(
                message=default_chunk_class(content="", usage_metadata=usage_metadata),
                generation_info=base_generation_info,
            )
            return generation_chunk

        choice = choices[0]
        delta = choice.get("delta")
        if delta is None:
            return None

        message_chunk = _convert_delta_to_message_chunk(delta, default_chunk_class)
        generation_info = {**base_generation_info} if base_generation_info else {}

        if finish_reason := choice.get("finish_reason"):
            generation_info["finish_reason"] = finish_reason
            if model_name := chunk.get("model"):
                generation_info["model_name"] = model_name
            if system_fingerprint := chunk.get("system_fingerprint"):
                generation_info["system_fingerprint"] = system_fingerprint

        logprobs = choice.get("logprobs")
        if logprobs:
            generation_info["logprobs"] = logprobs

        # Extract reasoning from delta
        reasoning_text = delta.get("reasoning")
        if isinstance(message_chunk, AIMessageChunk):
            if usage_metadata:
                message_chunk.usage_metadata = usage_metadata
            if isinstance(reasoning_text, str) and reasoning_text:
                message_chunk = _with_reasoning(
                    message_chunk, reasoning_text, preserve_whitespace=True
                )

        return ChatGenerationChunk(
            message=message_chunk,
            generation_info=generation_info or None,
        )


class PatchedAzureChatOpenAI(AzureChatOpenAI):
    """AzureChatOpenAI adapter that captures reasoning_content (Kimi-K2.5, GLM-5 etc.).

    Some models served via an Azure-style proxy return thinking content in
    ``choices[0].message.reasoning_content`` rather than the OpenAI standard
    ``choices[0].message.reasoning``.  This adapter:
    1. Extracts both fields and stores in ``additional_kwargs.reasoning_content``.
    2. Passes ``reasoning_content`` back on assistant messages in multi-turn
       conversations (required by Kimi-K2.5 when thinking is enabled).
    """

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        original_messages = self._convert_input(input_).to_messages()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        # Pass reasoning_content back on assistant messages (multi-turn requirement)
        payload_messages = payload.get("messages", [])
        if len(payload_messages) == len(original_messages):
            for payload_msg, orig_msg in zip(payload_messages, original_messages):
                if payload_msg.get("role") == "assistant" and isinstance(orig_msg, AIMessage):
                    rc = orig_msg.additional_kwargs.get("reasoning_content")
                    if rc is not None:
                        payload_msg["reasoning_content"] = rc
        else:
            ai_messages = [m for m in original_messages if isinstance(m, AIMessage)]
            assistant_payloads = [(i, m) for i, m in enumerate(payload_messages) if m.get("role") == "assistant"]
            for (idx, payload_msg), ai_msg in zip(assistant_payloads, ai_messages):
                rc = ai_msg.additional_kwargs.get("reasoning_content")
                if rc is not None:
                    payload_messages[idx]["reasoning_content"] = rc

        return payload

    def _create_chat_result(
        self,
        response: dict | Any,
        generation_info: dict | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump()
        choices = response_dict.get("choices", [])

        generations: list[ChatGeneration] = []
        for index, generation in enumerate(result.generations):
            choice = choices[index] if index < len(choices) else {}
            message = generation.message
            if isinstance(message, AIMessage):
                choice_message = choice.get("message", {}) if isinstance(choice, Mapping) else {}
                # Try both field names
                reasoning_text = choice_message.get("reasoning_content") or choice_message.get("reasoning")
                if isinstance(reasoning_text, str) and reasoning_text.strip():
                    message = _with_reasoning(message, reasoning_text)
                    generation = ChatGeneration(
                        message=message,
                        generation_info=generation.generation_info,
                    )
            generations.append(generation)

        return ChatResult(generations=generations, llm_output=result.llm_output)


class MiniMaxAzureChatOpenAI(PatchedAzureChatOpenAI):
    """PatchedAzureChatOpenAI variant for MiniMax models.

    MiniMax rejects ``system`` role messages with error code -4316.
    This class merges any system message into the first user message
    before sending, so the rest of the pipeline can still use SystemMessage
    as usual.
    """

    def _get_request_payload(self, input_: LanguageModelInput, *, stop=None, **kwargs) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = payload.get("messages", [])

        # Collect system texts and remove system-role entries
        system_texts: list[str] = []
        non_system: list[dict] = []
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
                if content:
                    system_texts.append(content)
            else:
                non_system.append(msg)

        if system_texts:
            prefix = "\n\n".join(system_texts)
            # Prepend to the first user message, or insert a new one
            for msg in non_system:
                if msg.get("role") == "user":
                    existing = msg.get("content", "")
                    if isinstance(existing, list):
                        msg["content"] = [{"type": "text", "text": prefix + "\n\n"}] + existing
                    else:
                        msg["content"] = f"{prefix}\n\n{existing}"
                    break
            else:
                non_system.insert(0, {"role": "user", "content": prefix})

        payload["messages"] = non_system
        return payload
