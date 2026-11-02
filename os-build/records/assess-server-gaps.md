# crates/assess-server — behaviours the Rust port does not carry yet (B137)

Premise correction first: **this crate has no Python original.** Its header
names five Node sources (`crates/assess-server/src/main.rs:3-5`), and a search
of `os/` for an assess module returns nothing. The behaviours below are
therefore measured against the Node originals, which are the actual port
source. This is a finding for the task list owner, not a silent substitution.

Each entry is a task, in the shape the list asks for: the behaviour, the source
line, the Rust line, and what "done" means. None is ported here.

## G1 — The four missing HTTP routes

- Behaviour: `/api/crew/status`, `/api/cameras`, `/api/fires`, and
  `/api/weather/radar/:z/:x/:y.png`, with their own refusals (502 upstream,
  503 no FIRMS key, 400 bad tile).
- Source: `server/server.mjs:176-236`.
- Rust: only assess, health, and static exist (`main.rs:750-786`).
- Done when: each route answers with the same status/shape as the Node server,
  or the crate doc states the port is assess-only.

## G2 — Queue result passthrough fields

- Behaviour: the normalised result carries `model`, `latency_ms`, and
  `completed_at` when the envelope supplies them, with type checks.
- Source: `server/queue.mjs:218-235`.
- Rust: `QueueResult` has only job id, assessment, and error (`main.rs:254-258`);
  the fields are ignored.
- Done when: `QueueResult` carries the three optional fields and a test pins
  each type refusal.

## G3 — Full job usability check before submit

- Behaviour: `isUsableJob` checks product, non-empty timestamp, and a JPEG
  data URL, not just version/kind/id.
- Source: `server/queue.mjs:141-162`, used at `164-200`.
- Rust: `submit_queue_job` checks only version, kind, and id
  (`main.rs:348-356`).
- Done when: a job with an unknown product or missing `image.dataUrl` is
  refused before the transport, with a test proving the transport was not
  called.

## G4 — The three missing prompt paragraphs

- Behaviour: the prompt includes the region-coordinate paragraph, the
  visible-marks paragraph, and the Vigiles "crowd gathered" note.
- Source: `server/model.mjs:100-106`.
- Rust: `guardrail::build_prompt` stops after the "Describe only" line
  (`crates/guardrail/src/lib.rs:130-155`); `build_spark_prompt` passes no
  correction or extra text (`main.rs:420-427`).
- Done when: the Rust prompt contains all three paragraphs, or the guardrail
  crate exposes a way to add them.

## G5 — Static content types and cache header

- Behaviour: `.sdf`, `.jsonl`, `.webmanifest`, `.png` are served with their
  types; radar bytes carry `Cache-Control: public, max-age=300`.
- Source: `server/server.mjs:41-50`, `56-64`.
- Rust: `content_type_for` serves html/css/js/mjs/json only
  (`main.rs:657-665`); no `Cache-Control` header anywhere (`634-655`).
- Done when: the same extension table is served and the cache header is
  present where the Node server sends it.

## G6 — Body reading without Content-Length

- Behaviour: the Node server streams the request body and enforces the 12 MiB
  cap while reading, so a chunked request works.
- Source: `server/server.mjs:76-92`.
- Rust: reads exactly `Content-Length` bytes (`main.rs:731-749`); a chunked
  body is read as zero bytes and fails JSON parse with 400.
- Done when: chunked bodies are either read correctly or refused with a
  stated 411/400 that names the limitation.

## G7 — Catch-all 500

- Behaviour: any unexpected handler error is a 500 with
  `internal error: ...`.
- Source: `server/server.mjs:240-243`.
- Rust: no wrapper; a panic closes the connection (`main.rs:702-788`).
- Done when: a handler failure returns a 500 JSON body instead of a dropped
  connection.

## G8 — Static containment by resolved path

- Behaviour: resolve the path and require it to start with the static root,
  which also stops symlink escapes.
- Source: `server/server.mjs:94-117`.
- Rust: rejects `..` segments but does not canonicalise (`main.rs:667-694`).
- Done when: a symlink inside the doc root pointing outside is refused, with
  a test or a written drill.

## G9 — Listen address and port parsing

- Behaviour: Node listens on all interfaces and `Number(process.env.PORT ?? 8080)`.
- Source: `server/server.mjs:246-252`.
- Rust: binds `127.0.0.1` only and silently falls back to 8080 on an
  unparseable `PORT` (`main.rs:790-799`).
- Done when: the intended bind address is documented (loopback-only is a
  defensible choice) and an invalid `PORT` is either refused or logged.

## G10 — Poll bound of zero

- Behaviour: `maxAttempts = 0` performs zero fetches and throws the timeout.
- Source: `server/queue.mjs:335-349`.
- Rust: `max_attempts.max(1)` performs one fetch (`main.rs:377`).
- Done when: the zero bound matches the source, or the difference is stated in
  the record as deliberate.

## G11 — Empty image bytes on the model path

- Behaviour: `assessWithModel` refuses empty `imageBytes` before building the
  data URL.
- Source: `server/model.mjs:174-181`.
- Rust: `assess_with_model` encodes whatever bytes it is given; the check
  exists only in `validate_assess_request` (`main.rs:429-452`).
- Done when: the public model function refuses empty bytes, or the function is
  made private to the validated path.

## G12 — Guardrail ledger write failure

- Behaviour: a failed budget-ledger write fails the request with
  `Budget ledger record failed: ...`.
- Source: `server/model.mjs:210-224`, `server/budget.mjs:125-146`.
- Rust: `guardrail::record` ignores the write result
  (`crates/guardrail/src/lib.rs:64-69`), so spend can go unrecorded.
- Done when: `record` returns a `Result` and `assess_with_model` maps a write
  failure to `model_call_failed`.

## G13 — Product list includes `science-lab`

- Behaviour: `isProductId("science-lab")` is true because `PRODUCTS` contains
  it (`js/products.js:138`, `208-210`), so `server/assess.mjs:96-112` accepts
  it and `server/server.mjs:167` reports four product ids.
- Rust: three products only (`main.rs:34-36`, `774-775`).
- Done when: the port matches whichever list is authoritative, and the
  disagreement between `js/products.js` and `server/README.md` ("the Trio
  three") is resolved by its owner.

## G14 — Queue HTTP transport injection

- Behaviour: `httpQueuePost`/`httpQueueGet` accept an injected `fetch` for
  tests and answer the same errors when no fetch exists.
- Source: `server/queue.mjs:359-424`.
- Rust: the transports take no injectable HTTP client; tests can only replace
  the whole `queue_post`/`queue_get` function (`main.rs:223-246`, `532-540`).
- Done when: the transport layer has a seam, or the record states that the
  function-level seam is the deliberate substitute.

## G15 — The guardrail ledger shape and its read failure

- Behaviour: the ledger is one JSON object whose log entries carry a nested
  `usage: { input_tokens, output_tokens }` object and an ISO `ts` ending
  `+00:00`; an unreadable or malformed file raises a `BudgetError` and no call
  is sent.
- Source: `server/budget.mjs:61-90` (read failure), `125-146` (entry shape).
- Rust: `guardrail::load_state` returns `Default` on any read/parse failure
  (`crates/guardrail/src/lib.rs:54-58`), and `record` writes flat
  `input_tokens`/`output_tokens` with the fixed `ts`
  `2026-10-30T00:00:00Z` (`crates/guardrail/src/lib.rs:88-92`).
- Done when: the ledger shape is either the same as the Node/Python one or a
  documented second shape, and an unreadable ledger fails closed with a
  `GUARDRAIL STOP` message instead of resetting the spend counter.
