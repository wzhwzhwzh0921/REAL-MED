"""OpenRouter chat adapter with lossless reasoning passback for tool turns."""

from copy import deepcopy
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk

from deerflow.models.patched_openai import PatchedChatOpenAI


class ChatOpenRouter(PatchedChatOpenAI):
    """Keep structured reasoning, including opaque signatures, across turns."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("base_url", "https://openrouter.ai/api/v1")
        super().__init__(**kwargs)

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        effort = kwargs.pop("reasoning_effort", self.reasoning_effort)
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        payload.pop("reasoning_effort", None)
        extra = dict(payload.get("extra_body") or {})
        reasoning = dict(extra.get("reasoning") or {})
        if effort:
            reasoning["effort"] = effort
        if reasoning:
            extra["reasoning"] = reasoning
        if extra:
            payload["extra_body"] = extra
        messages = self._convert_input(input_).to_messages()
        for original, converted in zip(messages, payload.get("messages", [])):
            if isinstance(original, AIMessage):
                details = original.additional_kwargs.get("reasoning_details")
                if details is not None:
                    converted["reasoning_details"] = deepcopy(details)
        return payload

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        data = response if isinstance(response, dict) else response.model_dump()
        for generation, choice in zip(result.generations, data.get("choices", [])):
            details = choice.get("message", {}).get("reasoning_details")
            if details is not None:
                generation.message.additional_kwargs["reasoning_details"] = deepcopy(details)
        return result

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info):
        result = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices", [])
        if result and isinstance(result.message, AIMessageChunk) and choices:
            details = (choices[0].get("delta") or {}).get("reasoning_details")
            if details is not None:
                result.message.additional_kwargs["reasoning_details"] = deepcopy(details)
        return result

    @staticmethod
    def _deduplicate_stream_formats(chunk, formats):
        # LangChain concatenates arbitrary strings while merging chunks. A
        # repeated format label is metadata, not a token fragment to concatenate.
        for detail in chunk.message.additional_kwargs.get("reasoning_details", []):
            index, label = detail.get("index"), detail.get("format")
            if index is not None and label is not None:
                if formats.get(index) == label:
                    detail.pop("format")
                else:
                    formats[index] = label
        return chunk

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        formats = {}
        for chunk in super()._stream(messages, stop=stop, run_manager=run_manager, **kwargs):
            yield self._deduplicate_stream_formats(chunk, formats)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        formats = {}
        async for chunk in super()._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
            yield self._deduplicate_stream_formats(chunk, formats)
