# Record — crates/os-identity (B049)

Scope: `crates/os-identity/src/lib.rs` (938 lines, one module). The Python
original is `os/mos/capabilities.py`; parity claims below are against that
file's line numbers. Every claim cites the Rust line range it comes from.

## What it is

The capability registry for the bus: agents register what they can do and
heartbeat it; the overseer asks which agents cover a job's requirements,
are fresh, and have spare capacity. Storage sits behind the `CapStore`
trait (`lib.rs:200-217`), so the crate itself has no network code.

Keys, from `Config::{key_for,index}` (`lib.rs:98-105`):

- `<ns>:<nick>` — hash with `caps/roles/max_jobs/host/updated/dm/info`
- `<ns>:index` — sorted set, member `nick`, score `updated`

Default namespace `muse-bus:cap` (`lib.rs:56`); default staleness 900 s
(`lib.rs:60`).

## Operations — what each does, and where

| Operation | Behaviour | Lines |
|---|---|---|
| `Config::from_env` | `MUSE_RELAY_CAPNS` (non-empty only) and `MUSE_RELAY_CAP_STALE` (parsed `i64`, invalid ignored) | 82-95 |
| `AgentRecord::from_fields` | missing `caps`→`""`, `max_jobs`→`"1"`, `updated`→`"0"`, `host`→`""`; unknown fields ignored | 126-137 |
| `AgentRecord::to_fields` | emits non-empty fields only | 140-160 |
| `AgentRecord::cap_set` | split `caps` on `,`, drop empties | 164-170 |
| `register` | validates, normalises caps (`trim`→`lowercase`→`sort`→`dedup`), writes hash then index, returns `true` | 312-357 |
| `touch` | `get` first; unknown → `Ok(false)`; else writes `updated` + index score | 362-373 |
| `unregister` | `del` hash then `zrem` index; always `Ok(true)` | 375-383 |
| `get` | empty hash → `None`, else typed record | 385-396 |
| `agents` | index read error → empty list; missing hash skipped; per-agent read error propagates | 398-412 |
| `active_claims` | counts jobs with `status == "claimed"` and `claim == nick`; any job read error → 0 | 414-423 |
| `find_for` | fresh + caps superset + `active_claims < max(1,max_jobs)`; sorted nicks | 428-460 |
| `prune_stale` | unregisters every non-fresh agent; sorted removed list | 462-478 |
| `is_fresh` | `now - updated <= stale_after`; unparseable → false | 268-273 |

Capacity is `max(1, max_jobs)` (`lib.rs:451`), so `0` and negatives behave
as `1` — the same clamp as Python `max(1, max_jobs)` (`capabilities.py:155`).

## What it refuses

| Refusal | Trigger | Value | Lines |
|---|---|---|---|
| `RegisterError::NickRequired` | `nick.trim().is_empty()` | `RegistryError::Validation(...)`, message `nick required` | 321-323, 226-236 |
| `RegisterError::AtLeastOneCapabilityRequired` | every capability blank after trim/lower | `RegistryError::Validation(...)`, message `at least one capability required` | 324-341, 226-236 |
| store failure on register | `hset` or `zadd` error | `RegistryError::Store(StoreError)` via `From` | 258-261, 354-355 |
| unknown heartbeat | `touch` on absent hash | `Ok(false)` | 363-365 |
| any store error in `touch`/`unregister`/`get`/`find_for`/`prune_stale` | trait returns `Err` | `Err(StoreError)` | 362-396, 428-478 |
| index read error in `agents` | `zrange` returns `Err` | `Ok(vec![])` — deliberately swallowed | 399-402 |
| job read error in `active_claims` | `job_claims` returns `Err` | `0` — deliberately swallowed | 415-422 |

Validation runs before any write, so a refused `register` stores nothing
(`lib.rs:321-341` precede the `hset` at 354).

## What it writes

`register` writes, in this order:

1. hash `<ns>:<nick>` — `caps` (comma-joined, sorted, unique), and
   `max_jobs`, `host`, `updated` always non-empty; `roles`, `dm`, `info`
   only when non-empty (`lib.rs:344-351`, `to_fields` 140-160).
2. sorted-set `<ns>:index` — member `nick`, score `now` seconds
   (`lib.rs:355`).

`touch` rewrites only `updated` on the hash and the index score
(`lib.rs:368-369`). `unregister` deletes both (`lib.rs:377-378`). The
crate writes no files and no ledger of its own.

## Freshness and matching

`is_fresh` is the only freshness rule (`lib.rs:268-273`). It is inclusive:
exactly `stale_after` old is fresh. An unparseable `updated` is stale. A
future `updated` is fresh because the difference is negative.

`find_for` lowercases and trims requirements, drops blanks
(`lib.rs:429-439`), then applies three filters in order: freshness (443-445),
capability superset (446-449), capacity (451-453). Ties are returned sorted
by nick (`lib.rs:456`).

## MemoryStore

`MemoryStore` (`lib.rs:484-570`) is the in-memory `CapStore`: hashes in a
`HashMap`, sorted sets as `BTreeMap<member, score>`, job claims as a flat
`Vec`. `zrange` sorts `(score, member)` pairs and returns members
(`lib.rs:557-569`), matching Redis `ZRANGE` order for equal scores.

## Findings (B052 — documentation vs code)

1. **"Error paths mirror Python exactly" is too strong.** The header says
   so (`lib.rs:41-44`), but `active_claims` folds per-job reads into one
   call and returns 0 on a per-job failure (`lib.rs:414-423`), where
   Python would propagate the per-job read (`capabilities.py:122-136`).
   The header now qualifies this; the behavioural deviation stays.
2. **Empty `MUSE_RELAY_CAPNS` differs from Python.** Python takes the
   empty string as the namespace (`capabilities.py:25`), producing keys
   like `:nick`; Rust ignores the empty value and keeps
   `muse-bus:cap` (`lib.rs:84-88`). The `from_env` doc did not state it;
   it does now.
3. **`is_fresh` can overflow on an extreme negative `updated`.** The
   subtraction at `lib.rs:270` is i64; `updated = i64::MIN` makes
   `now - updated` overflow and panic in a debug build, while Python's
   arbitrary-precision int does not (`capabilities.py:114-120`). No
   stored record can carry that value through `register` (it writes
   `now`), but a corrupted store can. Reported; not fixed.
4. **`cap_set` does not deduplicate.** Python builds a `set`
   (`capabilities.py:147`); Rust returns a `Vec` and keeps duplicates
   (`lib.rs:164-170`). `register` stores deduplicated caps, so this is
   reachable only through a crafted/corrupt record; `find_for` is
   unaffected because it only asks "contains".
5. **`to_fields` can omit `updated`/`max_jobs`.** Both are pushed only
   when non-empty (`lib.rs:149-151`), while Python's `register` always
   writes `str(int(max_jobs))` and `str(now)` (`capabilities.py:56-57`).
   Unreachable through `register`, reachable through a caller-built
   `AgentRecord` with empty strings. Reported; not fixed.
6. **Quoting contract is underspecified.** The header says the transport
   adapter handles URL-quoting "including ... hash field values and zset
   members" (`lib.rs:21-26`). Python also leaves the **hash key**
   unquoted (raw nick, `capabilities.py:29-30`) while quoting zset
   members (`capabilities.py:72, 91, 97-99`). An adapter that quotes keys
   would make `get` miss. Listed as a gap task in
   `os-identity-gaps.md` G3.
