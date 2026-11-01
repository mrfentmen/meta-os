# MCP gateway — the crew's shared tool backend (repo copy)

Committed 2026-11-01 on the boss's order, because the gateway previously
existed only on Pax's VM (`127.0.0.1:8931`) and nowhere else — which is
why other crew sessions could not connect. This folder is the full
gateway: one Python file, one config, one client. Run your own instance
from this copy; instances are local, there is no shared remote gateway.

## What it is

`gateway.py` starts every stdio MCP server listed in `backends.json`,
aggregates their tools as `<prefix>__<tool>`, and serves them over
Streamable HTTP at `http://127.0.0.1:8931/mcp`. `mcp_call.py` is a
command-line client: `mcp_call.py list` and
`mcp_call.py call <tool> '<json args>'`.

The committed `backends.json` is Pax's live config: 105 backends,
including the boss's own servers wired 2026-11-01 — `goose__*`
(goose-mcp 1.1.0, 17 tools), `lobster__*` (lobster-mcp 1.1.0, 16
tools), `browser__*` (@mrfentmen/browser-mcp, 6 tools) — plus
context7, fetch, fs (filesystem), memory, think (sequential thinking),
shell, mcpterminal, playwright, and the local keyless server fleet.
Tool names the boss ordered that do not exist under those names
anywhere (analysis, research, secstack) are NOT in this config, because
they have not been published under those names.

## Run your own instance

1. Python venv in this folder with the SDK:
   `python3 -m venv .venv && .venv/bin/pip install mcp starlette uvicorn`
2. Install the backend servers you want. The paths in `backends.json`
   are absolute paths on Pax's VM (`/home/hatch/workspace/mcp-servers/…`);
   either mirror that layout or edit the args to your own install
   paths. The boss's three install in minutes from npm:
   `npm install goose-mcp lobster-mcp @mrfentmen/browser-mcp`.
   The official servers (context7, filesystem, memory,
   sequential-thinking, fetch, shell, terminal, playwright) are public
   npm / PyPI packages named in each backend's args.
3. Trim `backends.json` to the backends you actually installed — the
   gateway skips a backend that fails to start and keeps serving the
   rest, but a trimmed config boots far faster (105 backends take
   about 2.5 minutes to all come up).
4. Start: `./start-gateway.sh` — wait until it prints
   `gateway: serving Streamable HTTP on 127.0.0.1:8931/mcp`.
5. Point your MCP client at `http://127.0.0.1:8931/mcp`, or use
   `mcp_call.py` directly.

## Notes

- No credentials live in this folder: `backends.json` holds commands,
  paths, and a no_proxy list only (checked at commit time). Servers
  that need keys read them from your own environment or vault.
- `browser__` needs Chrome: set `CHROME_PATH` in its backend env to a
  Chrome/Chromium binary (on Pax's VM it points at a wrapper that adds
  `--no-sandbox`; page loads from Pax's sandbox are proxy-blocked, the
  playwright backend covers browsing there).
- Pax's live instance on his VM stays the reference config; when the
  boss ships new goose-mcp / lobster-mcp versions, the 30-minute
  update watch pulls them there and posts to crew room 1.
