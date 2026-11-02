# `crates/agent-runtime` — failure drill (B105)

What breaks first when the crate's inputs stop arriving, written from
the code so another agent can run it. This crate has no process, no
timer and no loop: "inputs stop arriving" means the **caller stops
calling `serve_job`**, or a dependency it was given stops answering.

Machine rule: single crate only, `cargo test -p agent-runtime -j1`.
No workspace build, no QEMU.

## Drill 0 — the crate's own tests (baseline)

```sh
cargo test -p agent-runtime -j1
```

Expected: the three existing unit tests (`lib.rs:391-470`) plus the
tests in `tests/error_paths.rs`, `tests/edge_cases.rs`,
`tests/gap_close.rs` pass. This proves the crate compiles and the
branches below are reachable. If this is red, stop: nothing else in the
drill means anything.

## Drill 1 — no jobs arrive

There is no poll loop in the crate (gap G4). If the caller stops
calling `serve_job`, the crate does nothing and reports nothing.

```rust
// tests can show this without a clock:
let store = InMemoryStore::default();
let jobs = JobStore::new(store, "trio");
assert_eq!(jobs.open_job_ids(), Vec::<String>::new());
```

First thing that "breaks" is not the crate: it is the caller's
assumption that something is running. There is no heartbeat, no log
line, no idle metric — silence is the failure mode.

## Drill 2 — generation outlives the lease (the real first break)

This is the first genuine failure when inputs keep arriving but the
generator stops answering: the claim expires while the generator is
still working.

1. Build an `Agent` with `lease: 1`.
2. Make `Generator::generate` block for 2 seconds, then return a valid
   assessment.
3. While it blocks, build a second `Agent` over the same store and call
   `serve_job(jid)`.

Expected from the code:

- The second agent's `claim` succeeds after the first lease expires
  (`queue-store/src/lib.rs:432-435`); it does **not** return `Lost`.
- Both agents then call `put_result` for the same jid
  (`lib.rs:152`); the later write wins, with no compare-and-set.
- The first agent's `finish` and the second's both run; the `note`
  reflects whichever finished last (`lib.rs:169-170`).

Test form: `tests/edge_cases.rs` proves the claim half deterministically
by pre-claiming a job (`out_of_order_serve_loses_the_claim`). A
timing-based two-agent drill needs a real sleep and belongs in a
single-crate `-j1` run, not in the default suite.

## Drill 3 — the store stops answering

If `StoreBackend::get`/`set_nx_ex` return their failure shape (the
trait has no `Result`; `None`/`false` is the only signal,
`queue-store/src/lib.rs:172-184`):

- `get_result` -> `None`, so idempotency looks clean.
- `claim` -> `false`, so `serve_job` returns `Outcome::Lost`
  (`lib.rs:78-80`).
- No result is written and no error is surfaced.

First break: a dead store is indistinguishable from a lost race. The
drill is to run `serve_job` against a backend whose `set_nx_ex` always
returns `false` and confirm the outcome is `Lost`, not `Failed`.
`tests/error_paths.rs::claim_race_lost` covers the same return path with
a real competing claim.

## Drill 4 — the envelope stops being readable

Cut the envelope key and leave the claim free:

- `JobStore::job_envelope` -> `None` (`queue-store/src/lib.rs:424-427`).
- `serve_claimed` writes R1 and returns `Failed` (`lib.rs:92-98`).
- The result is a failed envelope with `assessment: null`.

Run: `tests/error_paths.rs::missing_envelope_refuses`.

## Drill 5 — the result already exists

Submit the job, call `serve_job` once, then call it again with a
`Generator` that panics if called.

Expected: `Outcome::Skipped`, exactly one result, zero generator calls
(`lib.rs:73-77`). Run:
`tests/edge_cases.rs::duplicate_serve_skips_before_generating`.

## Drill 6 — relay endpoint down

No effect today: the hook is not wired (gap G3). If it is wired later,
the drill is: set a dead `TRIO_RELAY_URL`, finish a job, assert the
result is still written and the job is still `done`. Python's rule is
"logged and swallowed" (`trio_agent.py:118-119`); the Rust port must
not turn a relay error into a failed job. There is no Rust code to run
yet.

## What this drill does not cover

- A real Spark transport: the crate takes a `Generator`; the transport
  is the caller's.
- Upstash or SQLite: `queue-store` owns both.
- Panics inside `Generator`: Rust has no exception boundary here (gap
  G6); a panicking generator unwinds out of `serve_job`.
