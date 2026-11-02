# Record — `crates/queue-store`, read from the code

Scope: the Rust crate `queue-store` (B02) as it stands on `main`,
2026-11-02, after this pass's doc-only edits. Sources it ports:
`server/queue/trio_repo.py` and `server/queue/trio_store.py`, both left
untouched. Every claim cites `crates/queue-store/src/lib.rs`
(abbreviated `lib.rs`) and, where relevant, the Python original.

## 1. Repo layer (ports `trio_repo.py`)

- `ProductProfile` (`lib.rs:29-35`) carries `id`, `display_name`,
  `department`, `categories`, `limitations`, all `&'static`.
- `PRODUCTS` (`lib.rs:37-84`) embeds exactly three profiles in the
  order vigiles, ignis, medicus. The Python original loads
  `js/products.js` by spawning node (`trio_repo.py:28-43`); the Rust
  port deliberately embeds the records so the queue is offline
  (`lib.rs:8-12`). The JS file remains the source of truth, so any
  drift is a bug.
- `product_ids()` (`lib.rs:86-88`) returns a `HashMap<String, ()>` —
  a set-shaped answer, but not `HashSet`. Python returns a `set`
  (`trio_repo.py:45-46`).
- `product_profile(product)` (`lib.rs:90-92`) returns
  `Option<&'static ProductProfile>`. Python **raises**
  `KeyError("no product profile …")` (`trio_repo.py:49-54`); the Rust
  caller must handle `None` instead of an exception.

## 2. Key layout and host resolution (ports `trio_store.py`)

- `namespace()` (`lib.rs:102-104`) reads `TRIO_JOB_NS` on each call,
  default `trio`. Python captures `NS` once at import
  (`trio_store.py:47`). An empty env value is accepted here and yields
  keys that begin with `:`.
- `RESULT_PREFIX` is the literal `trio` (`lib.rs:106`);
  `result_key()` (`lib.rs:120-122`) uses it regardless of the job
  namespace — the bus-424 ruling, mirrored from
  `trio_store.py:140-141`.
- `job_key` / `envelope_key` / `claim_key` / `index_key`
  (`lib.rs:108-122`) produce `<ns>:<jid>`, `<ns>:<jid>:job`,
  `<ns>:<jid>:claim`, `<ns>index`, matching `trio_store.py:124-138`.
- `host_of_url` (`lib.rs:126-145`) trims the candidate, adds `https://`
  when no scheme is present, then takes the text after `://` up to the
  first `/`, `?`, `#`, or `:`. It is a minimal parser, not a full URL
  parser.
- `resolve_upstash_host` (`lib.rs:147-162`) tries the environment host
  first, then an optional credential REST URL, and returns a typed
  `TrioStoreConfigError` naming `TRIO_UPSTASH_HOST` when both are
  empty/unparseable (`lib.rs:158-161`). Python's order is the same
  (`trio_store.py:99-121`), but its credential lookup is not ported
  (see `queue-store-gaps.md`).
- `resolve_upstash_host_from_env()` (`lib.rs:164-166`) passes `None`
  for the credential URL, so only the env var can configure it.

## 3. Backend surface

`StoreBackend` (`lib.rs:173-189`) has ten methods: `ping`, `get`,
`set_body`, `delete`, `set_nx_ex`, `set_xx_ex`, `hset`, `hgetall`,
`zadd`, `zrange`. All are synchronous and none returns a `Result`;
transport errors cannot be expressed.

### InMemoryStore (`lib.rs:192-267`)

- Entries are `(value, Option<expiry_secs>)`; `live()`
  (`lib.rs:200-212`) drops a key only when `now > expiry`, so the
  expiry second itself is still live.
- `set_nx_ex` refuses when a live value exists; `set_xx_ex` refuses
  when none does (`lib.rs:229-240`).
- `delete` counts only removed **kv** keys; hash and zset entries are
  removed without counting (`lib.rs:221-228`).
- `hset` skips fields whose value is the empty string and counts only
  the writes (`lib.rs:241-250`); `hgetall` returns an empty map for an
  unknown key.
- `zadd` always reports 1 (`lib.rs:251-254`); `zrange` orders by score,
  and ties fall back to the `BTreeMap` member order (`lib.rs:255-264`).

### SqliteStore (`lib.rs:270-367`)

- `open(path)` creates the three tables if absent and returns
  `rusqlite::Result` (`lib.rs:274-287`). There is no default path.
- Expiry is an integer second (`now_secs() + lease`), not the Python
  fallback's float (`trio_store.py:301-316`).
- `set_body` ignores the SQL result and always returns `"OK"`
  (`lib.rs:300-304`); a failed write is not reported.
- `delete` counts kv rows only (`lib.rs:305-316`).
- `set_nx_ex` checks for a live key then inserts; `set_xx_ex` checks
  for absence then updates (`lib.rs:317-330`). Both return the SQL
  success flag, not a distinct refusal type.
- `hset` skips empty values (`lib.rs:331-341`); `zadd`/`zrange` read
  and write the `zsets` table (`lib.rs:342-366`).

## 4. Job semantics (`lib.rs:376-450`)

- `submit(envelope)` returns `(jid, created)` (`lib.rs:385-401`).
  - `jid` is `envelope["id"]` or `""` when absent (`lib.rs:386`).
  - A non-empty job hash means "already filed" and returns
    `(jid, false)` without rewriting the envelope (`lib.rs:387-389`).
  - A new job writes `<ns>:<jid>:job` = the envelope JSON string
    (`lib.rs:391`), the hash fields `status=open`, `kind`, `version`,
    `product`, `timestamp`, `created_at` (`lib.rs:393-398`), and the
    index member `jid` with score `created_at` (`lib.rs:400`).
- `job_fields` (`lib.rs:403-405`) is a raw hash read; unknown key gives
  an empty map.
- `job_envelope` (`lib.rs:406-409`) returns `None` for missing,
  non-JSON, or non-object stored values.
- `open_job_ids` (`lib.rs:410-414`) walks the whole index zset and
  keeps only ids whose hash `status == "open"`. It does not remove
  stale index members.
- `get_result` (`lib.rs:415-418`) reads `trio:<jid>:result` with the
  same missing/non-JSON/non-object → `None` rule.
- `claim(jid, who, lease)` (`lib.rs:419-430`) is `SET NX EX` on
  `<ns>:<jid>:claim` (`lib.rs:420`); on success it writes
  `status=claimed`, `claim`, `claimed_at`, `lease_until`, `lease`
  (`lib.rs:423-427`). It does **not** check that the job exists first.
- `renew_claim` (`lib.rs:431-433`) is `SET XX EX` on the claim key;
  `release_claim` (`lib.rs:434-437`) deletes it and reports nothing.
- `put_result(result)` (`lib.rs:438-441`) writes
  `trio:<result["job_id"]>:result`; a missing `job_id` becomes `""`
  and therefore the key `trio::result` (`lib.rs:439`).
- `finish(jid, status, note)` (`lib.rs:442-448`) writes `status`,
  `note`, `done_at` to the job hash (`lib.rs:444-447`) and releases the
  claim (`lib.rs:448`). It does not check the current status, so it can
  overwrite a claimed or finished job.

## 5. What it refuses, and what it does not

The crate has exactly one typed refusal: `TrioStoreConfigError` from
`resolve_upstash_host` when no host is configured
(`lib.rs:147-162`). Everything else reports failure through `false`,
`None`, an empty collection, or `0`:

- a duplicate `submit` is not an error — it returns `created=false`;
- a lost claim race is not an error — `claim` returns `false`;
- `renew_claim` on a missing/expired claim returns `false`;
- writes to `SqliteStore` never surface a SQL error to the caller.

## 6. What it writes down

Two record families, both Redis-shaped: the job hash plus envelope
string plus index zset (in memory or three SQLite tables), and the
single frozen result envelope at `trio:<jid>:result`. The crate keeps
no log of its own and emits no diagnostics.

## Findings (reported, not fixed)

1. `submit` accepts a missing `id` and files the job under `""`
   (`lib.rs:386`). Python raises `KeyError` at `trio_store.py:382`.
2. `put_result` accepts a missing `job_id` and writes `trio::result`
   (`lib.rs:439`). Python raises `KeyError` at `trio_store.py:455`.
3. `claim` never checks that the job hash exists (`lib.rs:419-430`);
   Python behaves the same (`trio_store.py:433-441`), so this is a
   ported oddity, but a claim can outlive a missing job.
4. `finish` has no status precondition and no claim-owner check
   (`lib.rs:442-448`), so a worker whose lease expired can still mark
   the job done.
5. `SqliteStore::set_body` swallows the SQL error (`lib.rs:302`) and
   reports `"OK"`; a full or read-only database is silent.
6. Expiry units differ from Python (integer seconds here, float
   seconds there); see the header note at `lib.rs:11-16`.
