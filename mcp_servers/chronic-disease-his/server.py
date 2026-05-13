#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIS MCP Server — chronic disease management HIS simulator.

Treatment results are written to $OUTPUTS_DIR/his_result.jsonl.

Startup (managed by DeerFlow via extensions_config):
    python3 ${REPO_ROOT}/mcp_servers/chronic-disease-his/server.py
"""

import asyncio
import json
import os
import sys
from typing import Any

# Make sure same-directory session.py / tools.py are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from session import HISSession
from tools import TOOL_DEFINITIONS, dispatch


def _resolve_output_path() -> str:
    """Output path: prefer $OUTPUTS_DIR/his_result.jsonl, fall back to /tmp/his_result.jsonl."""
    outputs_dir = os.environ.get("OUTPUTS_DIR", "")
    if outputs_dir:
        os.makedirs(outputs_dir, exist_ok=True)
        return os.path.join(outputs_dir, "his_result.jsonl")
    return "/tmp/his_result.jsonl"


def create_server() -> tuple:
    output_path = _resolve_output_path()
    session = HISSession(output_path=output_path)
    server = Server("chronic-disease-his")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        result = dispatch(name, arguments, session)
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False),
        )]

    return server, session


async def main():
    server, session = create_server()

    print(f"HIS MCP Server started", file=sys.stderr)
    print(f"  output path: {session.output_path}", file=sys.stderr)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="chronic-disease-his",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

    # We do NOT flush on server exit: MCP stdio may start a fresh process per tool call,
    # and flushing early would produce JSONL lines holding only a single tool call's
    # isolated state — and once state is removed, the next process can't accumulate
    # earlier records. The state is already persisted by _save_state(); the next
    # process matches via _session_output_path and continues. A real flush only
    # happens inside submit_orders.
    if session.patient_loaded and not session.submitted:
        print(
            f"Session not submitted; state retained at {session._state_path}, "
            f"the next MCP process will continue.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    asyncio.run(main())
