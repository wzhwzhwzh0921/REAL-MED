import json
import os

import requests
from langchain.tools import tool

from deerflow.config import get_app_config


def _get_serper_api_key() -> str:
    config = get_app_config().get_tool_config("web_search")
    if config is not None and "api_key" in config.model_extra:
        key = config.model_extra.get("api_key")
        if key:
            return key
    return os.environ.get("SERPER_API_KEY", "")


@tool("web_search", parse_docstring=True)
def web_search_tool(query: str) -> str:
    """Search the web.

    Args:
        query: The query to search for.
    """
    config = get_app_config().get_tool_config("web_search")
    max_results = 5
    if config is not None and "max_results" in config.model_extra:
        max_results = config.model_extra.get("max_results")

    api_key = _get_serper_api_key()
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "num": max_results,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("organic", [])[:max_results]
        normalized_results = [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in results
        ]
        return json.dumps(normalized_results, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
