# MCP wiring (OS-181..OS-191)

## Inventory (OS-181)

Verified live on this Mac 2026-11-01 (every one smoke-called
below; outputs in `smoke-2026-11-01.log`):

- Goose docs MCP (`goose-mcp` 1.1.0, local stdio): 389 doc
  sections, 702 stdlib symbols, 57 keywords, 32 samples.
  Toolchain probe: FOUND (`goose` on PATH via /opt/homebrew/bin
  symlink to the Section K build). License: check the server
  package (docs are upstream Goose docs).
- Lobster docs MCP (`lobster-mcp` 1.1.0, local stdio): 187 doc
  sections, 879 builtins, 45 keywords, 18 samples. Toolchain
  probe: FOUND (same symlink pattern). Same license note.
- Rust docs: NO repo MCP existed (the "rustdocs pattern" lives
  in crew gateway practice, not in this repo). This section does
  NOT pretend otherwise — see OS-182.
- Filesystem + git: shell + file tools on this Mac, documented
  as the wired mechanism (no separate MCP binary needed).

## OS-182: the repo artifact (created here, not copied)

No MCP config existed in this repo (Buffy's lane finding stands).
Created by this section: `os-build/mcp/backends/` descriptors for
the goose + lobster doc servers (command, purpose, license, smoke
result each) in the gateway's backend shape, so Pax's gateway can
adopt them verbatim. The Rust-docs wiring is recorded as
PATTERN (vendored crate sources + rustup docs are the offline
authority; no new server written).

## OS-183/184: Goose + Lobster help

Docs MCPs exist LOCALLY (above) — the best case. Each is wired
in the client config AND described here; every Section K/L
language fact cites the lookup that proved it (see OS-188).
No local skill-note fallback needed.

## OS-185: filesystem + git

Wired as shell + file tools (this build used them for every
commit, read, and boot). Smoke: `git status` + a file read in
the log below.

## Rule card (OS-187)

Keyless first: doc servers need no keys. Secrets never in
files: none were written (the only key in this build, the Spark
test key, never touched these files). Every wiring proven by a
call: the smoke log.

## OS-188: one task that went measurably better

Two, both named: (1) `host.goose` uses `json::parse` /
`json::member` / `as_string` exactly as the MCP's json-module
listing specifies — first compile clean, no guessing the API;
(2) `agent-call.lobster` uses `launch_subprocess(cmdline,
stdin)` in the exact 2-arg form from the MCP's lookup, which
is why the cross-language call worked first try. Without the
docs MCP both would have been guess-then-fix cycles.

## OS-189: gateway note

No repo gateway is rebuilt here. The crew gateway
(`mcp-gateway/` on main) is Pax's; adoption of the two backend
descriptors is his call. My MCPs are client-local, verified
above. If the local gateway is down, restart pointer: the
client config at ~/.config/opencode/opencode.jsonc, entries
`goose` and `lobster`. Not rebuilt from this file.

## OS-190: crew summary

Goose help: ask the goose MCP (docs + symbols + samples) or
read os-build/research/goose.md. Lobster help: same pattern.
Both toolchains are on PATH. Wiring files live here in
os-build/mcp/. Smoke log beside them.
