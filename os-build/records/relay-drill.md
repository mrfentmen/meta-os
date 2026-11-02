# `crates/relay` — failure drill (B189)

Written from the code, not run. A drill another agent can run on a machine
with a terminal. Start the binary from the repo root:
`cargo run -p relay` (no workspace build needed; this crate has no deps).

## What "inputs stop arriving" means here

The relay's inputs are HTTP requests and the store file. It has no timers, no
peers it calls, and no background work (`crates/relay/src/main.rs:11-29`,
`crates/relay/src/http.rs:574-589`). So "input stops" does not degrade service
by itself — it changes what the next caller sees. The drill therefore removes
one input at a time and names the first observable break.

## D1 — No client ever POSTs

1. Start the binary with no store file.
2. `curl -s localhost:8787/health` → `{"ok":true,"rooms":0,"store":"memory"}`.
3. `curl -s 'localhost:8787/rooms/main/messages'` → `{"room":"main","total":0,"messages":[]}`.

First break: none. An idle relay is healthy; only an empty room is visible.

## D2 — Clients POST but never poll

1. POST 10,000 lines to one room.
2. Watch RSS.

First break: memory growth, unbounded. `RoomStore.rooms` is a plain
`HashMap<String, Vec<String>>` with no cap (`crates/relay/src/store.rs:17-20`);
with a store file the same lines also grow the file without limit. There is
no retention, no compaction, no eviction.

## D3 — The store file's disk fills

1. `RELAY_STORE_FILE=/tmp/relay.jsonl cargo run -p relay`.
2. Fill the filesystem; POST one message.

Observed by code path: `append` pushes into memory **first**, then tries the
file; on error it prints `Meta Nuntius: store append failed: <err>` and still
returns the index (`crates/relay/src/store.rs:60-78`). The POST is 201.

First break: durability, silently. The caller believes the line is stored; it
is only in memory and disappears on restart.

## D4 — The store file is deleted while the relay runs

1. Start with `RELAY_STORE_FILE=/tmp/relay.jsonl`, POST one line.
2. `rm /tmp/relay.jsonl`.
3. POST another line.

Observed by code path: `OpenOptions::create(true).append(true)` recreates the
file with only the new line (`crates/relay/src/store.rs:64-72`). The first
line stays in memory but is no longer on disk.

First break: history. A restart reloads one line, not two.

## D5 — The store file becomes unreadable at boot

1. `chmod 000 /tmp/relay.jsonl` (or point `RELAY_STORE_FILE` at a directory).
2. Start the binary.

Observed by code path: `read_to_string` fails, `Relay::with_viewer` panics with
`Meta Nuntius: failed to read store file <path>: <err>`
(`crates/relay/src/store.rs:41`, `crates/relay/src/http.rs:395-401`).

First break: boot. No listener is created. This is parity with the Node
original's `readFileSync` throw, but it is a hard stop.

## D6 — The viewer disappears

1. `rm relay/viewer.html` (or unset `RELAY_VIEWER_FILE` and run from `/tmp`).
2. `curl -i localhost:8787/`.

Observed by code path: 500, `text/plain`,
`viewer.html is missing beside relay.mjs` (`crates/relay/src/http.rs:437-455`).
`/health`, POST and GET message routes all keep working.

First break: only the human view. Machines are unaffected.

## D7 — One client sends a body with no end

1. Open a TCP socket, send
   `POST /rooms/main/messages HTTP/1.1` and a `Content-Length: 16384`, then
   send only 10 bytes.

Observed by code path: `read_exact` blocks until the remaining bytes arrive or
the socket errors; the handler thread is held (`crates/relay/src/http.rs:600-620`).
There is no read timeout and one thread per connection
(`crates/relay/src/http.rs:574-589`).

First break: one server thread per stalled client. Enough stalled clients
exhaust threads; the listener still accepts.

## D8 — A handler panics while holding the relay lock

1. Only reachable through a bug; none is known in the paths above.

Observed by code path: `relay.lock()` returns `Err`, and the connection gets
500 `{"error":"internal error: relay lock poisoned"}`
(`crates/relay/src/http.rs:627-638`). Every later request repeats the 500;
there is no recovery path.

First break: every route, permanently, until restart.

## D9 — The port is taken

1. Start any listener on 8787, then start the relay.

Observed by code path: panic
`Meta Nuntius: failed to bind port 8787: <err>` (`crates/relay/src/main.rs:24-26`).

First break: boot, loudly.

## Drill order

Run D1, D2, D3, D5, D6, D7, D9 in that order. D4 and D8 are state drills that
need the earlier steps' files. Each step's expected text is quoted above; a
step that prints something else is a finding against this record, not a pass.
