"""Optional OpenRouter Responses API adapter using the standard SDK transport."""

from typing import Any

from langchain_openai import ChatOpenAI


class ChatOpenRouterResponses(ChatOpenAI):
    """Preserve encrypted reasoning with LangChain's native Responses support."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("base_url", "https://openrouter.ai/api/v1")
        kwargs.setdefault("use_responses_api", True)
        kwargs.setdefault("include", ["reasoning.encrypted_content"])
        kwargs.setdefault("store", False)
        super().__init__(**kwargs)
