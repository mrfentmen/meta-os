# crates/assess-server — failure drill (B141)

Written from the code, for another agent to run. Each step names the input that
stops arriving, the first thing that breaks, the expected answer, and how to
tell pass from fail. Run from the repo root; the crate is a binary, so
`cargo run -p assess-server` is the launcher. No step requires a live model or
a live queue; the point is the refusal path.

## Setup

```sh
cargo build -p assess-server --bin assess-server -j1
BIN=target/debug/assess-server
export PORT=18080
export SPARK_GUARDRAIL_STATE=/tmp/assess-drill-guardrail.json
rm -f "$SPARK_GUARDRAIL_STATE"
```

A valid frame for every step below (a 5-byte JPEG header, enough for
validation):

```sh
FRAME=$(printf '\377\330\377\340\000' | base64)
BODY='{"product":"ignis","timestamp":"2026-11-02T00:00:00.000Z","image":"data:image/jpeg;base64,'"$FRAME"'"}'
```

## D1 — the model input stops arriving (no key)

```sh
"$BIN" & sleep 0.3
curl -s -o /tmp/d1 -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d "$BODY" localhost:18080/api/assess
cat /tmp/d1
```

- Expected: `503`, body `{"error":"No model API key is configured on the server. Set SPARK_API_KEY in the server environment."}` (`main.rs:433-435`, `615-618`).
- Pass: status and message match; no assessment object anywhere.
- Fail: 200, or a fabricated assessment, or `held` while `ASSESS_LIVE_MODEL=1`.

## D2 — the gate is shut (the default)

Unset `SPARK_API_KEY`, leave `ASSESS_LIVE_MODEL` unset, repeat D1.

- Expected: `503` with "Live model calls are held: Spark stays off until the build is complete and Del green-lights the test phase." (`main.rs:430-432`).
- Pass: that exact message, key present or not.
- Fail: any call attempt; a key alone must not open the gate.

## D3 — the spend input stops arriving (guardrail at cap)

```sh
printf '{"calls":999,"est_cost_usd":75.0,"log":[]}' > "$SPARK_GUARDRAIL_STATE"
SPARK_API_KEY=dummy ASSESS_LIVE_MODEL=1 "$BIN" & sleep 0.3
curl -s -o /tmp/d3 -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d "$BODY" localhost:18080/api/assess
cat /tmp/d3
```

- Expected: `502` with a `GUARDRAIL STOP: estimated test spend $75.0000 has reached the $75.00 test budget. No call sent.` message (`main.rs:436-438`; `crates/guardrail/src/lib.rs:67-75`).
- Pass: 502 and the stop message. The transport must not be reached: run with no
  network and the same answer must appear immediately, not after a 60 s timeout.
- Fail: a call is attempted, or the answer is 503 (that would mean the cap was
  checked after the key, which it is not: key at 435, guardrail at 438).

## D4 — the queue URL is configured but the queue is down

This is the first break an operator sees: a request hangs on the queue before
falling back.

```sh
TRIO_QUEUE_ENABLED=1 TRIO_QUEUE_URL=http://127.0.0.1:9 "$BIN" & sleep 0.3
time curl -s -o /tmp/d4 -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d "$BODY" localhost:18080/api/assess
```

- Expected: `503` (held/not configured, whichever the model env says), and one
  stderr line beginning `queue fallback:` and ending
  `; falling back to the direct Spark path` (`main.rs:600-611`).
- Pass: the fallback line appears once, the final status is the model path's
  status, and no assessment is fabricated.
- Fail: a 500, a silent answer with no log line, or a queue error returned as
  the HTTP body (queue failures are never surfaced as 5xx of their own).
- Note: the submit uses a 30 s timeout (`main.rs:218-220`), so "down" means a
  refused connection (fast) or a black hole (up to 30 s). Time it; the number
  is the cost of this failure mode.

## D5 — the queue accepts the job but its result never arrives

Use a stub queue that answers `POST /jobs` with `{"jobId":"trio-drill"}` and
`GET /jobs/trio-drill/result` with `{"job_id":"trio-drill","status":"pending"}`
on every call.

- Expected: 30 fetches at 1 s intervals, then `queue fallback: Queue result poll
  timed out after 30 attempts: job trio-drill still pending. ...`
  (`main.rs:373-399`, `600-611`), then the direct path's answer.
- Pass: the timeout message names the job and the attempt count; the request
  takes about 30 s plus transport time.
- Fail: an infinite poll, or a pending result treated as an assessment.

## D6 — the model endpoint is unreachable

`ASSESS_LIVE_MODEL=1`, `SPARK_API_KEY=dummy`, `SPARK_GUARDRAIL_STATE` fresh, and
no route to `api.meta.ai` (offline machine or a hosts entry).

- Expected: `502` with `Spark request failed: ...` after the 60 s timeout
  (`main.rs:454-466`), never a fabricated assessment.
- Pass: 502 and a transport message; no ledger entry is written (the record is
  after a response, `main.rs:468-472`).
- Fail: 200, or a ledger entry for a call that never completed.

## D7 — the client sends headers and no body

```sh
printf 'POST /api/assess HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\n\r\n' | nc 127.0.0.1 18080
```

- Expected: the connection **hangs**. `handle_connection` calls
  `read_exact` for 100 bytes with no read timeout (`main.rs:731-749`); the
  thread waits until the client closes.
- Pass (as a documented failure): the process stays alive and the thread remains
  blocked; `Ctrl-C` the client, then the server answers 400 to the dead socket
  or drops it.
- This is the first break when a client stops mid-body: one leaked thread per
  half-open request. There is no cap on concurrent threads (`main.rs:802-806`).
  Recorded as finding 8 in `assess-server.md` and a gap in
  `assess-server-gaps.md` G7.

## D8 — the static input stops existing

Start the binary from a directory with no `index.html` (for example
`target/debug`).

- `GET /` → `404 {"error":"not found: /"}` (`main.rs:667-694`).
- `GET /api/health` still answers 200, so health is green while the UI is
  entirely missing. Pass: that split is visible and both statuses are correct.
- This is the consequence of the cwd-relative root (finding 7).

## D9 — the body exceeds the cap

```sh
head -c 13000000 /dev/zero | tr '\0' 'a' > /tmp/big
curl -s -o /tmp/d9 -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' --data-binary @/tmp/big localhost:18080/api/assess
```

- Expected: `413` with `request body exceeds 12582912 bytes`, answered before
  the body is read (`main.rs:739-741`).
- Pass: 413 arrives while the client is still uploading.
- Fail: 400 from JSON parse, which would mean the cap was checked too late.

## D10 — the ledger write stops working

Point `SPARK_GUARDRAIL_STATE` at a read-only directory and make one billable
call (needs a live model, so this is the optional drill).

- Expected by the Rust code: the call succeeds and the spend is **not**
  recorded; no error is surfaced (`crates/guardrail/src/lib.rs:64-69`).
- Expected by the Node original: `502` with `Budget ledger record failed: ...`
  (`server/model.mjs:210-224`).
- Pass for the port as it stands: the divergence is observed and filed; it is
  gap G12. A fix is not part of this drill.

## What the drill proves, and what it does not

It proves the refusal paths answer what the code says, with the status and
message named above. It does not prove a live model assessment, a live queue
round trip, or the HTTP handler's behaviour under concurrency beyond D7. Those
need the Mac build and a real queue, which the light lane does not run.
