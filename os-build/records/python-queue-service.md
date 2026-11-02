# Python queue service — behaviour record (B223)

Source: `server/queue/queue_service.py` (218 lines). Storage:
`server/queue/trio_store.py`; dispatch log: `server/queue/crew_records.py`.
Every claim cites the file and line range it was read from.

## What it is

The HTTP service end of the Trio queue (OS queue). The Trio server POSTs
the envelope `server/queue.mjs buildQueueJob()` produces; a resident agent
answers it; the Trio server polls the result (`queue_service.py:1-38`).
Stdlib only. The process opens its store once at import (`:56-63`) and
serves until killed.

## Endpoints

| Route | Input | Success | Refusal | Where |
|---|---|---|---|---|
| `POST /jobs` | one `trio-assessment` v1 envelope | `201 {"jobId": id}` (200 if already filed) | `400 {"error": "refused job: <reason>"}` or `400 {"error": "request body is not JSON"}` | `:179-204` |
| `GET /jobs/<id>/result` | job id in path | `200` stored result envelope | `404 {"status": "pending"}` if filed but unanswered; `404 {"status": "unknown", "error": ...}` if no such job | `:108-131` |
| `GET /health` | none | `200` with `ok`, `service`, `store`, `store_fallback`, `namespace`, `result_prefix` | — | `:108-120` |
| `POST /dispatch-simulated[/suffix]` | JSON package with `"simulated": true` | `201` receipt with `receipt_id`, `simulated: true`, `received_at`, SIMULATED note | `400` non-JSON, or `400` when `simulated` is not literally `true` | `:133-177` |
| anything else | — | — | `404 {"error": "not found"}` | `:132-133`, `:181-183` |

## Envelope validation

`validate_envelope(env)` returns an error string or `None`
(`:64-92`). In order:

| Check | Refusal string |
|---|---|
| not a dict | `envelope is not a JSON object` |
| `version != 1` or `kind != "trio-assessment"` | `not a trio-assessment v1 envelope` |
| `id` missing / not a non-empty str | `envelope has no job id` |
| `product` not in `trio_repo.product_ids()` | `unknown product '<value>'` |
| `timestamp` missing / not a non-empty str | `envelope has no timestamp` |
| `image` not a dict | `envelope has no image object` |
| `image.dataUrl` not a `data:image/jpeg;base64,` string | `image.dataUrl is not a JPEG data URL` |
| data URL payload does not base64-decode | `image.dataUrl does not base64-decode` |
| `image.byteLength != len(decoded)` | `image.byteLength does not match the decoded frame` |
| `image.sha256 != sha256(decoded).hexdigest()` | `image.sha256 does not match the decoded frame` |

A failed check refuses the job; nothing is filed (`:198-201`).

## Writes

- `JOBS.submit(env)` files the job in the configured store and returns
  `(job_id, created)`; a duplicate deterministic id returns `created =
  false` (`:202-204`, `:374+` of `trio_store.py`).
- `/dispatch-simulated` appends one record to the crew dispatch log and
  returns a receipt; `service_route` is the path suffix after the route,
  or `/default` (`:151-175`).
- Store selection is `trio_store.open_store(LOCAL_DB)`, with
  `TRIO_LOCAL_DB` or `trio-queue-local.db` as the fallback file; the
  health route states when the fallback is in use (`:56-63`, `:112-119`).
- Request logs go to stderr, keeping stdout clean (`:97-98`).

## Runtime

`python3 queue_service.py [--port 8935]`; binds `127.0.0.1` only
(`:205-218`). A fallback store prints an explicit warning at startup
(`:209-213`).

## Findings (reported, not fixed)

1. **Import has side effects.** `STORE`, `FELL_BACK`, and `JOBS` are
   created at module import (`:56-63`), so importing the module merely to
   call `validate_envelope` — as the existing tests do — opens a store and
   may touch the local SQLite file.
2. **`byteLength` accepts `true` for a one-byte frame.** The check is
   `!=` (`:85-86`), and Python treats `True == 1`, so a 1-byte JPEG with
   `"byteLength": true` passes. The SHA check still pins the bytes.
3. **No request-body cap.** `Content-Length` is read and that many bytes
   are read into memory with no maximum (`:141-145`, `:186-190`); a large
   POST is a memory cost before validation can refuse it.
4. **Empty job ids reach the store on GET.** `/jobs//result` slices an
   empty id and performs a store lookup (`:121-130`); it answers `unknown`
   rather than refusing the path.
5. **The SIMULATED route accepts any suffix.** `startswith`/slicing
   records the suffix as `service_route` (`:151-156`, `:165-169`); the
   route is still local-only and labelled SIMULATED in the receipt.
