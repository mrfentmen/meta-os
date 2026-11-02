# `crates/relay` — behaviours the Rust port does not carry (B185)

The original behind this crate is **Node**, not Python: `relay/relay.mjs`
(275 lines) with `relay/relay.test.mjs` and `relay/README.md`. The task
template says "Python original (os/ tree)"; the crate header and `BATCHES.md`
B08 both name the Node file, so this list compares against that source.
Each gap names the upstream line and what the Rust port does instead.
These are tasks for the owner; none is ported here.

## G1 — Module-relative viewer path

- Upstream: `VIEWER_PATH = path.join(HERE, "viewer.html")`
  (`relay/relay.mjs:49-50`), read per request at `relay/relay.mjs:156-168`.
- Rust: `RELAY_VIEWER_FILE`, then cwd-relative `relay/viewer.html`
  (`crates/relay/src/http.rs:404-417`).
- Task: resolve the viewer beside the executable or embed the asset; today a
  binary run from another directory answers 500 on `/`.

## G2 — Chunked / streamed request bodies

- Upstream: `req.on("data")` accumulates regardless of transfer framing
  (`relay/relay.mjs:98-118`).
- Rust: only `Content-Length` is honoured; chunked requests read a zero-length
  body (`crates/relay/src/http.rs:600-625`).
- Task: parse `Transfer-Encoding: chunked` or state the limitation in the
  README the image ships.

## G3 — Invalid UTF-8 in a POST body

- Upstream: `Buffer.concat(chunks).toString("utf8")` replaces bad bytes with
  U+FFFD, then `JSON.parse` runs (`relay/relay.mjs:117`).
- Rust: `std::str::from_utf8` failure is 400 `not valid JSON`
  (`crates/relay/src/http.rs:145`).
- Task: decide which refusal is correct and pin it; today the same bytes get
  different statuses.

## G4 — Invalid UTF-8 in the store file

- Upstream: `readFileSync(file, "utf8")` replaces bad bytes per file, then
  per-record `JSON.parse` failures are skipped (`relay/relay.mjs:75-90`).
- Rust: `read_to_string` errors, `RoomStore::with_file` returns `Err`, and
  `Relay` panics at boot (`crates/relay/src/store.rs:41`,
  `crates/relay/src/http.rs:395-401`).
- Task: read bytes and decode lossily, or document that a corrupt store file
  is a boot refusal.

## G5 — Invalid `RELAY_PORT`

- Upstream: `Number(process.env.RELAY_PORT || 8787)`; `"abc"` → `NaN`;
  `server.listen(NaN)` throws (`relay/relay.mjs:271-272`).
- Rust: parse failure or `> 65535` silently falls back to 8787
  (`crates/relay/src/main.rs:12-16`).
- Task: refuse an invalid port loudly, or record the fallback as intended.

## G6 — Embeddable server factory

- Upstream: `createRelayServer(options)` returns a `node:http` server with
  `listen`/`close` and an injectable `storeFile` (`relay/relay.mjs:54-58`).
- Rust: `Relay::new` / `serve(listener, …)` exist, but there is no factory that
  binds an ephemeral port and hands back a shutdown handle
  (`crates/relay/src/http.rs:382-401`, `crates/relay/src/http.rs:574-589`).
- Task: a small `RelayServer` wrapper if the OS stack is going to manage it as
  a child process with graceful stop.

## G7 — Host binding option

- Upstream: `server.listen(port, …)` binds all interfaces, with Node's optional
  host argument available to callers (`relay/relay.mjs:272`).
- Rust: always `0.0.0.0:<port>` (`crates/relay/src/main.rs:24-25`).
- Task: accept `RELAY_HOST` or keep the fixed bind and say so; the viewer is
  reachable from the LAN today.

## G8 — URL decoding of every path segment

- Upstream: `new URL(req.url).pathname` decodes `%XX` everywhere before the
  split (`relay/relay.mjs:151-153`).
- Rust: splits raw segments and decodes only the room
  (`crates/relay/src/http.rs:433-469`).
- Task: decode the action segment too, or record that `%6dessages` is 404 by
  design.

## G9 — `null` body status

- Upstream: `JSON.parse("null")` succeeds, destructuring throws, catch-all
  answers 500 `internal error: …` (`relay/relay.mjs:219-221`,
  `relay/relay.mjs:255-258`).
- Rust: 400 `request body is not valid JSON` (`crates/relay/src/http.rs:144-146`).
- Task: decide the contract; the Rust answer is the safer one, but it is not
  parity.

## G10 — Connection model

- Upstream: one event loop, unbounded concurrent sockets, keep-alive
  (`relay/relay.mjs:149-266`).
- Rust: one OS thread per accepted connection, `Connection: close` on every
  response (`crates/relay/src/http.rs:574-589`, `crates/relay/src/http.rs:649-654`).
- Task: only if load matters; for the demo path the behaviour is invisible.

## G11 — Empty request target

- Upstream: `url.pathname === "/"` is the only viewer branch
  (`relay/relay.mjs:155`); an empty target is a 404.
- Rust: `path.is_empty()` also serves the viewer (`crates/relay/src/http.rs:435`).
- Task: drop the `path.is_empty()` branch or record it as a deliberate
  leniency.

## G12 — Graceful shutdown

- Upstream: Node closes the server and sockets on process signals by default.
- Rust: `serve` loops forever; no signal handling, no `Drop` for `Relay`
  (`crates/relay/src/http.rs:574-589`).
- Task: add a stop path when the stack starts managing the binary.
