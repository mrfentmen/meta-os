# Python trio store — behaviour record (B225)

Source: `server/queue/trio_store.py` (read at 465 lines). This record
describes what the module does, what it refuses, and what it writes.
Citations are `file:line` against the source as read; no behaviour is
inferred from a caller.

## What it is

The OS jobs-store semantics for the Trio queue, over one small
Redis-command surface with two implementations: Upstash REST
(`trio_store.py:152-243`) and a local SQLite file
(`trio_store.py:245-352`). `open_store` chooses between them
(`trio_store.py:354-372`). Job semantics live in `JobStore`
(`trio_store.py:374-465`).

## Inputs

- `JobStore.submit(envelope)` requires a dict with an `id`
  (`trio_store.py:380-399`). It reads `kind`, `version`, `product`,
  `timestamp` with `.get(..., "")`, so a missing field is stored as
  an empty string, not refused.
- `claim(jid, who, lease)` takes a job id, a claimant string and a
  lease in seconds (`trio_store.py:433-441`).
- `finish(jid, status, note="")` takes any status string
  (`trio_store.py:458-465`).
- `put_result(result_env)` requires `result_env["job_id"]`
  (`trio_store.py:454-456`).

## Key layout (namespace from `TRIO_JOB_NS`, default `trio`)

| Key | Shape | Source |
|---|---|---|
| `<NS>:<jid>` | hash: status/kind/version/product/timestamp/created_at, then claim and finish fields | `trio_store.py:124-126`, `380-399`, `433-465` |
| `<NS>:<jid>:job` | string: the full v1 envelope JSON | `trio_store.py:128-130`, `387` |
| `<NS>:<jid>:claim` | mutex: `SET NX EX <lease>` | `trio_store.py:132-134`, `433-441` |
| `<NS>index` | zset: jid -> created_at | `trio_store.py:136-138`, `398` |
| `trio:<jid>:result` | string: result envelope, namespace-independent | `trio_store.py:140-142`, `454-456` |

`_q` percent-encodes every path segment with `safe=""`
(`trio_store.py:144-145`), so a slash in a member cannot become a
path separator.

## Outputs

- `submit` returns `(jid, created)`; a second submit of the same id
  returns `(jid, False)` without writing again
  (`trio_store.py:380-386`).
- `job_fields(jid)` returns the hash, `{}` when absent
  (`trio_store.py:400-401`).
- `job_envelope(jid)` / `get_result(jid)` return a dict, or `None`
  when the key is absent, the JSON does not parse, or the parsed
  value is not a dict (`trio_store.py:403-411`, `421-431`).
- `open_job_ids()` returns ids whose hash exists and whose status is
  exactly `open`, in zset score order (`trio_store.py:413-419`).
- `claim` returns True only when `SET NX` won; `renew_claim` returns
  whatever `SET XX` returned (`trio_store.py:433-443`).
- `release_claim` swallows every exception (`trio_store.py:446-452`).
- `finish` writes `status`, `note`, `done_at` and releases the claim
  (`trio_store.py:458-465`).

## Refusals

| Situation | Behaviour | Source |
|---|---|---|
| No `TRIO_UPSTASH_HOST`, and the credential record carries no URL | `TrioStoreConfigError` naming the missing configuration; there is no hardcoded host | `trio_store.py:99-122` |
| `RELAY_URL` set but unparseable | `TrioStoreConfigError` | `trio_store.py:157-175` |
| Upstash path without the `dynamic_credentials` helper | `TrioStoreConfigError` on the first `_call` | `trio_store.py:176-202` |
| Any Upstash transport error | retried three times, then `RuntimeError` with the last error truncated to 160 chars | `trio_store.py:176-202` |
| Upstash unreachable / `ping` false | `open_store` prints a warning to stderr and returns the SQLite fallback with `fell_back=True` | `trio_store.py:354-372` |

## What it writes

A submission writes the envelope string, the job hash and one zset
member (`trio_store.py:387-398`). A claim writes the claim key and
four hash fields (`trio_store.py:433-441`). A result writes only the
result string (`trio_store.py:454-456`). A finish writes three hash
fields and deletes the claim key (`trio_store.py:458-465`).

## Findings (reported, not fixed)

1. **`submit` trusts the envelope.** A missing `id` raises
   `KeyError`; there is no shape validation here
   (`trio_store.py:380-382`).
2. **`put_result` trusts the result envelope.** A missing `job_id`
   raises `KeyError`; an empty string writes the key
   `trio::result` (`trio_store.py:454-456`).
3. **`claim` does not check that the job exists.** A `SET NX` on an
   unknown id succeeds and `hset` creates a partial hash for it
   (`trio_store.py:433-441`).
4. **`finish` accepts any status string.** There is no terminal-state
   validation (`trio_store.py:458-465`).
5. **SQLite `delete` counts only `kv` rows.** Deleting a key that
   exists only as a hash or zset removes it but returns 0
   (`trio_store.py:290-300`).
6. **`hset` silently drops empty values.** `""` and `None` are
   skipped, so `status=""` is indistinguishable from "not written"
   (`trio_store.py:223-232`, `319-331`).
7. **The result prefix is fixed.** `trio:<jid>:result` ignores
   `TRIO_JOB_NS` by design; a namespaced deployment still shares the
   result prefix (`trio_store.py:140-142`).
8. **`UpstashStore._call` retries every exception**, including a
   deterministic 4xx; a refused request costs three attempts
   (`trio_store.py:176-202`).

## Tests

Missing cases are in `tests/queue-python/test_trio_store_missing.py`
(key layout, host refusal, SQLite lease/expiry, malformed records).
