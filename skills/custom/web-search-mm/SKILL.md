---
name: web-search-mm
description: "Image search and download. Use when you need images for documents, presentations, or visual content. Searches Google Images via Serper API and downloads to local disk."
allowed-tools:
  - Bash
  - Read
  - Write
---

# Multimodal Web Search Skill

Search and download images. **Do NOT write your own download code** — use the script below.

## Search Images

```bash
python scripts/search.py "query" --num 5
```

Output: numbered results with title, dimensions, image URL, source URL.

## Search + Download

```bash
# Download top 3 results to images/
python scripts/search.py "朱元璋画像" --num 5 --save-dir /mnt/user-data/workspace/images --download 3
```

Downloaded files are saved to `--save-dir` with auto-generated filenames. The script prints the saved filename and size for each image.

## Batch Download (Multiple Keywords)

```bash
python scripts/search.py "朱元璋 肖像" --save-dir /mnt/user-data/workspace/images --download 2
python scripts/search.py "鄱阳湖之战" --save-dir /mnt/user-data/workspace/images --download 2
python scripts/search.py "明孝陵" --save-dir /mnt/user-data/workspace/images --download 2
```

## Tips

- Some images fail to download (403/timeout) — download more than you need (e.g. `--download 3` when you need 1)
- Check what was actually saved: `ls /mnt/user-data/workspace/images/`
- Use the saved filenames (printed by the script) in your downstream code
