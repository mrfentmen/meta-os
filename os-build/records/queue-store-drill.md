# Failure drill — `crates/queue-store`

What breaks first when its inputs stop arriving, written from
`crates/queue-store/src/lib.rs` on `main`, 2026-11-02. Another agent
can run this without a spec: each step names the call, the expected
observation, and why the code produces it.

Machine rule: single-crate checks only —
`cargo test -p queue-store -j1`. No workspace build, no emulator.

## The inputs

1. New job envelopes (`submit`).
2. Claim attempts (`claim` / `renew_claim`).
3. Result envelopes (`put_result`).
4. Backend answers (`get`, `hset`, `zadd`, …).

## Drill 1 — no new envelopes arrive

```
submit one job, note its id, then never submit again.
call open_job_ids() 100 times.
```

Expected: every call returns the same id. **Nothing ages out**: there
is no TTL on the job hash, the envelope, or the index member
(`lib.rs:385-401`). The crate has no "stale job" concept. First
visible consequence: an ever-growing `trioindex` and SQLite file if
the process runs long enough.

## Drill 2 — the backend stops accepting writes

```
use a backend whose set_body/hset are no-ops (InMemory cannot fail;
SqliteStore::set_body ignores the SQL error at lib.rs:302).
submit an envelope with id "drill-1".
call open_job_ids().
```

Expected: `submit` returns `("drill-1", true)`, then the id **never
appears** in `open_job_ids()`: the index member was added but the job
hash has no `status=open` field (or the reverse), and the filter at
`lib.rs:410-414` drops it. First break: "submitted but invisible".
No error is reported anywhere.

## Drill 3 — the claim store stops

```
submit job "drill-2".
make set_nx_ex always return false.
claim("drill-2", "worker-a", 60) -> false.
```

Expected: the worker treats the job as owned by someone else
(`agent-runtime/src/lib.rs:78-80`) and skips it forever. The job stays
`open`. No timeout, no error, no takeover path in this crate.

## Drill 4 — a worker dies holding the lease

```
claim("drill-3", "worker-a", 1)
sleep 2 seconds
claim("drill-3", "worker-b", 60) -> true
worker-a (still alive) calls finish("drill-3", "done", "late")
```

Expected: worker-b wins the second claim because the NX key expired
(`lib.rs:229-240`, `419-430`). Worker-a's `finish` still succeeds: it
writes `status=done` with no owner or status check
(`lib.rs:442-448`). First break: **two workers can believe they own the
job**, and the late one can overwrite the record.

## Drill 5 — result writes stop arriving

```
submit job "drill-4"; claim it; never call put_result.
call get_result("drill-4") -> None
```

Expected: `None` is also the answer for "not finished yet"
(`lib.rs:415-418`), so a polling agent cannot tell "lost write" from
"still running". The agent's idempotency check is result presence
(`agent-runtime/src/lib.rs:74-76`), so a lost result means it will
generate again on a later pass — a re-bill risk, not a crash.

## Drill 6 — the SQLite file cannot be opened

```
SqliteStore::open("/no/such/dir/store.db")
```

Expected: a `rusqlite::Error` is returned from `open`
(`lib.rs:274-287`). This is the only backend failure that reaches the
caller before any job is filed. Everything after open is silent.

## Drill 7 — the clock moves backward

```
insert a claim with lease 60 at t.
set the system clock back 1 hour.
claim the same job again.
```

Expected: `live()` drops a key only when `now > expiry`
(`lib.rs:200-212`), so a backward jump makes the lease look live for
longer and the second claim is refused until real time catches up. The
index order also stops matching wall-clock creation order. No warning
is emitted.

## What does not break

- Reading a missing job: `job_fields` returns an empty map
  (`lib.rs:403-405`), `job_envelope`/`get_result` return `None`
  (`lib.rs:406-409`, `415-418`). This is the crate's honest empty
  state.
- A duplicate `submit`: returns `created=false` and leaves the first
  envelope in place (`lib.rs:386-389`). Idempotence is the one
  failure path that is deliberate.
- Releasing a claim that does not exist: `delete` is a no-op
  (`lib.rs:221-228`).

## Drill verdict rule

A run passes only if every "Expected" above is what was observed.
A different answer is a finding, not a drill failure: name the call,
the observed value, and the line range that disagrees.
