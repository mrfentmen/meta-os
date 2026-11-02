# `crates/relay` — callers and their expectations (B187)

Search scope: the whole repo for `relay::`, `use relay`, `RELAY_PORT`,
`RELAY_STORE_FILE`, `RELAY_VIEWER_FILE`, `Meta Nuntius`, `nuntius`, and
`trio-result`. Every hit is listed or grouped below.

## Rust callers

**None.** No workspace crate depends on `relay`:
`crates/relay/Cargo.toml` has no dependants in any other `Cargo.toml`, and
`relay::http` is reached only from `crates/relay/src/main.rs:23-28` and the
crate's own tests. The `relay` binary is standalone.

## The Node original is still the process the stack launches

`crates/stack` models the relay as a host process:

- `crates/stack/src/lib.rs:185-191` — argv `["node", "relay/relay.mjs"]`,
  env `RELAY_PORT`, name "Meta Nuntius relay".
- `crates/stack/src/lib.rs:130,142` — resolves `RELAY_PORT`, default `8787`.
- `crates/stack/src/lib.rs:237` — prints the viewer URL
  `http://127.0.0.1:<port>/`.

Expectation: a child process on `RELAY_PORT` serving `/health` and `/`.
It does **not** expect the Rust binary, and nothing in the stack points at
`crates/relay`. Flag: the port exists, the wiring does not.

`run-stack.sh`:

- line 31 — `RELAY_PORT="${RELAY_PORT:-8787}"`.
- line 74 — `RELAY_PORT="$RELAY_PORT" node relay/relay.mjs &`.
- lines 76, 98 — waits on `/health`, prints the viewer URL.

Expectation: Node on PATH, repo-relative `relay/relay.mjs`, port from env.

## Network clients (HTTP, not crate callers)

`server/queue/trio_agent.py:87` (hook documented at lines 40-90):
posts one NOTIFY line to `TRIO_RELAY_URL` after a finished job.
Expects HTTP 201 with JSON; treats any failure as fire-and-forget and never
fails the job.

`tests/queue-python/test_queue.py:461`: exercises the optional hook against a
stub HTTP server, asserting the `relay: NOTIFY:` line shape, not the Rust
server.

## Documentation references (no executable expectation)

- `README.md:194` — lists `relay/` as the product's own relay.
- `BATCHES.md:112` — B08 names `relay/relay.mjs` as the port source.
- `docs/AGENTIC.md:14,55,71-73,188-193` — the relay as the NOTIFY sink and
  durable log when `RELAY_STORE_FILE` is set.
- `RUNBOOK.md:61,89` — viewer URL and the expected NOTIFY line.
- `board/README.md:16,76` — the board speaks the same line protocol.
- `os-build/ROOT_MANIFEST.md:22` — host process, not kernel-managed.
- `SUPER_PROMPT.md:304` — T086 writes the port task; status UNCOMPILED until
  gate 1 passes.
- `MAC_RUN_REPORT.md:58` — the Node relay was up on 8787 in that run.

## Callers expecting something the crate does not do

1. **`crates/stack` expects a supervisor-managed process**, but the Rust
   binary has no graceful stop and no readiness handshake beyond binding the
   port (`crates/relay/src/http.rs:574-589`). Node exits on signal; the Rust
   thread-per-connection loop does not.
2. **`trio_agent.py` expects a JSON 201 body**; the Rust route does return it
   (`crates/relay/src/http.rs:526-530`), so this one matches.
3. **The viewer URL printed by the stack is `127.0.0.1`**, while the binary
   binds `0.0.0.0` (`crates/relay/src/main.rs:24`). Reachable either way, but
   the printed URL is not the bind address.
4. **`run-stack.sh` invokes Node**, so swapping in the Rust binary is a change
   to that script plus `crates/stack`; neither is done in this crate.
