"""ByteMCP client for GlobalSearch and TextBrowserView.

Provides fallback web search and web fetch via ByteMCP when primary providers
(Jina, Tavily) are unavailable.
"""

from __future__ import annotations

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

BYTEMCP_ENDPOINT = os.getenv("BYTEMCP_ENDPOINT", "")
SEARCH_TRAFFIC_ID = os.getenv("SEARCH_TRAFFIC_ID", "super_agent")
SEARCH_TRAFFIC_GROUP = os.getenv("SEARCH_TRAFFIC_GROUP", "seed")
TIMEOUT_SECONDS = 30


class ByteMCPClient:
    """Synchronous wrapper around ByteMCP GlobalSearch and TextBrowserView APIs."""

    def _call(self, tool_name: str, arguments: dict) -> dict:
        payload = {
            "name": tool_name,
            "arguments": json.dumps(arguments, ensure_ascii=False),
            "traffic_group": SEARCH_TRAFFIC_GROUP,
            "traffic_id": SEARCH_TRAFFIC_ID,
        }
        if tool_name == "GlobalSearch":
            payload["mcp_namespace"] = "search_tool_api"

        resp = requests.post(
            f"{BYTEMCP_ENDPOINT}/plugin/search/tools/call",
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        result_str = data.get("result", "")
        if result_str:
            return json.loads(result_str)
        return data

    def search(self, query: str, max_results: int = 5) -> str:
        """Run a web search via ByteMCP GlobalSearch. Returns JSON string."""
        try:
            result = self._call("GlobalSearch", {"query": query, "max_results": max_results})
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_msg = f"ByteMCP GlobalSearch failed: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def fetch(self, url: str, description: str = "提取页面主要正文", token_count: int = 4096) -> str:
        """Fetch a URL via ByteMCP TextBrowserView. Returns extracted text."""
        try:
            result = self._call(
                "TextBrowserView",
                {
                    "url": url,
                    "is_offline": True,
                    "description": description,
                    "from_mcp_call": True,
                    "token_count": token_count,
                },
            )
            docs = result.get("documents") or []
            text_parts: list[str] = []
            for doc in docs:
                for block in doc.get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        text_parts.append(block["text"])
            if text_parts:
                return "\n".join(text_parts)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_msg = f"ByteMCP TextBrowserView failed: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
