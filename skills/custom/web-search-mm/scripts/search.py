#!/usr/bin/env python3
"""
CLI: image search and download.

Usage:
  python scripts/search.py "query" [--num 5] [--save-dir DIR] [--download N]
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.mm_tools import MMSearchToolsWithVision

def main():
    parser = argparse.ArgumentParser(description="Image search and download")
    parser.add_argument("query", help="Image search query")
    parser.add_argument("--num", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--save-dir", default="images", help="Directory to save downloaded images")
    parser.add_argument("--download", type=int, default=0, metavar="N",
                        help="Download top N results (0 = search only, default: 0)")
    args = parser.parse_args()

    tools = MMSearchToolsWithVision(image_save_dir=args.save_dir)

    results = tools.image_search(args.query, num=args.num)
    print(results)

    if args.download > 0:
        print(f"\nDownloading top {args.download} images to: {args.save_dir}")
        for i in range(1, args.download + 1):
            detail = tools.click_image(i)
            img_url = detail.get("image_url") or detail.get("thumbnail")
            if img_url:
                result = tools.download_image(img_url)
                path = result.get("local_path", "")
                size = result.get("size_bytes", 0)
                if path:
                    print(f"  [{i}] {os.path.basename(path)} ({size} bytes)")
                else:
                    print(f"  [{i}] failed")

if __name__ == "__main__":
    main()
