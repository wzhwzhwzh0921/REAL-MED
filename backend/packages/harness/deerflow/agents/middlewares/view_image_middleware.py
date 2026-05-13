"""Middleware for injecting image details into conversation before LLM call."""

import json
import logging
from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from deerflow.agents.thread_state import ViewedImageData

logger = logging.getLogger(__name__)


class ViewImageMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    viewed_images: NotRequired[dict[str, ViewedImageData] | None]


class ViewImageMiddleware(AgentMiddleware[ViewImageMiddlewareState]):
    """Injects image details as a human message before LLM calls when view_image tools have completed.

    For models that support vision natively, injects raw base64 image data so the model can
    see the image directly.

    For models that do NOT support vision, uses a proxy vision model (the first model with
    supports_vision=True in config) to describe the image in text, then injects the text
    description instead. This allows all models to benefit from view_image.
    """

    state_schema = ViewImageMiddlewareState

    def __init__(self, model_name: str | None = None) -> None:
        from deerflow.config import get_app_config

        config = get_app_config()
        model_config = config.get_model_config(model_name) if model_name else None
        self._supports_vision: bool = model_config.supports_vision if model_config else False

        # Find proxy vision model for non-vision models.
        # Preference order: gemini-3-flash → first model with supports_vision=True
        self._proxy_model_name: str | None = None
        if not self._supports_vision:
            preferred = ["gemini-3-flash"]
            model_names = {m.name for m in config.models if m.supports_vision}
            for name in preferred:
                if name in model_names:
                    self._proxy_model_name = name
                    break
            if self._proxy_model_name is None:
                for m in config.models:
                    if m.supports_vision:
                        self._proxy_model_name = m.name
                        break
            if self._proxy_model_name:
                logger.info(f"ViewImageMiddleware: model '{model_name}' has no vision — will use '{self._proxy_model_name}' as proxy")
            else:
                logger.warning("ViewImageMiddleware: no vision-capable proxy model found in config")

    def _get_last_assistant_message(self, messages: list) -> AIMessage | None:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg
        return None

    def _has_view_image_tool(self, message: AIMessage) -> bool:
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return False
        return any(tool_call.get("name") == "view_image" for tool_call in message.tool_calls)

    def _all_tools_completed(self, messages: list, assistant_msg: AIMessage) -> bool:
        if not hasattr(assistant_msg, "tool_calls") or not assistant_msg.tool_calls:
            return False
        tool_call_ids = {tool_call.get("id") for tool_call in assistant_msg.tool_calls if tool_call.get("id")}
        try:
            assistant_idx = messages.index(assistant_msg)
        except ValueError:
            return False
        completed_tool_ids = set()
        for msg in messages[assistant_idx + 1 :]:
            if isinstance(msg, ToolMessage) and msg.tool_call_id:
                completed_tool_ids.add(msg.tool_call_id)
        return tool_call_ids.issubset(completed_tool_ids)

    def _describe_via_proxy(self, viewed_images: dict[str, ViewedImageData]) -> str:
        """Call proxy vision model to describe images, return text description."""
        from deerflow.models.factory import create_chat_model

        proxy_model = create_chat_model(self._proxy_model_name)
        descriptions: list[str] = []

        for image_path, image_data in viewed_images.items():
            mime_type = image_data.get("mime_type", "image/jpeg")
            base64_data = image_data.get("base64", "")
            if not base64_data:
                continue
            try:
                msg = HumanMessage(
                    content=[
                        {"type": "text", "text": "Describe this image in detail. Focus on layout, text content, data, charts, and any visually important elements."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}},
                    ]
                )
                response = proxy_model.invoke([msg])
                desc = response.content if isinstance(response.content, str) else str(response.content)
                descriptions.append(f"**{image_path}**:\n{desc}")
            except Exception as e:
                logger.warning(f"Proxy vision model failed for {image_path}: {e}")
                descriptions.append(f"**{image_path}**: (could not describe — {e})")

        return "\n\n".join(descriptions) if descriptions else "No images could be described."

    def _collect_viewed_images(self, state: ViewImageMiddlewareState) -> dict[str, ViewedImageData]:
        """Collect view_image payloads from ToolMessages in message history.

        view_image_tool now stores base64 data in ToolMessage content as JSON
        instead of updating viewed_images state, to avoid LangGraph Command conflicts
        when view_image is called in parallel.
        """
        messages = state.get("messages", [])
        last_assistant_msg = self._get_last_assistant_message(messages)
        if not last_assistant_msg:
            return {}
        try:
            assistant_idx = messages.index(last_assistant_msg)
        except ValueError:
            return {}

        collected: dict[str, ViewedImageData] = {}
        for msg in messages[assistant_idx + 1:]:
            if not isinstance(msg, ToolMessage):
                continue
            content = msg.content if isinstance(msg.content, str) else ""
            if not content.startswith("{"):
                continue
            try:
                data = json.loads(content)
                if data.get("__view_image__"):
                    path = data["path"]
                    collected[path] = {"base64": data["base64"], "mime_type": data["mime_type"]}
            except Exception:
                pass
        return collected

    def _create_image_details_message(self, state: ViewImageMiddlewareState) -> list[str | dict]:
        # Collect from ToolMessage payloads (primary) then fall back to viewed_images state (legacy)
        viewed_images = self._collect_viewed_images(state)
        if not viewed_images:
            viewed_images = state.get("viewed_images") or {}
        if not viewed_images:
            return ["No images have been viewed."]

        if self._supports_vision:
            # Native vision: inject base64 directly
            content_blocks: list[str | dict] = [{"type": "text", "text": "Here are the images you've viewed:"}]
            for image_path, image_data in viewed_images.items():
                mime_type = image_data.get("mime_type", "unknown")
                base64_data = image_data.get("base64", "")
                content_blocks.append({"type": "text", "text": f"\n- **{image_path}** ({mime_type})"})
                if base64_data:
                    content_blocks.append(
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}
                    )
            return content_blocks
        elif self._proxy_model_name:
            # Proxy vision: get text description from vision model
            logger.info(f"[ViewImageMiddleware] Using proxy model '{self._proxy_model_name}' to describe images")
            description = self._describe_via_proxy(viewed_images)
            return [{"type": "text", "text": f"Here are the images you've viewed (described by vision model):\n\n{description}"}]
        else:
            # No vision available at all
            paths = list(viewed_images.keys())
            return [{"type": "text", "text": f"Image(s) were loaded but no vision model is available to describe them: {paths}"}]

    def _should_inject_image_message(self, state: ViewImageMiddlewareState) -> bool:
        messages = state.get("messages", [])
        if not messages:
            return False
        last_assistant_msg = self._get_last_assistant_message(messages)
        if not last_assistant_msg:
            return False
        if not self._has_view_image_tool(last_assistant_msg):
            return False
        if not self._all_tools_completed(messages, last_assistant_msg):
            return False
        assistant_idx = messages.index(last_assistant_msg)
        for msg in messages[assistant_idx + 1 :]:
            if isinstance(msg, HumanMessage):
                content_str = str(msg.content)
                if "Here are the images you've viewed" in content_str:
                    return False
        return True

    def _inject_image_message(self, state: ViewImageMiddlewareState) -> dict | None:
        if not self._should_inject_image_message(state):
            return None
        image_content = self._create_image_details_message(state)
        human_msg = HumanMessage(content=image_content)
        print("[ViewImageMiddleware] Injecting image details message with images before LLM call")
        return {"messages": [human_msg]}

    @override
    def before_model(self, state: ViewImageMiddlewareState, runtime: Runtime) -> dict | None:
        return self._inject_image_message(state)

    @override
    async def abefore_model(self, state: ViewImageMiddlewareState, runtime: Runtime) -> dict | None:
        return self._inject_image_message(state)
