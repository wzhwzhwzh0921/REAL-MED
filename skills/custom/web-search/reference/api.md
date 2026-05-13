# Web Tools API Reference

## Configuration

### Pre-configured API Keys

```python
import os
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
```

### External APIs

| API | Endpoint | Purpose |
|-----|----------|---------|
| Serper | `https://google.serper.dev/search` | Google Search |
| Jina Reader | `https://r.jina.ai/{url}` | Page content extraction |

## WebTools Class

### Constructor

```python
WebTools(
    serper_api_key: str = None,  # Uses default if not provided
    jina_api_key: str = None,    # Uses default if not provided
    symbol: str = "§",           # Symbol for result numbering
    timeout: int = 30,           # Request timeout in seconds
    max_retries: int = 2,        # Max retry attempts
    retry_delay: float = 0.8     # Base delay between retries
)
```

### Methods

#### search(query, num=10, gl="us", hl="en")

Perform Google search via Serper API.

**Parameters:**
- `query` (str): Search query
- `num` (int): Number of results (1-10)
- `gl` (str): Geolocation code (default: "us")
- `hl` (str): Language code (default: "en")

**Returns:** `str` - Formatted results

**Example:**
```python
tools = WebTools()
results = tools.search("machine learning", num=5)
# Returns:
# 【§1】Title: ... Abstract: ...。url: ...
# 【§2】Title: ... Abstract: ...。url: ...
```

#### visit(url, max_chars=50000)

Fetch webpage content.

**Parameters:**
- `url` (str): URL to visit
- `max_chars` (int|float): Max characters (use `float('inf')` for unlimited)

**Returns:** `Dict[str, str]` with keys:
- `url`: Final URL
- `title`: Page title
- `text`: Extracted content

**Example:**
```python
page = tools.visit("https://example.com")
print(page["title"])
print(page["text"])
```

#### click(index, max_chars=50000)

Click a search result by reference number.

**Parameters:**
- `index` (int): Reference number from search results
- `max_chars` (int|float): Max characters

**Returns:** Same as `visit()`

**Example:**
```python
tools.search("AI news")
page = tools.click(1)  # Click §1
```

#### get_stats()

Get usage statistics.

**Returns:** `Dict[str, int]` with:
- `search_count`: Number of searches
- `visit_count`: Number of page visits

#### reset_stats()

Reset usage counters to zero.

## Tool Executor

### execute_tool(tool_name, tool_args, tools_instance=None)

Execute a tool by name.

**Parameters:**
- `tool_name` (str): "search", "visit", or "click"
- `tool_args` (dict): Arguments for the tool
- `tools_instance` (WebTools): Optional existing instance

**Returns:** `str` - Tool output

**Example:**
```python
from scripts.web_tools import execute_tool

result = execute_tool("search", {"query": "Python tutorial", "num": 5})
print(result)
```

## Tool Definitions (TOOL_DEFINITIONS)

Ready-to-use tool definitions for LLM function calling:

```python
from scripts.web_tools import TOOL_DEFINITIONS

# Use with OpenAI-compatible APIs
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    tools=TOOL_DEFINITIONS
)
```

## Error Handling

All methods may raise `WebToolsError`:

```python
from scripts.web_tools import WebTools, WebToolsError

tools = WebTools()
try:
    result = tools.search("query")
except WebToolsError as e:
    print(f"Error: {e}")
```

## Rate Limits

- Serper API: ~100 searches/day (free tier)
- Jina Reader: ~1000 requests/day (free tier)

Monitor usage with `get_stats()` to avoid hitting limits.
