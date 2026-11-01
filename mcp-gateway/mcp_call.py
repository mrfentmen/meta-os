#!/usr/bin/env python3
"""Generic client for the MCP gateway. Usage:
  mcp_call.py list
  mcp_call.py call <tool_name> '{"arg": "value"}'
Reads gateway URL from backends.json (or MCP_GATEWAY_URL env).
"""
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "backends.json").read_text())
URL = os.environ.get("MCP_GATEWAY_URL", f"http://127.0.0.1:{CFG.get('port', 8931)}/mcp")


@asynccontextmanager
async def _session():
    # trust_env=False: the sandbox's proxy env vars confuse httpx's URL
    # parsing (bracketed IPv6 entries in no_proxy); the gateway is
    # localhost-only so no proxy is needed or wanted.
    import httpx
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(headers=headers, timeout=timeout or 30,
                                 auth=auth, trust_env=False)

    async with streamablehttp_client(URL, httpx_client_factory=factory) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def cmd_list() -> None:
    async with _session() as session:
        for t in (await session.list_tools()).tools:
            print(f"- {t.name}: {(t.description or '')[:100]}")


async def cmd_call(name: str, args_json: str) -> None:
    args = json.loads(args_json) if args_json else {}
    async with _session() as session:
        result = await session.call_tool(name, args)
        if result.isError:
            print("ERROR:", file=sys.stderr)
        for block in result.content:
            if hasattr(block, "text"):
                print(block.text)
            else:
                print(json.dumps(block.model_dump(), indent=2)[:4000])


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("list", "call"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "list":
        asyncio.run(cmd_list())
    else:
        if len(sys.argv) < 3:
            print("usage: mcp_call.py call <tool_name> '<json args>'")
            sys.exit(1)
        asyncio.run(cmd_call(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "{}"))


if __name__ == "__main__":
    main()
