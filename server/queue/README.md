# Trio queue service + resident agent (the OS-queue leg)

This directory is the production home of the OS-queue leg of the
Meta Trio, moved here from the verified `trio-queue-prototype` after
its live proof (2026-10-30). It is the service end of the transport
`server/queue.mjs` speaks to: the Trio server files assessments as
jobs; a resident agent claims them and answers with real Muse Spark
assessments; the Trio server polls for the result. Apps keep calling
`/api/assess` unchanged, and the direct Spark path in
`server/model.mjs` stays as the fallback.

## The three processes

```
Trio server (server/server.mjs)          queue_service.py           trio_agent.py
POST /api/assess                         POST /jobs                 polls the job index
  buildQueueJob (server/queue.mjs)  ──►    files the envelope   ──►   claims (SET NX lease
  polls GET /jobs/<id>/result       ◄──    serves the result          + heartbeat)
                                           from trio:{jid}:result     spark_gen.generate()
                                                                      validateAssessment
                                                                      writes the result
```

1. **Trio server** — with `TRIO_QUEUE_ENABLED=1` and
   `TRIO_QUEUE_URL` set, `server/queue.mjs` submits the job and
   polls for the result (that wiring is Rowan's lane; the adapters
   are in `server/queue.mjs`).
2. **Queue service** — `python3 queue_service.py [--port 8935]`.
   Files envelopes and serves results over the shared jobs store
   (`trio_store.py`: OS jobs.py semantics over Upstash Redis REST,
   reached through the credential surrogate — no credential value is
   read or logged; a local SQLite fallback exists and is always
   labelled `local-sqlite-FALLBACK`, including in `/health`).
3. **Resident agent** — `python3 trio_agent.py` (or `--once` for a
   single pass). Claims jobs, generates via `spark_gen.py`,
   validates with the repo's own `validateAssessment`
   (`../../js/schema.js`), and writes the result envelope.
   Idempotency is load-bearing: if a result already exists for the
   deterministic job id, generation is skipped — a resubmitted frame
   is never re-billed.

## The wire shape (ruled final)

Job envelope: the exact object `buildQueueJob()` in
`server/queue.mjs` returns (version 1, kind `trio-assessment`,
deterministic id, frame as a JPEG data URL with byteLength + SHA-256,
both verified by the service before filing; resubmission is
idempotent, 201 first filing / 200 after).

Result envelope, stored at Redis key `trio:{jid}:result`:

```json
{"job_id": "...", "status": "ok" | "failed",
 "assessment": { ...v2 contract object... } | null,
 "error": null | "...", "model": "muse-spark-1.3",
 "latency_ms": 4670, "completed_at": "2026-10-30T05:30:58.761Z"}
```

`GET /jobs/<id>/result` returns that envelope with 200, or
`404 {"status": "pending", "job_id": id}` while the job is filed but
unanswered (`"unknown"` when no such job exists). Invalid model
output is NEVER written as an assessment — it lands as
`status: "failed"` with the reason in `error`.

## Environment

| Variable | Read by | Meaning |
|---|---|---|
| `TRIO_QUEUE_ENABLED` | Trio server (`server/queue.mjs`) | `1` turns the queue path on; otherwise the direct Spark path is used. |
| `TRIO_QUEUE_URL` | Trio server | Base URL of this queue service, e.g. `http://127.0.0.1:8935`. Server-side only. |
| `SPARK_API_KEY` | `spark_gen.py` (agent) | The Meta Model API key for the production direct transport. Environment ONLY — never in a file, envelope, log, or commit. Set by Del on the machine that runs the agent. |
| `TRIO_SPARK_VIA_HELPER` | `spark_gen.py` | `1` selects the DEV transport: delegate generation to the connector helper `spark_call.py`, whose vaulted key + own guardrail apply. Sandbox-only path. |
| `TRIO_JOB_NS` | service + agent | Job namespace in the store. Default `trio`; proofs use a scratch namespace (result keys are always `trio:{jid}:result`). |
| `TRIO_STORE` | service + agent | `local` forces the labelled SQLite fallback (tests/dev). |
| `TRIO_LOCAL_DB` | service + agent | Path of the fallback SQLite file (default beside the modules; gitignored). |
| `TRIO_UPSTASH_HOST` | `trio_store.py` | The Upstash store host (a bare host, or the full REST URL). Required for the Redis path: the host is deployment configuration, resolved at runtime from this variable or from the REST URL stored on the `custom.upstash` credential record — it is never hardcoded in the repo. When neither source supplies it, store construction reports the missing configuration and the labelled SQLite fallback engages. |
| `RELAY_URL` | `trio_store.py` | Full store base URL override (wins over `TRIO_UPSTASH_HOST`). |

Spend guardrail: the direct transport counts every call in
`spark_guardrail_state.json` beside `spark_gen.py` (gitignored),
estimates cost at the published rate card ($1.25/M in, $4.25/M out),
and refuses any call that would start at or beyond the **$75** test
budget. The helper transport is counted by the helper's own
guardrail instead — never both.

## Tests

From the repo root (offline; stub transports only, no live calls):

```
python3 -m unittest discover -s tests/queue-python -v
```

Covers: envelope build/verify against the real `buildQueueJob`
(incl. byteLength/SHA-256 tamper refusals), the guardrail stop,
the exact result-envelope shape, a stubbed-generation round trip
with idempotent no-rebill, the direct transport's request shape
with a stubbed HTTP layer, and the HTTP service end to end on the
SQLite fallback. 17 tests.

## Status (honest labels, 2026-10-30)

- **Helper transport (`TRIO_SPARK_VIA_HELPER=1`) — VERIFIED LIVE.**
  Re-proven from this repo copy on 2026-10-30: queue service +
  agent on scratch namespace `trio-scratch-reproof`, job built by
  the real `buildQueueJob` on the steam test frame, result
  `status: ok`, category **"steam or fog"**, model `muse-spark-1.3`,
  latency 4670 ms, assessment independently re-validated with
  `validateAssessment`; spend delta exactly +1 guarded call
  ($0.059492 → $0.066552 on the helper's counter).
- **Direct transport (`SPARK_API_KEY`) — STUB-TESTED ONLY.** The
  request shape (endpoint, model, text + `image_url` data-URL
  parts, key only in the `Authorization` header) mirrors
  SPARK-TRANSPORT-1 in `server/model.mjs` and is covered by a
  stubbed-HTTP unit test, but it has never run against the real API
  with a real key: the sandbox holds no raw key by design. It
  becomes verified when it runs on Del's Mac.
- **Not yet done:** wiring `/api/assess` to submit/poll through
  this service (Rowan's `server/queue.mjs` step), and running the
  service + agent as standing processes instead of by hand.
