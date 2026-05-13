#!/usr/bin/env python3
"""
CLI: web search and page visit.

Usage:
  python scripts/search.py "query" [--num 10]
  python scripts/search.py --visit "https://example.com" [--goal "what is X?"]
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.web_tools import WebTools

def main():
    parser = argparse.ArgumentParser(description="Web search and page visit")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--num", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--visit", metavar="URL", help="Visit a URL instead of searching")
    parser.add_argument("--goal", help="Summarization goal when visiting a page")
    args = parser.parse_args()

    tools = WebTools()

    if args.visit:
        result = tools.visit(args.visit, goal=args.goal)
        print(f"URL: {result['url']}")
        print(f"Title: {result['title']}")
        print()
        print(result["text"])
    elif args.query:
        results = tools.search(args.query, num=args.num)
        print(results)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
