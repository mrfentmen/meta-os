# Record — crates/assess-server, from the code

Scope: the whole crate, which is one file, `crates/assess-server/src/main.rs`
(11 lines of header + 800 lines of code + the test module at line 813). It is a
binary crate: `Cargo.toml` declares `[[bin]] name = "assess-server"` and there is
no `src/lib.rs`, so nothing outside the binary can link it (B142 records the
consequence).

Sources it ports, named in the header (lines 1-11): `server/README.md`,
`server/assess.mjs`, `server/model.mjs`, `server/queue.mjs`, `server/server.mjs`.
The port is Rust, not a Python original — see `assess-server-gaps.md` for the
premise correction and the not-yet-carried behaviours.

## What it does

### 1. Request validation (`main.rs:34-166`)

- `is_product_id` accepts exactly `vigiles`, `ignis`, `medicus` (34-36).
- `is_valid_iso8601` is a hand parser: 10-char date with `-` at 4 and 7, real
  calendar day via `days_in_month` (38-49), `T` separator, `hh:mm` required,
  optional `:ss` and fractional seconds, timezone `Z` or `±hh:mm`/`±hhmm`
  (51-108). Seconds and offset minutes are range-checked (99-101, 106-108).
- `parse_image_data_url` requires the exact prefix
  `data:image/jpeg;base64,`, standard base64, non-empty bytes, the 8 MiB cap
  `MAX_IMAGE_BYTES` (23), and the JPEG magic `ff d8 ff` (110-127). It returns
  the bytes and `"image/jpeg"`.
- `validate_assess_request` collects every error rather than stopping at the
  first, and returns one joined message (136-166). A non-object body short-
  circuits to a single error (137-139).

### 2. Queue transport (`main.rs:168-399`)

- Job build: version 1, kind `trio-assessment`, deterministic id delegated to
  `queue_core::deterministic_job_id` (190-192), frame as a JPEG data URL plus
  byte length and SHA-256 (194-212). Refuses a bad product, empty timestamp, or
  empty frame (195-203).
- Transports: POST `{base}/jobs` (223-236) and GET `{base}/jobs/{id}/result`
  (238-246), both with a 30 s agent timeout (218-220). A 404 on the result is
  normalised to `pending` (242).
- Result envelopes: both the Pax-agreed shape (`job_id`, `status ok|failed`,
  plus `pending`) and the step-2 shape (`version`, `kind`, `jobId`,
  `status pending|done|failed`) are accepted and normalised into `QueueResult`
  (254-258, 265-338). Mismatched ids, wrong version/kind, a done envelope
  without an assessment object, a pending envelope carrying an assessment, and
  unknown statuses are all `queue_fetch_failed` (260-262, 268-338).
- `submit_queue_job` refuses disabled, unconfigured, and malformed jobs before
  calling the transport (340-357). `fetch_queue_result` refuses disabled,
  unconfigured, and empty ids before the transport (359-371).
- `poll_queue_result` fetches until a non-pending result, sleeps between
  attempts, and turns an exhausted bound into `queue_fetch_failed` with the
  attempt count and job id in the message (373-399).

### 3. Model adapter (`main.rs:401-505`)

- Refusal order is the Spark rule: live gate off → `held` (430-432); gate on
  and no key → `not_configured` (433-435); then the shared spend guardrail
  (436-438); then the transport.
- The request is the OpenAI-style body with a text prompt and an `image_url`
  data URL; the key travels only in `Authorization` (441-452, 461). The endpoint
  is overridable (453) and defaults to the guardrail crate's `SPARK_ENDPOINT`.
- After a billable response, `guardrail::record` is called with the product
  kind, model, input/output tokens, and latency (468-472). Empty content and
  non-JSON content are typed `model_call_failed` (488-500).
- `build_spark_prompt` resolves the product profile from `queue_store` and
  builds the prompt through `guardrail::build_prompt` (420-427).

### 4. Orchestration (`main.rs:507-632`)

- `Env::from_process` reads the six variables tabulated in
  `assess-server-config.md` (516-530).
- `Deps` is the test seam: model call, queue post/get, poll interval, max
  attempts, sleep, log (532-540). `default_deps` wires the real transports
  (553-566).
- `handle_assess` validates first (400 on failure, 576-581), then, only when
  `trio_queue_enabled`, builds/submits/polls the queue (583-610). Any queue
  failure is logged and falls through to the direct model path (600-611); a
  done queue assessment is not special-cased — both paths meet the same
  `contract_check` (568-574, 618-622). A `model_call_failed` is 502, any other
  model refusal is 503 (613-617); an off-contract answer is 502 (620-622).

### 5. HTTP service (`main.rs:634-811`)

- `send_json` writes a fixed header set: JSON content type, length, `ACAO: *`,
  `Connection: close` (634-655). `content_type_for` serves html, css, js/mjs,
  and json only (657-665).
- `serve_static` resolves the launch directory, rejects any `..` segment, and
  404s on an unknown extension or unreadable file (667-694).
- `handle_connection` reads the head line by line up to 64 KiB, answers
  `OPTIONS` with 204, parses `Content-Length`, enforces `MAX_BODY_BYTES` (24)
  with a 413 before reading (739-741), and routes `/api/assess` (POST only),
  `/api/health` (GET only), other `/api/*` as 404, and everything else as
  static GET (750-786).
- `main` binds `127.0.0.1:PORT` (default 8080), prints three startup lines, and
  spawns one thread per accepted connection (790-811).

## What it refuses (the refusal table)

| Condition | Answer | Source |
|---|---|---|
| body not a JSON object | 400, one error | `main.rs:137-139`, `576-581` |
| bad product / timestamp / image | 400, all errors joined | `136-166` |
| body over 12 MiB | 413 before reading the body | `739-741` |
| wrong method on `/api/assess` | 405 | `750-753` |
| wrong method on `/api/health` | 405 | `766-769` |
| unknown `/api/*` route | 404 | `779-782` |
| non-GET on a static path | 405 | `783-786` |
| unknown static extension / `..` / unreadable | 404 | `667-694` |
| queue disabled | `queue_disabled` | `341-343` |
| queue enabled, no URL | `queue_not_configured` | `343-347` |
| malformed queue job | `queue_submit_failed` | `348-356` |
| bad/unknown result envelope | `queue_fetch_failed` | `265-338` |
| poll bound exhausted | `queue_fetch_failed`, job named | `386-396` |
| model live gate off | `held` → 503 | `430-432`, `615-618` |
| gate on, no key | `not_configured` → 503 | `433-435` |
| guardrail cap reached | `model_call_failed` → 502 | `436-438` |
| transport/HTTP/JSON failure | `model_call_failed` → 502 | `454-500` |
| off-contract model/queue answer | 502, never passed through | `568-574`, `620-622` |

No path fabricates an assessment: every failure returns an HTTP status plus
`{"error": ...}`.

## What it writes down

- **stderr** fallback logs, one line per queue failure, prefixed
  `queue fallback:`, always naming the job when there is one (`600-611`);
  accept failures print `assess-server: accept failed` (`808`).
- **The guardrail ledger file** through `guardrail::record` (`468-472`), at the
  path in `SPARK_GUARDRAIL_STATE` (default `spark_guardrail_state.json`,
  `524-527`). This crate never writes that file itself; the guardrail crate
  does (`crates/guardrail/src/lib.rs:81-102`).
- **HTTP response bodies** only. No database, no queue file, no cache: the
  queue lives behind `TRIO_QUEUE_URL`, and the static files are read-only.

## Findings — docs/comments versus code (B136)

1. **The header overstates the HTTP surface.** Line 7 says it "mirrors plain
   `node:http` in server.mjs", but `server.mjs` also serves `/api/crew/status`,
   `/api/cameras`, `/api/fires`, and `/api/weather/radar/:z/:x/:y.png`
   (`server/server.mjs:176-236`). The Rust routes stop at assess/health/static
   (`main.rs:750-786`). The header's own route sentence is accurate; the
   "mirrors" sentence is not. See `assess-server-gaps.md` G1.
2. **"Invalid queue/model answers are 502" is only true of contract-invalid
   answers.** A malformed queue envelope is an `Err` and falls back to the
   direct path (`600-611`); it never becomes a 502. The sentence at lines 9-10
   should say "a contract-invalid answer".
3. **`ModelConfig` is dead.** Defined at `411-414`, never constructed;
   `model_status` takes two bools instead (`416-418`).
4. **`queue_config_enabled` is dead.** Defined at `184-186`, never called;
   `handle_assess` builds `QueueConfig` directly (`584`).
5. **`is_product_id` rejects `science-lab`, while the JavaScript original
   accepts it.** `js/products.js:138` puts `science-lab` in `PRODUCTS`, and
   `isProductId` (208-210) tests `PRODUCT_BY_ID`, so `server/assess.mjs:96-112`
   accepts it. The Rust list is three (`main.rs:34-36`) and its health answer
   hardcodes three (`773-777`). Either the JS list is the truth (then the port
   is wrong) or the README's "Trio three" is the truth (then `js/products.js`
   carries a fourth assessment product). Reported, not changed.
6. **The empty-image refusal message differs.** JS: an empty string is
   "missing or not a string" (`server/assess.mjs:75-77`). Rust: an empty string
   reaches the prefix check and gets "must be a data:image/jpeg;base64 URL"
   (`main.rs:112-115`). Same status, different words.
7. **The static root differs.** JS resolves `STATIC_ROOT` to the repo root
   (`server/server.mjs:39`); Rust uses the process current directory
   (`main.rs:791`). Running the binary from `target/debug` serves nothing until
   the 404 path. This is a behaviour difference, not a crash.
8. **There is no catch-all 500.** JS wraps the whole request in try/catch and
   answers 500 (`server/server.mjs:240-243`). A panic in a Rust connection
   thread ends that connection with no response (`main.rs:702-788`).
9. **`poll_queue_result` treats `max_attempts = 0` as one attempt.**
   `max_attempts.max(1)` (377) makes a zero bound fetch once; JS's
   `for (attempt = 1; attempt <= 0; ...)` fetches zero times and throws
   (`server/queue.mjs:335-349`).
10. **Queue result passthrough fields are dropped.** JS copies `model`,
    `latency_ms`, and `completed_at` into the normalised result
    (`server/queue.mjs:218-235`); the Rust `QueueResult` has no field for them
    (`254-258`), so a caller cannot see which model answered or when.
11. **`submit_queue_job` validates less than `isUsableJob`.** JS checks product,
    timestamp, and the JPEG data URL (`server/queue.mjs:141-162`); Rust checks
    only version, kind, and a non-empty id (`main.rs:348-356`). A job with a bad
    product would be posted.
12. **The Rust prompt is shorter than the JS prompt.** JS adds the region
    paragraph, the marks paragraph, and the Vigiles crowd note
    (`server/model.mjs:100-106`); `guardrail::build_prompt` has none of the
    three (`crates/guardrail/src/lib.rs:130-155`). `build_spark_prompt` cannot
    add them without changing the guardrail crate. See gaps G4.
13. **The guardrail file write is silent on failure.** `save_state` ignores
    the write result (`crates/guardrail/src/lib.rs:64-69`), while the JS
    `recordBudgetCall` throws on a failed write (`server/budget.mjs:125-146`).
    A spend record can be lost without the assess request failing. This is a
    caller-expectation mismatch recorded in `assess-server-callers.md`.
14. **The binary ignores arguments.** `main` reads only the environment
    (`790-811`); the Node server does the same, so this is consistent, but there
    is no `--help` or `--port` flag to document.
15. **The guardrail ledger shape is not the Node/Python shape, and a corrupt
    ledger fails open.** Rust writes flat `input_tokens`/`output_tokens` and a
    fixed `ts` (`crates/guardrail/src/lib.rs:88-92`); the Node original writes
    a nested `usage` object and an ISO timestamp
    (`server/budget.mjs:125-146`). More seriously, an unreadable or malformed
    ledger returns a zero-cost state (`crates/guardrail/src/lib.rs:54-58`) while
    the Node original raises `BudgetError` and sends nothing
    (`server/budget.mjs:61-90`). Gap G15 records the port task.
