# MCP wiring for the OS build

Owner: Section M (OS-181..OS-192). Written by Buffy 2026-11-01, on the boss's
order to connect a Rust, a Goose and a Lobster MCP before writing OS code.

Every line below is a result, not a plan. Where something could not be wired,
it says so in the same table rather than a paragraph further down.

## The wiring in one table

| Language / layer | MCP server | Status | Evidence |
|---|---|---|---|
| Rust (Layer 0, kernel) | `docs-rs` — npm `@nuskey8/docs-rs-mcp@1.0.1`, MIT | **WIRED, verified live** | Handshake plus two successful tool calls, below |
| Goose (Layer 1, services) | none exists | **NOT POSSIBLE** | No MCP server for the Goose language exists. Substitute is `goose lsp` (a real LSP), not yet installed |
| Lobster (Layer 2, agents) | none exists | **NOT POSSIBLE** | No MCP server and no LSP. Substitute is the docs sources |

## Rust: what was proven, and the exact output

The server was run over stdio and spoken to directly with JSON-RPC, because
that is the only way to prove a server works without a client in the loop.

```
$ python3 os-build/mcp/smoke_mcp.py npx -y @nuskey8/docs-rs-mcp@latest
[stderr] docs.rs MCP server running on stdio
initialize OK: docs-rs 1.0.1
protocol: 2024-11-05
tools (4):
  - docs_rs_search_crates   args:['query', 'per_page', 'sort']  required:['query']
  - docs_rs_readme          args:['crate_name', 'version']       required:['crate_name']
  - docs_rs_get_item        args:['crate_name', 'item_type', 'item_path', 'version']
  - docs_rs_search_in_crate args:['crate_name', 'query', 'version', 'item_type']
```

Two real calls, both against the crate our K1 kernel already depends on:

```
docs_rs_readme {"crate_name":"bootloader"}
  -> 104 chars: "# bootloader Documentation ... An experimental x86_64
     bootloader that works on both BIOS and UEFI systems."

docs_rs_search_in_crate {"crate_name":"bootloader","query":"Bootloader"}
  -> 88 chars: "# Search Results for \"Bootloader\" in bootloader Found 0 items"
```

The second returning 0 items is a valid answer, not a failure: the transport,
the call and the response are all proven, the query simply matched nothing.

## The one broken tool, and why (do not rediscover this)

`docs_rs_search_crates` fails on every call:

```
MCP error -32603: Failed to search crates:
AxiosError: Request failed with status code 403
```

Root cause, isolated by direct curl:

| Request | Result |
|---|---|
| `curl https://crates.io/api/v1/crates?q=bootloader` (no User-Agent) | **403** |
| same with `-H "User-Agent: meta-os-smoke/1.0"` | **200** |
| `curl https://docs.rs/crate/bootloader/latest` | **200** |

crates.io refuses requests with no User-Agent, and this server sends none. So
crate *search* is dead, while every tool that reads docs.rs works. That matters
because the three working tools are the ones that answer "what is this crate's
API", which is the reason the rule exists ("use the rustdocs MCP tools for crate
APIs instead of guessing them").

Workaround until upstream fixes it, in order of preference:

1. Search crates.io by hand or with `curl` (with a User-Agent), then ask the MCP
   for the docs. No fork, no patching.
2. If `search_crates` becomes load-bearing, fork the server and set a default
   User-Agent on its axios client. Record the fork here if that happens.

Also rejected, for the record: npm `mcp-rust-docs@0.1.0`. It ships a Linux
binary and dies on this Mac with `cannot execute binary file`. Its repo is named
`mcp-rust-docs-deprecated`, so it is not the long term answer anyway.

## How a client actually loads this

Three configs are committed, all additive, all keyless:

| File | Client |
|---|---|
| `opencode.json` (repo root) | OpenCode. This is the one OS-182 asked for: `mcp.docs-rs`, `type: local` |
| `.mcp.json` (repo root) | Claude Code and other `mcpServers` clients, project scope |
| `.vscode/mcp.json` | VS Code, and anything using the `servers` shape |

**A restart is required.** MCP servers are spawned by the client at startup, so
these files do nothing to a session that is already running. Restart OpenCode
(or reload the VS Code window) and `docs_rs_*` should appear in the tool list.

**What is not claimed:** the session that wrote this file had no MCP tools
bound to it. The proof above is a direct stdio conversation with the server, not
a tool call made through a client. Nobody should read this file as "the agent
had the tools while it wrote this".

## Goose and Lobster: the honest answer

Checked again 2026-11-01, searching for each language's name plus MCP. There is
no MCP server for either. The only hits are Block's *unrelated* AI agent, also
called goose, which is an MCP **client** with dozens of extensions and says
nothing about our Layer 1.

**Goose, the real tooling.** `goose lsp` serves the Language Server Protocol
over stdio, and the release archive ships `vscode/goose-language.vsix`. For
coding, an LSP beats a docs MCP: it gives completions, diagnostics, hover and
go-to-definition against the actual standard library rather than prose about it.

Blocked on one thing: **Goose is not installed on this machine**, so `goose lsp`
could not be smoke called. Install order is in
`../research/ecosystem-watch.md` §2: unpack the macOS release, add it to `PATH`,
run `xattr -dr com.apple.quarantine`, then `goose version` and `goose toolchain`
to record what it found. After that, `goose lsp` is a one line addition to the
same config files with `command: ["goose", "lsp"]`.

**Lobster.** No MCP and no LSP found. The honest substitute is the docs set
(strlen.com/lobster and aardappel.github.io/lobster) plus a build/run note, and
that is what OS-184's "state which case it is" should say.

## Slot reserved: the Goose and Lobster MCPs being built now

The boss is building these as of 2026-11-01. The wiring below is written and
waiting, so the day they exist it is a paste and a smoke call, not a research
task. The names `goose` and `lobster` are reserved here, not in the configs:
only `docs-rs` is in them today. A config entry pointing at a server that does
not exist yet is worse than no entry, because it fails at startup and can take
the working server's tool load down with it.

Drop-in for `opencode.json`:

```json
"goose": {
  "type": "local",
  "command": ["npx", "-y", "<package-or-path>"],
  "enabled": false
},
"lobster": {
  "type": "local",
  "command": ["npx", "-y", "<package-or-path>"],
  "enabled": false
}
```

The same two entries go in `.mcp.json` under `mcpServers` and in
`.vscode/mcp.json` under `servers`, with `command`/`args` split instead of an
array. Flip `enabled` to `true` only after the smoke passes.

Proof required before flipping it on, in this order:

1. `python3 os-build/mcp/smoke_mcp.py <cmd...>` prints
   `initialize OK` and the tool list.
2. One real call passes with `SMOKE_TOOL` and `SMOKE_ARGS` set.
3. Both lines pasted into the table at the top of this file.

What I need from whoever builds them, because it changes the entry: is it a
stdio process or an HTTP endpoint (the command array above assumes stdio), what
is it called on npm or where does the binary live, does it need a key or env
var, and what is its license. **If it needs a key it does not go in a committed
file**: use the client's secret store or an environment variable and note it
here.

## The full set, wired 2026-11-01 on the boss's order

Twelve servers he named, plus the three the security stack already had and the
Rust docs server above. Every row was proven by spawning the server and
speaking `initialize` plus `tools/list` to it, not by reading its config.

```
14/14 servers answered
```

| Config name | Server / version | Tools | What it is for |
|---|---|---|---|
| `analysis` | analysis 1.0.0 | 6 | Endpoint mining, response diffs, JWT decode, corpus search |
| `browser` | browser-mcp 1.0.0 | 10 | Open a page, screenshot, links, headings, run script, DNS records |
| `context7` | Context7 4.4.4 | 2 | Library documentation lookup by library id |
| `docs-rs` | docs-rs 1.0.1 | 4 | Rust crate docs and API items (see the 403 note above) |
| `fetch` | fetch-mcp 0.0.5 | 2 | Fetch a URL, fetch a YouTube transcript |
| `filesystem` | secure-filesystem 2.0.0 | 14 | Read/write files, rooted at `/Users/test/Desktop` |
| `mcp-advisor` | mcp-advisor 0.5.1 | **0** | See the note below: starts, but exposes no tools |
| `mcp-shell` | terminal-mcp-server 1.0.0 | 1 | Arbitrary terminal |
| `mcp-terminal` | mcp-shell-server 2.8.1 | 13 | Shell exec with async execution records |
| `memory` | memory-server 2.0.0 | 9 | Knowledge graph entities, relations, observations |
| `research` | research 0.1.0 | 3 | `market_check`, `trend`, `suggest` |
| `secstack` | secstack 1.0.0 | 5 | nuclei, httpx, ffuf, header audit, raw fetch. Scope enforced |
| `sequential-thinking` | sequential-thinking 2.0.0 | 1 | Structured multi-step reasoning |
| `state` | state 1.0.0 | 9 | The engagement ledger (confirmed / refuted / untested) |

Where they live: `/Users/test/Desktop/.agents/mcp.json`, the project-scoped
client config (`.agents/mcp.json` under the working directory). It is outside
this repo on purpose: it is a client config for one machine, not something the
crew VMs should inherit. All fourteen entries are stdio, all keyless, and every
`env` value in them is a filesystem path, so nothing secret is in the file.

**`mcp-advisor` answers with zero tools.** It initializes cleanly and reports
version 0.5.1, so the process and the wiring are correct, but it exposes no
callable tools, which is consistent with it being an advisory server that speaks
in resources or instructions rather than actions. Counting it as "12 connected"
would be wrong: eleven of the fourteen give me callable tools.

**Restart is still required.** These were verified by talking to each server
directly. They become tools in a session only after the client restarts, so the
next session is the first one that can actually use them.

**The parked program stays parked.** `secstack` and `analysis` are wired
because they were already live in this workspace, not because the cybersecurity
program started. The boss's park order stands: no scanning, no engagement work,
no program design. Their scope file is enforced by the server, not by me.

## Rule card (OS-187)

- **Keyless first.** Everything wired here needs no account, no token, no key.
  If a future server needs one, it does not go in a committed file.
- **Secrets never in files.** No API keys in `opencode.json`, `.mcp.json` or
  `.vscode/mcp.json`. Use the client's own secret store or an environment
  variable, and note in this file that you did.
- **Every wiring is proven by a call.** A config file is not a wiring. Paste the
  `initialize` line and one tool result, or it is not wired.
- **Restart is part of the procedure.** A wired server with no restart is a
  file, not a tool.

## If the local gateway is down (OS-189)

The `mcp-gateway` in the parent workspace (`../mcp-gateway`, aggregated onto
`127.0.0.1:8931/mcp`) is a different machine's setup: it references a sandbox
path `/run/hatch/egress-tls` and was not running here (`pgrep -fl gateway.py`
found nothing, and its log ends in an `EPIPE` from a dead backend).

Nothing in this file depends on it. The `docs-rs` wiring is a direct stdio
server, which is deliberately the simplest thing that cannot be broken by a
gateway. If a lane needs the gateway, restart it with
`../mcp-gateway/start-gateway.sh`; do not rebuild it from this file.
