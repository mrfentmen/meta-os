# Meta Trio assessment server

Rowan's lane: the server side of the frozen v2 contract
(`MASTER_DIRECTIVE_V2.md` §9), shared by Meta Vigiles, Meta Ignis, and
Meta Medicus. Zero dependencies, no build step — plain Node, like the
rest of the repo.

## Run it

```sh
npm start            # node server/server.mjs
# or: PORT=8080 node server/server.mjs
```

Default port is **8080**, which is the native app's default endpoint
(`http://localhost:8080/api/assess`). The web app's default endpoint is
the relative `/api/assess`; this server also serves the static web app
from the repo root, so one process runs the whole demo stack locally.

## Routes

| Route | What it does |
| --- | --- |
| `POST /api/assess` | One frame in, one v2 assessment out (below). |
| `GET /api/health` | `{ ok, service, products, model: { configured, live_enabled } }`. Never exposes key material. |
| `GET /…` | Static web frontend (`index.html`, `styles.css`, `js/`). |

## The contract

Request body (exactly what both clients already send):

```json
{ "product": "vigiles" | "ignis" | "medicus",
  "timestamp": "ISO-8601 with timezone",
  "image": "data:image/jpeg;base64,…" }
```

Success is HTTP 200 with the v2 assessment object from `js/schema.js`,
validated server-side against that same schema before it is sent.
Failure is an HTTP status plus the contract error shape
`{ "error": "…" }`, which both clients surface as the real error:

- `400` — request failed validation (product, timestamp, image envelope,
  JPEG magic bytes, 8 MB decoded-image cap). The model is never called.
- `413` — request body over the 12 MB envelope cap.
- `502` — the model call failed, or its response failed contract
  validation (off-contract output is never passed through).
- `503` — no model assessment is available right now (held / not
  configured — the message says which).

The server never fabricates an assessment. No model, no assessment —
only the honest error.

## Model wiring and the Spark rule

Del's ruling (2026-10-28): **Spark stays off until the build is complete
and Del green-lights the test phase. No live calls during the build.**
That green light came 2026-10-30 00:23 EDT (relayed by Pax), with the
transport shape verified against the real API — so gate 3 below is now
wired, and gates 1–2 still refuse before any call can leave the server.

`server/model.mjs` is the only place a model call can leave this
server, and it refuses in layers:

1. `ASSESS_LIVE_MODEL` unset → every call refused as *held*, even with a
   key present.
2. Gate open, no key → refused as *not configured*.
3. Gate open, key present → the Spark transport runs: POST
   `https://api.meta.ai/v1/chat/completions`, model `muse-spark-1.3`,
   OpenAI-style text + `image_url` (JPEG data URL) parts. The key
   travels only in the `Authorization` header — never in a request body,
   a commit, or a log. Del puts `SPARK_API_KEY` in the server
   environment on the Mac himself.

Configuration is environment-only, server-side:

| Variable | Meaning |
| --- | --- |
| `SPARK_API_KEY` | The model key slot. Never in a request, a commit, or a log. |
| `ASSESS_LIVE_MODEL` | `1` opens the test-phase gate. Leave unset during the build. |
| `PORT` | Listen port, default `8080`. |

Per-product prompt profiles (categories + limitations) are derived from
`js/products.js` in `model.mjs` (`PRODUCT_PROFILES`), so the server and
the clients cannot drift.

## OS queue path (Trio side, steps 1-3 — envelope + submit + result fetch + poll + wiring)

Del's direction, 2026-10-30 (relayed by Pax): the OS operates the Trio
— one submission, Best Agentic aim. The Trio server submits assessments
as jobs to the OS job queue; a resident agent claims and answers them
with Spark; the direct Spark path above stays as fallback; apps keep
calling `/api/assess` unchanged. Hard cutoff Nov 2: the queue round trip
is verified live by then, or the clean Trio ships alone.

`server/queue.mjs` is Rowan's server queue transport lane:

- `buildQueueJob(input)` turns a validated assess input into a
  versioned job envelope (`version: 1`, `kind: "trio-assessment"`):
  product, timestamp, the frame as the same JPEG data URL the clients
  send, its byte length, its SHA-256, and a deterministic id from
  product + timestamp + frame bytes (a resubmitted frame is the same
  job, and the audit trail can name it). A job is a submission, not an
  answer — no assessment is invented here.
- `submitQueueJob(job, env, deps)` posts the envelope to the queue URL
  through an injected transport and echoes the filed job id, refusing
  in layers like the model adapter: queue disabled
  (`TRIO_QUEUE_ENABLED` not `1`), queue URL not configured
  (`TRIO_QUEUE_URL` unset), malformed job, or submit failure — every
  refusal a typed `QueueError`, never a fabricated job id.

Step 2 adds `fetchQueueResult(jobId, env, deps)`: one result fetch
through an injected transport, returning `pending`, `done` (assessment
verbatim, NOT validated here — assess.mjs runs it through
`validateAssessment` before it is ever sent), or `failed` (the agent's
error string when it has one), with the same layered refusals
(disabled / not configured / fetch failure) and malformed envelopes
failing as typed `QueueError`s. The result shape is the one Pax
settled 2026-10-30 (room-1 ruling): `{ job_id, status: "ok" |
"failed", assessment: <v2 contract object> | null, error: string |
null, model, latency_ms, completed_at }`, keyed
`{job_ns}:{jid}:result` with job_ns `"trio"` on the OS side; an ok
result carries ONLY an assessment that already passed
`validateAssessment` on the agent side. The reader still accepts the
step-2 proposed shape (version 1, kind `"trio-assessment-result"`,
`jobId`, status `pending` | `done` | `failed`) and normalizes both,
and accepts a `pending` status in either shape. The Trio job is NOT
forced into the OS spark-complete envelope.

Step 3 wires the queue into `handleAssess` (`server/assess.mjs`):
when `TRIO_QUEUE_ENABLED=1`, a valid request first builds, submits,
and polls (`pollQueueResult`, bounded — 30 attempts x 1s by default)
the queue; a done queue assessment is validated exactly like a model
reply, and any queue failure — submit, fetch, poll timeout, or a
failed result — falls back to the direct Spark path and is logged
(`deps.log`, else `console.error`), never faked in contract fields.
A done queue assessment that fails contract validation is a 502, not
a silent fallback. When the queue is disabled, the direct path runs
alone, unchanged. Production transports are `httpQueuePost` /
`httpQueueGet`: POST `{TRIO_QUEUE_URL}/jobs`, GET
`{TRIO_QUEUE_URL}/jobs/:id/result` (a 404 before a result exists
reads as pending). The queue service itself is a named external
service, never inside this repo: its URL comes only from
`TRIO_QUEUE_URL`, server-side, and no key material is ever put in a
job envelope, a commit, or a log. What is deliberately NOT in this
step: a live round trip against Pax's resident-agent end — that
verification is Pax's next item, before the Nov 2 cutoff.

| Variable | Meaning |
| --- | --- |
| `TRIO_QUEUE_ENABLED` | `1` enables the queue path in `/api/assess`. Leave unset: the queue path is skipped and the direct path runs alone. |
| `TRIO_QUEUE_URL` | Queue service base URL, operator-configured (transports append `/jobs` and `/jobs/:id/result`). No URL → the queue attempt refuses as not configured and falls back to the direct path. |

## Held-state round trip: what the user actually sees

While the Spark rule holds, the server answers every valid assess request
with an honest refusal instead of an assessment, and both UIs show that
refusal verbatim — no placeholder assessment is ever rendered. Verified
live against the local server (health `configured: false`,
`live_enabled: false`; assess returns HTTP 503 with the message below).

### 1. The server's answer

A valid frame for any product (`vigiles`, `ignis`, `medicus`) gets:

```http
HTTP/1.1 503
{"error": "Live model calls are held: Spark stays off until the build is complete and Del green-lights the test phase."}
```

The other refusal states travel the same path with their own message:
gate open but no key → 503 *not configured*; a model call that fails →
502. A request that fails validation never reaches the model at all
(400, or 413 over the envelope cap). In the test phase, gate open with a
key runs the Spark transport; while the gate stays shut, every valid
request still gets the 503 *held* answer above.

### 2. What the web UI shows

`js/client.js` turns the 503 + error body into an `AssessError`
(kind `http`) carrying the server's message. `js/app.js` then, for that
one request:

- records a session-log entry with status `http_error` and the message;
- sets the backend status line to
  `Model backend not connected: <server message>`;
- adds a history item titled `Analysis request failed` with the message
  as its body;
- renders no assessment, and counts the failure in the sampler's error
  count when sampling is running.

### 3. What the native app shows

`AssessClient.swift` throws the same `AssessError`; `AppModel`
(`submitAssessment`) then:

- records a log entry with status `httpError` and the message;
- sets `backendStatus` to `.error("Model backend not connected: <message>")`,
  which `ContentView` renders in red;
- inserts a failure item in the timeline;
- renders no assessment, and the sampler counts the failure.

### 4. Reachable is not ready: the health check is a different question

`GET /api/health` answers `{ ok, service, products, model: { configured,
live_enabled } }` and never sends a frame. The web config panel's
`Check backend` button reports it in plain words — a reachable server
with the model held reads `Backend reachable: … · model: key not
configured, live calls held` (or `key configured, live calls held` when
a key is present) — followed by the explicit caveat that this does not
mean an assessment is available; an assess request still has to succeed.
A health check that passes while assess returns 503 is the expected
held-state picture, not a contradiction.

### Reproduce it locally

```sh
npm start
curl -s http://localhost:8080/api/health   # model.live_enabled: false
curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"product":"ignis","timestamp":"2026-10-28T10:20:00-04:00","image":"data:image/jpeg;base64,…"}' \
  http://localhost:8080/api/assess         # 503 + held error above
```

## Tests

`npm test` runs the whole repo suite, including `tests/server.test.mjs`:
request/image validation, every adapter refusal state, contract
validation of model output (via a labelled test double injected at the
handler boundary — tests only), and live HTTP checks of health, the
held state, bad JSON, wrong methods, and static serving; plus
`tests/server-spark-transport.test.mjs`, which exercises the Spark
transport through an injected stub fetch (request shape, fenced-JSON
unwrap, non-200 / non-JSON / empty-content failures, and the
fetch-never-called refusal states); plus
`tests/server-queue-transport.test.mjs`, which exercises the queue
envelope and submit adapter through an injected stub queuePost
(envelope fields and deterministic id, disabled / not-configured
refusals before any transport call, filed-id echo, and submit-failure
states). No test fires a live call.
