---
name: web-search
description: "Web search and page visit. Use for finding information, researching topics, and reading web pages. search() returns titles/abstracts/URLs; visit() returns full page text with optional goal-based summarization."
allowed-tools:
  - Bash
  - Read
  - Write
---

# Web Search & Visit Skill

Search the web and read pages. Write results to a file in `/mnt/user-data/workspace/` if you need to reference them later.

## Search

```bash
python scripts/search.py "your query" --num 5
```

Output: numbered results with title, abstract, URL.

## Visit a Page

```bash
# Full page text
python scripts/search.py --visit "https://example.com"

# Summarized to a specific goal
python scripts/search.py --visit "https://example.com" --goal "what are the main product features?"
```

## Typical Workflow

```bash
# 1. Search
python scripts/search.py "朱元璋 明朝建立" --num 5

# 2. Visit the most relevant result
python scripts/search.py --visit "https://zh.wikipedia.org/wiki/朱元璋" --goal "生平事迹和政治成就"
```

## Tips

- Use `--goal` when pages are long — it extracts only what's relevant
- Chain search → visit to go from overview to detail
- Save important content: `python scripts/search.py ... > /mnt/user-data/workspace/research.txt`
