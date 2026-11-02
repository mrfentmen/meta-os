# crates/assess-server — the record shapes, worked (B138)

The crate writes exactly three kinds of thing: a queue job it builds, HTTP
response bodies, and (through the guardrail crate) a ledger entry. It also
writes one stderr line per queue fallback. Each is below with every field
annotated. Values that a documentation example must invent are labelled
**illustrative**; no example is presented as a captured run.

## 1. Queue job envelope — built by `build_queue_job` (`main.rs:194-212`)

```json
{
  "version": 1,
  "kind": "trio-assessment",
  "id": "trio-0123456789abcdef0123456789abcdef",
  "product": "ignis",
  "timestamp": "2026-11-02T00:00:00.000Z",
  "image": {
    "mediaType": "image/jpeg",
    "byteLength": 1024,
    "sha256": "<64 lowercase hex of the frame bytes>",
    "dataUrl": "data:image/jpeg;base64,<the same frame>"
  }
}
```

| Field | Value / rule | Source |
|---|---|---|
| `version` | always `1` (`QUEUE_JOB_VERSION`, line 25) | 207 |
| `kind` | always `"trio-assessment"` (line 26) | 207 |
| `id` | `trio-` + first 32 hex of `sha256(product \0 timestamp \0 frame)`, delegated to `queue_core` | 190-192, 204 |
| `product` | the validated product, echoed verbatim | 208 |
| `timestamp` | the validated ISO-8601 string, echoed verbatim | 209 |
| `image.mediaType` | fixed `"image/jpeg"`: validation only admits JPEG | 210 |
| `image.byteLength` | `frame.len()` | 210 |
| `image.sha256` | `hex(Sha256(frame))`, 64 lowercase chars | 204, 210 |
| `image.dataUrl` | `data:image/jpeg;base64,` + standard base64 of the frame | 211 |

The illustrative id is the sibling `queue-core-records.md` convention; the
algorithm above fixes it, and the crate never accepts a caller-supplied id.

Refusals before a job exists: bad product, empty timestamp, empty frame
(`main.rs:195-203`), each `queue_submit_failed`.

## 2. Queue result envelopes — accepted by `parse_queue_result_envelope` (`main.rs:265-338`)

### 2a. Pax-agreed shape (the primary one)

```json
{
  "job_id": "trio-0123456789abcdef0123456789abcdef",
  "status": "ok",
  "assessment": { "product": "ignis", "...": "the v2 contract object" },
  "error": null
}
```

| Field | Rule | Source |
|---|---|---|
| `job_id` | must equal the requested id | 267-271, 320-322 |
| `status` | `pending` / `ok` / `failed` | 323-336 |
| `assessment` | required object for `ok`; forbidden for `pending`/`failed`; carried verbatim | 324-330 |
| `error` | must be absent/null for `ok`; string or absent for `failed` | 331-337 |

Normalised to `QueueResult::Done { job_id, assessment }` (254-258). The
assessment is **not** validated here; `handle_assess` runs `contract_check`
before it can become a 200 (`main.rs:618-622`).

### 2b. Step-2 proposed shape (still accepted)

```json
{
  "version": 1,
  "kind": "trio-assessment-result",
  "jobId": "trio-0123456789abcdef0123456789abcdef",
  "status": "pending"
}
```

| Field | Rule | Source |
|---|---|---|
| `version` | must be `1` (`QUEUE_RESULT_VERSION`, line 27) | 276-278 |
| `kind` | must be `"trio-assessment-result"` (line 28) | 279-281 |
| `jobId` | must equal the requested id | 282-284 |
| `status` | `pending` / `done` / `failed` | 285-310 |
| `assessment` | required object for `done` | 288-291 |
| `error` | optional string for `failed`; non-string refused | 292-297 |

### 2c. What is refused

`job_id`/`jobId` mismatch, version != 1, wrong kind, `done` without an
assessment object, `pending` with an assessment, `failed` with a non-string
error, `ok` with an error, and any unknown status — all
`queue_fetch_failed` with `Queue result envelope malformed: <detail>`
(`main.rs:260-262`, 268-338).

## 3. Model request body — built inside `assess_with_model` (`main.rs:441-452`)

```json
{
  "model": "muse-spark-1.3",
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "<the product prompt>" },
        { "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,<frame>" } }
      ]
    }
  ]
}
```

| Field | Rule | Source |
|---|---|---|
| `model` | `guardrail::SPARK_MODEL` (`muse-spark-1.3`) | 442 |
| `messages[0].role` | always `"user"` | 444 |
| `content[0]` | text part, the prompt from `build_spark_prompt` | 439, 446 |
| `content[1]` | image part, the frame re-encoded as a JPEG data URL | 440, 447 |
| `Authorization` | `Bearer <key>` header, never in the body | 461 |

The response is read at `choices[0].message.content` (`main.rs:473-486`); a
string or an array of text parts is accepted, anything else is
`model_call_failed`. The guardrail ledger is updated before the content is
read, because a completed call is billable (`main.rs:468-472`).

## 4. HTTP response bodies

All bodies are JSON, written by `send_json` (`main.rs:634-655`), with
`Access-Control-Allow-Origin: *` and `Connection: close`.

| Status | Body | Where |
|---|---|---|
| 200 | the contract object, unchanged | 620-621 |
| 400 | `{"error":"<all validation errors joined by \"; \">"}` | 578-581 |
| 413 | `{"error":"request body exceeds 12582912 bytes"}` | 739-741 |
| 404 | `{"error":"not found: <path>"}` or `{"error":"unknown route: <path>"}` | 668-672, 781-783 |
| 405 | `{"error":"method not allowed: use POST"}` / `use GET` | 750-753, 766-769 |
| 502 | `{"error":"Model response failed contract validation: <errors>"}` | 570-573 |
| 502 | `{"error":"<model transport failure>"}` | 613-615 |
| 503 | `{"error":"<held or not configured message>"}` | 613-615 |

No 500 body exists: an unexpected panic ends the connection (finding 8 in
`assess-server.md`).

## 5. stderr fallback line — one per queue failure (`main.rs:600-611`)

```
queue fallback: <error message>; falling back to the direct Spark path
```

The message always ends with the fixed suffix; when a job id exists the line
names it (`for job <id>`), and a failed result appends the agent's error after
a colon (`600-607`). Examples of the variable part:

- `queue fallback: Cannot build a queue job without a timestamp.; ...`
- `queue fallback: Queue submit failed with HTTP 503.; ...`
- `queue fallback: queue result failed for job trio-<id>: agent overloaded; ...`

The same fallthrough happens for a poll timeout (`main.rs:608-611`). Nothing
is written to a file: the log sink is the `log` function in `Deps`
(`main.rs:538`), `eprintln!` in production (`545-547`).

## 6. Guardrail ledger entry — written by `guardrail::record` (`main.rs:471`)

The crate does not write this file itself; it calls the guardrail crate at the
path from `SPARK_GUARDRAIL_STATE` (`main.rs:524-528`). The file is one JSON
object (`crates/guardrail/src/lib.rs:81-102`):

```json
{
  "calls": 1,
  "est_cost_usd": 0.000009,
  "log": [
    {
      "ts": "2026-10-30T00:00:00Z",
      "kind": "assess:ignis",
      "model": "muse-spark-1.3",
      "input_tokens": 1000,
      "output_tokens": 200,
      "latency_ms": 850,
      "est_cost_usd": 0.000009,
      "cum_est_cost_usd": 0.000009
    }
  ]
}
```

| Field | Rule | Source (guardrail crate) |
|---|---|---|
| `calls` | incremented once per billable response | 84-85 |
| `est_cost_usd` | cumulative, rounded to 6 dp | 86 |
| `log[].ts` | fixed literal `2026-10-30T00:00:00Z` | 89 |
| `log[].kind` | `assess:<product>` | 89, `main.rs:471` |
| `log[].model` | response `model`, else the default | 89, `main.rs:470` |
| `log[].input_tokens` / `output_tokens` | `usage.prompt_tokens`/`completion_tokens` or the OpenAI names, default 0 | 88-90, `main.rs:469-470` |
| `log[].est_cost_usd` | this call, 6 dp | 91 |
| `log[].cum_est_cost_usd` | running total after this call | 92 |

A write failure is ignored (`crates/guardrail/src/lib.rs:64-69`) — see finding
13 in `assess-server.md`.
