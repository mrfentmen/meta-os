# queue-core — record shapes, worked examples (B114)

Every record below is produced by `crates/queue-core/src/lib.rs`. Values
are illustrative; field names, types and write sites are the code's.
The namespace is `trio` and the job id is the deterministic one for the
example product/timestamp/frame.

## 1. Job hash — `<ns>:<jid>`

Written by `submit` (`lib.rs:404-418`), then extended by `claim`
(`lib.rs:452-460`) and `finish` (`lib.rs:477-491`).

After `submit` (example `now = 1762041600`):

| Field | Value | Written by | Meaning |
|---|---|---|---|
| `status` | `open` | `lib.rs:411` | the job is fileable, not yet claimed |
| `kind` | `trio-assessment` | `lib.rs:412` | copied from the envelope |
| `version` | `1` | `lib.rs:413` | copied from the envelope, stringified |
| `product` | `ignis` | `lib.rs:414` | copied from the envelope |
| `timestamp` | `2026-11-02T00:00:00.000Z` | `lib.rs:415` | copied from the envelope |
| `created_at` | `1762041600` | `lib.rs:416` | the caller's `now`, stringified |

After `claim(jid, "agent-a", 60, 1762041610)`:

| Field | Value | Written by | Meaning |
|---|---|---|---|
| `status` | `claimed` | `lib.rs:454` | a worker holds the lease |
| `claim` | `agent-a` | `lib.rs:455` | claim holder, the same value in the claim key |
| `claimed_at` | `1762041610` | `lib.rs:456` | caller's `now` |
| `lease_until` | `1762041670` | `lib.rs:457` | `now + lease` |
| `lease` | `60` | `lib.rs:458` | seconds |

After `finish(jid, "done", "", 1762041700)`:

| Field | Value | Written by | Meaning |
|---|---|---|---|
| `status` | `done` | `lib.rs:481` | terminal word from the caller; not validated |
| `note` | *(absent)* | `lib.rs:482` | `hset` skips empty values (`lib.rs:344-355`), so `note=""` writes nothing |
| `done_at` | `1762041700` | `lib.rs:483` | caller's `now` |

`finish` also deletes the claim key (`lib.rs:490`).

## 2. Envelope string — `<ns>:<jid>:job`

`set_body` at `lib.rs:409-410`. The value is the caller's
`envelope_json` **verbatim**; the crate never parses or re-serializes it
(finding 3 in `queue-core.md`). Example:

```
{"version":1,"kind":"trio-assessment","id":"trio-0123456789abcdef0123456789abcdef",
 "product":"ignis","timestamp":"2026-11-02T00:00:00.000Z",
 "image":{"dataUrl":"data:image/jpeg;base64,<frame>","byteLength":1024,"sha256":"<64 hex>"}}
```

Read by `job_envelope` (`lib.rs:424-426`), which returns the raw string.

## 3. Claim key — `<ns>:<jid>:claim`

Written by `set_nx_ex` inside `claim` (`lib.rs:444-451`): the value is
the holder (`agent-a`), the TTL is the lease in seconds. Renewed by
`renew_claim` via `set_xx_ex` (`lib.rs:464-466`); deleted by
`release_claim` (`lib.rs:468-471`). The key's existence is the mutex; a
second `claim` before expiry returns false.

## 4. Index — `<ns>index`

`zadd(index_key(ns), now, jid)` at `lib.rs:417`. Member is the job id,
score is `created_at`. `open_job_ids` walks it in score order
(`lib.rs:428-437`) and keeps only jobs whose hash still says `open`.
A duplicate submit does not add a second member (`lib.rs:400-403`).

## 5. Result string — `trio:<jid>:result`

`set_body(result_key(job_id), result_json)` at `lib.rs:473-475`. The
prefix is always `trio`, independent of the job namespace
(`lib.rs:247-249`). The value is the caller's JSON **verbatim**; the
crate does not validate that its `job_id` matches the key (finding 4).
`get_result` returns the raw string (`lib.rs:439-441`).

## 6. What the crate does not write

No files, no log lines, no stderr output. Every record above is a
backend command; `MemoryBackend` holds them in memory only
(`lib.rs:278-381`).
