# crates/assess-server — configuration surface (B140)

The binary has **no flags and no config file**. Everything comes from the
process environment (`main.rs:516-530`, `790-811`), plus two paths it reads:
the guardrail ledger file and the static document root. Defaults are the
`unwrap_or`/`unwrap_or_default` values, quoted below.

## Environment variables

| Variable | Read at | Default when unset/empty | Accepted values | Refusal when wrong |
|---|---|---|---|---|
| `PORT` | `main.rs:791` | `8080` | anything `u16::from_str` accepts | **none** — a non-numeric or out-of-range value silently becomes 8080 |
| `TRIO_QUEUE_ENABLED` | `main.rs:519` | disabled | exactly `"1"` | none — any other string (`"true"`, `"yes"`) silently disables the queue |
| `TRIO_QUEUE_URL` | `main.rs:520` | `""` | service base URL; trailing `/` trimmed at `214-216` | queue attempt refuses `queue_not_configured` (`343-347`) |
| `SPARK_API_KEY` | `main.rs:521` | `None` | any non-empty string; empty string is treated as absent | live gate on + absent → `not_configured` (`433-435`) |
| `ASSESS_LIVE_MODEL` | `main.rs:522` | held | exactly `"1"` | any other value (including `"true"`) keeps the call `held` (`430-432`) |
| `SPARK_GUARDRAIL_STATE` | `main.rs:524-528` | `spark_guardrail_state.json` | any path | unreadable/malformed file is **not** a refusal: `guardrail::load_state` falls back to a zero-cost state (`crates/guardrail/src/lib.rs:54-58`) |

There is no `HOST`, `TLS`, `WORKERS`, or log-level variable: the listener is
fixed to `127.0.0.1` (`main.rs:795`), there is one thread per connection
(`802-806`), and logs go to stderr (`545-547`).

## Files it reads or writes

| Path | Direction | When | Failure behaviour |
|---|---|---|---|
| `SPARK_GUARDRAIL_STATE` (default `spark_guardrail_state.json`) | read before a model call, written after a billable one | `main.rs:436-438`, `468-472` | unreadable → treated as empty state (fails **open**, unlike the Node original, `server/budget.mjs:61-90`); unwritable → write ignored (`crates/guardrail/src/lib.rs:64-69`) |
| current working directory | read | every static request (`main.rs:791`, `667-694`) | missing file → 404; missing directory → 404; no startup check |
| any static file under that directory | read | `GET` on a non-`/api/` path | unknown extension, `..`, or unreadable → 404 (`667-694`) |

It writes **no** file of its own. The queue lives behind `TRIO_QUEUE_URL`; the
HTTP server writes only socket bytes.

## Timeouts and caps (constants, not configurable)

| Name | Value | Line | Effect |
|---|---|---|---|
| `MAX_IMAGE_BYTES` | 8 MiB | 23 | decoded frame cap; over → 400 |
| `MAX_BODY_BYTES` | 12 MiB | 24 | request envelope cap; over → 413 |
| queue poll interval | 1000 ms | 29 | default `Deps.poll_interval_ms` (562) |
| queue poll attempts | 30 | 30 | default `Deps.max_attempts` (563) |
| queue HTTP timeout | 30 s | 218-220 | applies to POST and GET |
| model HTTP timeout | 60 s | 456 | Spark call |
| request head cap | 64 KiB | 718 | head read stops; a longer head is parsed as-is |
| write cap | none | — | response size is not bounded |

## Wrong-value summary

- `PORT=abc` or `PORT=70000` → binds 8080, no warning. A port already in use
  panics at `main.rs:795` (`expect("assess-server: bind failed")`).
- `TRIO_QUEUE_ENABLED=true` → queue skipped; the direct path runs as if the
  variable were unset.
- `TRIO_QUEUE_ENABLED=1` with `TRIO_QUEUE_URL` unset → every request logs a
  `queue fallback: No queue URL is configured...` line and uses the direct path
  (`343-347`, `600-611`).
- `ASSESS_LIVE_MODEL=1` without `SPARK_API_KEY` → 503 *not configured*; with a
  key and a guardrail at cap → 502 *GUARDRAIL STOP*; with a key under cap →
  the Spark call runs.
- `SPARK_GUARDRAIL_STATE` pointing at a corrupt file → the spend ledger resets
  to zero and the next call is allowed. This is the most consequential default
  in the surface: a corrupt ledger fails open (finding 15 below).

## Findings

1. **Silent `PORT` fallback.** A typo in `PORT` starts the server on 8080 with
   no line saying the value was rejected (`main.rs:791`). The startup banner
   prints the port it bound, which is the only clue.
2. **The guardrail fails open on an unreadable ledger.** The Node original
   raises a `BudgetError` and sends nothing (`server/budget.mjs:61-90`); the
   Rust `load_state` returns `Default` (`crates/guardrail/src/lib.rs:54-58`), so
   a corrupt file silently resets the $75 counter.
3. **The ledger entry shape is not the Node/Python shape.** Rust writes flat
   `input_tokens`/`output_tokens` and a fixed `ts` (`crates/guardrail/src/lib.rs:88-92`);
   Node writes a nested `usage` object and an ISO timestamp with `+00:00`
   (`server/budget.mjs:125-146`). A tool reading both ledgers sees two shapes.
