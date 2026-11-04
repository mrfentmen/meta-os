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
| `POST /api/agent/ask` | One question from any app's chat box in, one short plain-text answer out (below). |
| `GET /api/health` | `{ ok, service, products, model: { configured, live_enabled } }`. Never exposes key material. |
| `GET /api/cameras` | Same-origin NYCTMC camera list, with any positioned IP cameras from `cams.json` appended. 502 only when both are empty and NYCTMC failed. |
| `GET /api/ipcam` | `{ cameras, error, config, configMissing, ffmpeg }` for the configured IP cameras. The config problems are named, never hidden. |
| `GET /api/ipcam/:id/snapshot` | One JPEG frame from that camera, taken through ffmpeg. 404 unknown id, 409 disabled, 502 ffmpeg failure with the reason. |
| `GET /api/fires` | NASA FIRMS trailing-24 h hotspots, cached 15 min. 503 without `FIRMS_MAP_KEY`. |
| `GET /api/weather/radar/:z/:x/:y.png` | Proxied IEM NEXRAD radar tile (PNG). 400 on out-of-range tiles. |
| `GET /…` | Static web frontend (`index.html`, `styles.css`, `js/`). |

## IP cameras (RTSP in, JPEG out)

The NYCTMC cameras publish a JPEG per camera, so a page loads them directly.
An IP camera speaks RTSP or ONVIF, which no browser plays. The server takes a
frame with ffmpeg and answers the browser with a JPEG, so every page keeps one
contract: a camera has a name, a position and an image URL.

Create `server/cams.json` (or set `METAOS_IPCAMS` to another path):

```json
{
  "cameras": [
    {
      "id": "lobby",
      "name": "Lobby east",
      "area": "Midtown",
      "input": "rtsp://viewer:${CAM_PASSWORD}@10.0.0.5:554/stream1",
      "latitude": 40.758,
      "longitude": -73.9855,
      "enabled": true
    }
  ]
}
```

`id` is lowercase letters, digits, `-` or `_`, at most 41 characters, and it is
the name in the URL. `input` is required. `name`, `area`, `latitude` and
`longitude` are optional; a camera without both coordinates stays off the map
list and is still listed on `/api/ipcam`. `${NAME}` is replaced from the server
environment, so a password can live in the service environment instead of this
file. Error text is redacted (`rtsp://***@host`, `password=***`) before it
leaves the module.

Each camera is grabbed at most once per 5 seconds (`IPCAM_SNAPSHOT_TTL_MS`),
concurrent requests share one ffmpeg run, and at most 2 run at once
(`IPCAM_MAX_CONCURRENT`). Numbers are environment settings, not code edits.

ffmpeg must be installed where this server runs (`apt install ffmpeg` on the
image). Without it, `/api/ipcam/:id/snapshot` answers 502 saying ffmpeg is not
installed; no other route changes behaviour.

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
| `FIRMS_MAP_KEY` | NASA FIRMS map key (free). Without it `/api/fires` answers 503 and the map offers no fire layer. Never in a request, a commit, or a log. |
| `METAOS_IPCAMS` | Path to the IP camera config. Default `server/cams.json`. |
| `CAM_*` | Any variable a `cams.json` `input` refers to, for camera credentials. |
| `FFMPEG` | ffmpeg binary name or path, default `ffmpeg`. |
| `IPCAM_SNAPSHOT_TTL_MS` / `IPCAM_GRAB_TIMEOUT_MS` / `IPCAM_MAX_CONCURRENT` | Frame cache life (5000 ms), per-grab timeout (8000 ms), parallel grabs (2). |
| `PORT` | Listen port, default `8080`. |

Per-product prompt profiles (categories + limitations) are derived from
`js/products.js` in `model.mjs` (`PRODUCT_PROFILES`), so the server and
the clients cannot drift.

## The in-app agent chat (`POST /api/agent/ask`)

Every app carries a chat box that talks to this server: `js/agent-chat.js`
on the product pages, and the division console (`trio/agent.js`) on Vigiles,
Ignis and Medicus. Both post the same shape:

```json
{ "app": "officina", "question": "what does this sheet show?", "context": "what the page is showing right now" }
```

The answer is `{ reply, app, model, latency_ms, spend }`. `division` is still
accepted instead of `app` so the three division pages keep working, and an
unknown `app` falls back to the general persona rather than refusing, so a
page added later is never a dead chat box. Personas live in
`server/agent-chat.mjs` (`APP_PROFILES`): vigiles, ignis, medicus, science,
musica, officina, custos, boards, aegis, nervus, messages, monitor, notes,
and `general`.

Same two gates as the assessment path (`ASSESS_LIVE_MODEL`, `SPARK_API_KEY`)
and the same `$75` ledger (`server/budget.mjs`), checked before the call and
recorded after. It uses the **contributor** model
(`muse-spark-1.3-contributor`) with an explicit `max_tokens`, because the
model bills its reasoning against that budget: a 1200-token cap returned an
empty answer on 3 of 14 app questions, so the default is 3000.

| Variable | Meaning |
| --- | --- |
| `METAOS_CHAT_MODEL` | Model id for the chat. Default `muse-spark-1.3-contributor`. |
| `METAOS_CHAT_MAX_TOKENS` | Completion cap per question. Default `3000`; raise it if a page reports "used all … tokens". |
| `METAOS_CHAT_TIMEOUT_MS` | Per-request timeout. Default `45000`. |
| `METAOS_CHAT_ENDPOINT` | Point the chat at a local OpenAI-compatible server instead. |

`tools/proof_agent_chat.sh` starts the server with these gates open, asks each
app one live question through the same endpoint the on-page box uses, and
prints every reply plus the ledger's estimated spend. It stops before a
configurable cap (`METAOS_CHAT_MAX_SPEND_USD`, default `$0.50`).

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

## Local message bus (`server/bus.mjs`, R2-T3 Section A)

Local-only, file-backed bus. Node stdlib only, no npm deps, no
Upstash/Redis import. Default port **18935** (the board port
`js/site-chat.js` already uses); binds **127.0.0.1 only**.

```sh
node server/bus.mjs            # BUS_PORT=18935, data dir below
node server/bus.test.mjs       # selftest: random port, exits 0/1
```

Data dir (one location, outside the git tree): `$BUS_DATA_DIR`, else
`$METAOS_STATE/bus`, else `~/.local/state/metaos/bus`.

| Endpoint | Notes |
| --- | --- |
| `GET /` | `{ ok, service, board_compat, dataDir, rooms }` |
| `GET /health` | `{ ok, store: "file", dataDir, rooms, count, counts, lastWrite, uptimeSec, pageSize, maxLimit }` |
| `GET /rooms` | `[{ room, count }]`; `general` always exists |
| `POST /rooms { room }` | create; 200 exists / 201 created; needs token |
| `GET /rooms/<room>/messages?since=<n>&limit=<k>` | board-compat lines + parallel `items`; `since=-1`/missing = all; `limit` 1–1000 |
| `POST /rooms/<room>/messages { nick, text, attachmentIds? }` | 201 `{ index, id, ts, delivery }`; needs token |
| `POST /rooms/<room>/notify { severity, topic, text }` | 201 `{ index, id (ntf-…), seq }`; needs token |
| `GET /rooms/<room>/history?cursor=<id\|seq>&limit=<k>` | paged items, oldest-first; default page size 50, max 200; `nextCursor` |
| `GET /rooms/<room>/search?q=<text>&limit=<k>` | case- and accent-insensitive over nick+text; max 200 |
| `GET /rooms/<room>/presence` | `{ online, count }`, 60 s expiry |
| `POST /rooms/<room>/presence { nick, action }` | `join`/`leave`/`heartbeat`; needs token |
| `POST /rooms/<room>/join { nick }` | presence-join alias; needs token |
| `POST /rooms/<room>/attachments { filename, mime, dataBase64 }` | 1 MiB cap; allowlist `image/png, image/jpeg, text/plain, application/pdf`; named codes `attachment_malformed` / `attachment_too_large` / `attachment_mime_not_allowed` / `attachment_filename_invalid`; needs token |
| `GET /rooms/<room>/attachments/<id>` | raw bytes with stored MIME |
| `POST /rooms/<room>/prune { before, keep_last? }` | retention-guarded: refuses below 500 (`retention_would_leave_fewer_than_500`); needs token |
| `GET /rooms/<room>/events?cursor=<seq\|id>` | SSE `data:` JSON per message + `: heartbeat`; replays missed then streams live; `Last-Event-ID` also honoured |

Validation mirrors `board/board.mjs` (room `[a-z0-9-]{1,32}`, nick/text
single-line 1–40/1–2000, 16384-byte body cap, `ntf-` id shape), so
`js/site-chat.js` reads work unchanged; writes need the local token
(`<dataDir>/token`, mode 0600, created on first boot) via
`x-bus-token` or `Authorization: Bearer`. Every stored item carries
`delivery: { state: "stored", reason }`; refusals are 4xx with a named
`code` and `delivery.state: "failed"`. Logs are one JSON line per
write (`{ ts, room, id, result }`) — never the body. Appends are
serialised through a single-writer chain. The server never
auto-deletes; `/prune` keeps seqs stable (no renumbering).

On-disk format: `<dataDir>/rooms/<room>.jsonl` (one message object
per line: `id, seq, room, nick, text, ts, tsMs, kind, delivery`, plus
`severity/topic/notifyId` for notifies and `attachments` when
linked); `<dataDir>/attachments/<room>/<id>-<safe-name>` (raw bytes,
record keeps the relative `attachments/<room>/…` path only — never
inside the JSONL); `<dataDir>/presence.json` (ephemeral snapshot);
`<dataDir>/token` (0600); `<dataDir>/meta.json` (counts/lastWrite).
Migration from the old relay: Upstash `muse-bus` / `muse-bus:room:<r>`
lists (`<nick>: <text>` lines, newest-500 trim) and `board/...jsonl`
`{ room, line }` records map to bus items by parsing the line,
assigning `seq` in order, `id = msg-<16 hex>`, `ts` from the
`[ts:…]` suffix (or file mtime when absent), and copying any
`BLOB:`-style side keys to `attachments/` with the relative path
recorded. Remote path is off by default: `BUS_UPSTASH` unset/empty
runs local; `BUS_UPSTASH=1` refuses to start. No Upstash token is
read in the default path (`process.env` reads are only `BUS_DATA_DIR`,
`METAOS_STATE`, `BUS_UPSTASH`, `BUS_PORT`/`BOARD_PORT`).
