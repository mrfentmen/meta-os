# Worked records — every shape `crates/queue-store` writes

One real example of each kind, built from the writes in
`crates/queue-store/src/lib.rs` on `main`, 2026-11-02 (after this
pass's doc edits). Values are illustrative but field-for-field what the
code stores; no field below is invented. `ns = "trio"`,
`jid = "trio-1a2b3c4d5e6f"`.

## 1. Submitted job hash — `trio:trio-1a2b3c4d5e6f`

Written by `JobStore::submit` (`lib.rs:385-401`). Redis hash; SQLite
rows in `hashes` with the same key.

| Field | Example | Type | Meaning / source |
|---|---|---|---|
| `status` | `open` | string | fixed literal at `lib.rs:393` |
| `kind` | `trio-assessment` | string | `envelope["kind"]`, empty if absent (`lib.rs:394`) |
| `version` | `1` | JSON value rendered as text | `envelope["version"]`, empty if absent (`lib.rs:395`) |
| `product` | `ignis` | string | `envelope["product"]`, empty if absent (`lib.rs:396`) |
| `timestamp` | `2026-10-30T06:00:00.000Z` | string | `envelope["timestamp"]`, empty if absent (`lib.rs:397`) |
| `created_at` | `1761804000` | unix seconds | `now_secs()` at submit (`lib.rs:390`, `398`) |

Readers: `job_fields` returns the hash verbatim (`lib.rs:403-405`);
`open_job_ids` reads only `status` (`lib.rs:410-414`); the agent reads
`status`/`claim` fields while serving.

## 2. Envelope string — `trio:trio-1a2b3c4d5e6f:job`

Written by `set_body` at `lib.rs:391`; the value is
`serde_json::Value::to_string()` of the caller's envelope. It is opaque
to the crate: no field is validated, and it is stored before the hash
is written.

```
{"id":"trio-1a2b3c4d5e6f","kind":"trio-assessment","version":1,
 "product":"ignis","timestamp":"2026-10-30T06:00:00.000Z",
 "image":{"dataUrl":"data:image/jpeg;base64,…","byteLength":12345,
          "sha256":"…"}}
```

`job_envelope` parses it back and returns `None` for missing,
non-JSON, or non-object values (`lib.rs:406-409`).

## 3. Index zset — `trioindex`

Written by `zadd(index_key(ns), created_at, jid)` at `lib.rs:400`.

| Member | Score |
|---|---|
| `trio-1a2b3c4d5e6f` | `1761804000` |

`open_job_ids` walks this zset and filters by the job hash's
`status == "open"` (`lib.rs:410-414`). Stale members are never removed
by the crate.

## 4. Claim hash fields added to `trio:trio-1a2b3c4d5e6f`

Written only after the NX claim succeeds (`lib.rs:419-430`).

| Field | Example | Type |
|---|---|---|
| `status` | `claimed` | string |
| `claim` | `worker-1` | string (`who`) |
| `claimed_at` | `1761804010` | unix seconds |
| `lease_until` | `1761804070` | `claimed_at + lease` |
| `lease` | `60` | seconds, rendered from `u64` |

The mutex itself is the separate key `trio:trio-1a2b3c4d5e6f:claim`
with the worker name and the lease expiry (`lib.rs:420`).

## 5. Finished job hash — `trio:trio-1a2b3c4d5e6f`

`finish` writes three fields and deletes the claim key
(`lib.rs:442-448`). It does not clear the claim fields already in the
hash.

| Field | Example |
|---|---|
| `status` | `done` |
| `note` | `` (empty string) |
| `done_at` | `1761804065` |

## 6. Result envelope — `trio:trio-1a2b3c4d5e6f:result`

`put_result` stores `result.to_string()` verbatim (`lib.rs:438-441`).
The crate does not validate it; the frozen shape is the contract:

| Field | Example | Meaning |
|---|---|---|
| `job_id` | `trio-1a2b3c4d5e6f` | also selects the key; missing → `""` |
| `status` | `ok` or `failed` | ruled shape |
| `assessment` | object or `null` | v2 contract object when `ok` |
| `error` | string or `null` | agent's error when `failed` |
| `model` | `muse-spark-1.3` | model that answered |
| `latency_ms` | `1200` | generation latency |
| `completed_at` | `2026-10-30T06:01:05.000Z` | agent timestamp |

## 7. SQLite rows (fallback backend)

For the same job, `SqliteStore` writes (`lib.rs:274-287` for the
schema):

```
kv      ("trio:trio-1a2b3c4d5e6f:job", "<envelope JSON>", NULL)
hashes  ("trio:trio-1a2b3c4d5e6f", "status", "open")
        ("trio:trio-1a2b3c4d5e6f", "kind",   "trio-assessment")
        … one row per non-empty hash field
zsets   ("trioindex", "trio-1a2b3c4d5e6f", 1761804000.0)
kv      ("trio:trio-1a2b3c4d5e6f:claim", "worker-1", 1761804070)
```

Note: the SQLite schema stores `expires` as an integer second here
(`lib.rs:317-330`), where the Python fallback stores a float
(`trio_store.py:301-316`).
