# `crates/relay` — behaviour record (B181)

Source read: `crates/relay/src/{lib,main,validation,notify,sha256,json,store,http}.rs`
at the tree this record was written on. Port source: `relay/relay.mjs` and
`relay/README.md`. Every claim below names the file and line range it comes from.

## What it is

Meta Nuntius, the product-layer message relay: rooms of stamped text lines,
plus structured NOTIFY lines, over HTTP. One binary (`main.rs:11-29`) over a
library (`lib.rs:1-97`) with no external crates (`Cargo.toml:1-7`).

## What it does

### Wire lines

- Message line: `message_line` formats `"<nick>: <text> [ts:<secs>]"`
  (`notify.rs:17-19`).
- NOTIFY line: `notify_line` formats
  `"relay: NOTIFY:<id> <severity> [<topic>] <text> [ts:<secs>]"`
  (`notify.rs:23-30`).
- The timestamp is whole epoch seconds from `SystemTime` (`http.rs:562-568`).
- NOTIFY id: `"ntf-"` + first 16 hex of SHA-256 over
  `room + "\n" + topic + "\n" + severity + "\n" + text`
  (`notify.rs:9-13`).

### Validation (refusals are 400 JSON)

- Room: `^[a-z0-9-]{1,32}$`, checked as ASCII bytes (`validation.rs:10-20`).
- Nick: 1–40 UTF-16 code units, no controls U+0000–U+001F or U+007F
  (`validation.rs:24`, `validation.rs:30-49`).
- Text: 1–2000, same single-line rule (`validation.rs:26`).
- Topic: 1–64 (`validation.rs:27`).
- Body: at most 16384 bytes (`validation.rs:24`, `http.rs:473`,
  `http.rs:498`).
- Severity: exactly `info` / `warning` / `critical` (`validation.rs:20-22`,
  `http.rs:497-501`).

The UTF-16 count is deliberate: JS `String.length` counts astral characters as
two, and `utf16_len` reproduces that (`validation.rs:30-32`).

### Routing (`http.rs:429-556`)

| Method + path | Success | Refusal |
|---|---|---|
| `GET /` | 200 HTML viewer, or 500 text when the file is missing (`http.rs:437-450`) | — |
| `GET /health` | 200 `{"ok":true,"rooms":N,"store":"memory"\|"file"}` (`http.rs:419-427`, `http.rs:452-454`) | — |
| `POST /rooms/<room>/messages` | 201 `{"index":N}` (`http.rs:472-495`) | 400 room / body / nick / text |
| `POST /rooms/<room>/notify` | 201 `{"index":N,"id":"ntf-…"}` (`http.rs:497-531`) | 400 room / body / severity / topic / text |
| `GET /rooms/<room>/messages?since=N` | 200 `{"room","total","messages"}` (`http.rs:533-553`) | 400 room |
| anything else | — | 404 `{"error":"not found"}` (`http.rs:555`) |

- A malformed `%` escape or non-UTF-8 bytes in the room segment is a 500
  (`http.rs:43-73`, `http.rs:458-470`). This mirrors the original's
  `decodeURIComponent` throw caught by its catch-all.
- `since` uses JS `parseInt` semantics (`"3abc"` → 3), missing/NaN/`< -1`
  → whole room (`http.rs:75-105`).
- GET bodies are never read; POST bodies are capped (`http.rs:617-625`).

### Storage (`store.rs:17-110`)

- In-memory rooms by default (`store.rs:24-33`).
- With a store file: reload on construction, append one JSON record per line,
  return the in-memory index even when the append fails
  (`store.rs:35-78`).
- Reload skips blank lines and any unparseable or wrongly-typed record
  (`store.rs:43-58`). An unreadable file is an error, and `Relay` panics at
  boot on it (`http.rs:389-401`).
- `messages_since` clamps `since < -1` to `-1`; an unknown room is empty
  (`store.rs:87-97`).

### JSON handling (`json.rs`)

- `escape` matches `JSON.stringify` for the record shape: `"`/`\` escaped,
  `\b \f \n \r \t` named, other controls `\u00xx`, everything else passes
  through (`json.rs:10-26`).
- `record_line` emits `{"room":"…","line":"…"}` (`json.rs:29-35`).
- `parse_record` accepts an object with string `room` and `line`, ignores
  extra fields, rejects trailing garbage, handles surrogate pairs
  (`json.rs:215-260`).

### Serving (`http.rs:574-655`)

- Std-only TCP, one thread per accepted connection (`http.rs:574-589`).
- Reads the request line and headers, honours `Content-Length`, caps the body
  at `MAX_BODY_BYTES + 1` before handing it to `Relay::handle`
  (`http.rs:591-647`).
- A poisoned relay mutex becomes a 500 JSON error (`http.rs:629-640`).
- Responses are `HTTP/1.1` with `Content-Type`, `Content-Length`, and
  `Connection: close` (`http.rs:646-661`).

## What it refuses (one table)

| Input | Answer |
|---|---|
| room not `[a-z0-9-]{1,32}` | 400 `room name must match [a-z0-9-]{1,32}` |
| body > 16384 bytes | 400 `request body too large or unreadable` |
| body not a JSON object | 400 `request body is not valid JSON` |
| nick missing/non-string/empty/>40/control | 400 `nick must be a single line of 1-40 chars` |
| text missing/empty/>2000/control | 400 `text must be a single line of 1-2000 chars` |
| severity not the exact set | 400 `severity must be one of "info", "warning", "critical"` |
| topic missing/empty/>64/control | 400 `topic must be a single line of 1-64 chars` |
| bad `%` escape in room | 500 `internal error: invalid percent-encoding in room name` |
| unknown method/path | 404 `not found` |
| viewer file missing | 500 text/plain `viewer.html is missing beside relay.mjs` |
| unreadable store file at boot | panic `failed to read store file <path>: <err>` |

## What it writes down

- One JSONL record per appended line when `RELAY_STORE_FILE` is set:
  `{"room":"…","line":"…"}` (`store.rs:60-78`).
- stderr notes: `skipped an unparseable store record`
  (`store.rs:51`), `store append failed: <err>` (`store.rs:72`),
  `connection error` / `accept failed` (`http.rs:581-586`).
- stdout on boot: `Meta Nuntius relay listening on port <p> (store: <kind>)`
  (`main.rs:27`).

## Findings (reported, not fixed)

1. **Viewer path is cwd-relative here, module-relative upstream.**
   `viewer_path()` checks `RELAY_VIEWER_FILE`, then `relay/viewer.html` in the
   current directory (`http.rs:404-417`); the Node original resolves it beside
   `relay.mjs` (`relay/relay.mjs:49-50`, `relay/relay.mjs:162-168`). Running
   the Rust binary outside the repo root makes `/` a 500 unless the env var is
   set.
2. **Invalid `RELAY_PORT` is silently 8787 here.** `parse::<u16>()` failure or
   a value > 65535 falls back to 8787 (`main.rs:12-16`); Node's
   `Number("abc")` is `NaN` and `listen(NaN)` throws
   (`relay/relay.mjs:271-272`). The refusal is quieter on the Rust side.
3. **A JSON `null` body is 400 here, 500 upstream.** `JSON.parse("null")`
   succeeds, then destructuring throws inside the try block and the Node
   catch-all answers 500 (`relay/relay.mjs:219-221`, `relay/relay.mjs:255-258`);
   `parse_body` answers 400 `not valid JSON` (`http.rs:144-146`).
4. **Non-UTF-8 bodies are 400 here, decoded upstream.** Node's
   `Buffer.toString("utf8")` replaces invalid bytes with U+FFFD before
   parsing; `parse_body` refuses the bytes (`http.rs:145`).
5. **A non-UTF-8 store file fails boot here.** `read_to_string` errors and
   `Relay` panics (`store.rs:41`, `http.rs:395-401`); Node replaces invalid
   bytes and then skips records it cannot parse (`relay/relay.mjs:75-90`).
6. **No chunked requests.** The server needs `Content-Length`
   (`http.rs:600-625`); Node streams whatever arrives.
7. **The doc's 500-JSON promise is not universal.** `lib.rs:62-63` says
   unexpected failures are JSON; the missing-viewer failure is `text/plain`
   (`http.rs:448-453`).
8. **Path segments other than the room are not percent-decoded.** Node's
   `URL.pathname` decodes them, so `/rooms/main/%6dessages` matches upstream
   and 404s here (`http.rs:433-436`).
9. **One thread per connection, no cap** (`http.rs:577-583`), versus the
   Node event loop. A slow client holds a thread until the body is read.
10. **`target` with no path (`""`) serves the viewer here** (`http.rs:435`),
    while Node's `url.pathname === "/"` check would not match an empty target
    and would 404 (`relay/relay.mjs:155`).

## Test inventory at this record

| Module | `#[test]` count |
|---|---:|
| `http` | 10 |
| `validation` | 4 |
| `notify` | 4 |
| `store` | 4 |
| `json` | 3 |
| `sha256` | 3 |

B191 closes `json` (tied fewest with `sha256`) to 13 in
`crates/relay/tests/gap_close.rs`.
