#!/usr/bin/env python3
"""MCP gateway: aggregates stdio MCP servers and exposes them over Streamable HTTP.

Config: backends.json next to this file:
  {"port": 8931, "backends": [{"prefix": "openlibrary", "command": "node",
    "args": ["/path/to/dist/index.js"]}, ...]}

Downstream tools appear as <prefix>__<tool>, e.g. openlibrary__search_books.
Serves Streamable HTTP at http://127.0.0.1:<port>/mcp
"""
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import mcp.types as types
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "backends.json").read_text())


# The MCP SDK's stdio client only inherits a tiny allowlist of env vars
# (HOME, PATH, ...), so proxy settings must be passed explicitly or the
# downstream servers' fetch() calls fail. Merged over the SDK defaults.
PROXY_ENV_KEYS = ("https_proxy", "http_proxy", "HTTPS_PROXY", "HTTP_PROXY",
                  "ALL_PROXY", "all_proxy", "NODE_USE_ENV_PROXY",
                  "no_proxy", "NO_PROXY",
                  # Egress proxy does TLS interception; node needs its CA.
                  "NODE_EXTRA_CA_CERTS")
CHILD_ENV = {k: v for k in PROXY_ENV_KEYS if (v := os.environ.get(k))}


async def main() -> None:
    backends = {}  # prefix -> {"session": ClientSession, "tools": [Tool]}
    stack = AsyncExitStack()

    gateway = Server("mcp-gateway")

    @gateway.list_tools()
    async def _list_tools() -> list[types.Tool]:
        out: list[types.Tool] = []
        for prefix, be in backends.items():
            for t in be["tools"]:
                out.append(types.Tool(
                    name=f"{prefix}__{t.name}",
                    description=f"[{prefix}] {t.description or ''}".strip(),
                    inputSchema=t.inputSchema,
                ))
        return out

    @gateway.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        prefix, _, tool_name = name.partition("__")
        be = backends.get(prefix)
        if not be or not tool_name:
            raise ValueError(f"unknown tool: {name}")
        result = await be["session"].call_tool(tool_name, arguments or {})
        return result.content

    session_manager = StreamableHTTPSessionManager(app=gateway, stateless=True)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with stack:
            for b in CFG["backends"]:
                # Per-backend isolation (2026-09-30): one dead backend must not
                # kill the whole gateway. Skip it with a log line instead.
                try:
                    params = StdioServerParameters(command=b["command"], args=b["args"],
                                                   env={**CHILD_ENV, **(b.get("env") or {})})
                    _read, _write = await stack.enter_async_context(stdio_client(params))
                    session = await stack.enter_async_context(ClientSession(_read, _write))
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    backends[b["prefix"]] = {"session": session, "tools": tools}
                    print(f"gateway: backend '{b['prefix']}' up, {len(tools)} tools", flush=True)
                except Exception as exc:  # noqa: BLE001 - log and keep the gateway alive
                    print(f"gateway: backend '{b['prefix']}' FAILED, skipped: {type(exc).__name__}: {exc}", flush=True)
            async with session_manager.run():
                yield

    async def handle_mcp(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    starlette_app = Starlette(
        lifespan=lifespan,
        routes=[Mount("/mcp", app=handle_mcp)],
    )

    import uvicorn
    port = CFG.get("port", 8931)
    print(f"gateway: serving Streamable HTTP on 127.0.0.1:{port}/mcp", flush=True)
    config = uvicorn.Config(starlette_app, host="127.0.0.1", port=port, log_level="warning")
    await uvicorn.Server(config).serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
