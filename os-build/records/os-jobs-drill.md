# `os-jobs` — failure drill: what breaks first

B033. Written from the code, runnable by another agent. The crate has
no transport, so "input stops arriving" means one of five things: the
store stops answering, the clock jumps, the keyring file disappears, a
job id is lost from the index, or a spec/claim key is lost while its
hash survives. The commands always return a `CmdOutcome`; nothing in
this list panics.

## The order things break in

1. **The store stops answering.** Every command returns exit 2 with
   `RELAY_ERROR: <command> failed (…)`; nothing is half-written by the
   crate itself, because each command maps the error before it invents
   state (post 1414-1460, claim 1816-1857, list 1499-1507, sweep
   2183-2191). `job_get` is the exception: a read failure is swallowed
   as `(None, "")` (1042-1047), so `show` says "no such job" rather
   than "store down". **First misleading message:** `show` on a store
   outage looks like a missing job.
2. **The keyring file disappears after a post.** The job hash, spec,
   and index are already written; `post` then fails with
   `ERROR: cannot read secret file`, exit 2 (1462-1467). The queue now
   holds an open, unsigned job. Nothing retries the signature.
   **First state drift.**
3. **The spec key is lost.** `job_get` returns `(Some(hash), "")`
   (1049-1056); `show` prints `--- spec ---` with an empty body
   (1645-1647). Unsigned jobs still claim and complete. A signed job
   now verifies `BAD`, because the v2 payload includes the spec
   (623-643, 1199-1245) — so a lost spec turns every later claim into
   a loud refusal (exit 1) until the spec is restored.
4. **The index zset is lost or truncated.** `list` prints `NO_JOBS`
   and `sweep` prints `SWEEP_CLEAN` (1499-1516, 2183-2191), while
   `show <id>` and `claim <id>` still work: they read the hash
   directly. **First blind spot:** the queue is fully usable by id and
   completely invisible to the board.
5. **The claim mutex expires while the hash still says `claimed`.**
   This is self-healing: `claim_or_requeue` sees the missing mutex and
   reopens the job (1169-1187); `requeue` refuses while the mutex is
   present and accepts after it is gone (2101-2115); `sweep` reopens
   every such job and announces `REQUEUE:` (2197-2213).
6. **The clock jumps forward.** Every claim's TTL is in the past at
   once: `sweep` requeues the whole board in one pass, `verify` reports
   `EXPIRED` for every signed job with an `expires_at`, and `heartbeat`
   silently renews because its `SET XX` fails and its `SET NX` succeeds
   (1252-1283). **First storm:** one sweep can reopen every job and
   emit one `REQUEUE:` per job.
7. **A job hash is lost while its id stays in the index.** `list`
   skips it silently (`hgetall` empty → `continue`, 1518-1526), `sweep`
   skips it (2196-2200), and `show` says no such job. **First silent
   loss:** no command reports the dangling index member.
8. **A non-numeric `attempts` or `max_attempts` is written by hand.**
   Rust treats `attempts` as 0 and an unparseable `max_attempts` as
   unlimited (2135-2172); the requeue proceeds. Python's `int()` would
   raise here (`os/jobs.py:855-861`) — this is a deliberate divergence
   (G10).
9. **Nothing consumes the announcements.** There is no transport, so
   `JobQueue::announcements` grows for the life of the queue
   (958, 1156-1168). **First resource break in a long run:** memory,
   not correctness.

## Drill A — store outage (5 minutes)

1. Read `crates/os-jobs/tests/error_paths.rs`; the `FaultStore` already
   fails one operation at a time.
2. Run `cargo test -p os-jobs --test error_paths` (single crate, `-j1`
   if the machine is loaded). PASS = all tests green, including
   `post_fails_when_the_sequence_counter_fails`,
   `claim_reports_a_mutex_write_failure`,
   `sweep_reports_an_index_read_failure`, `job_get_swallows_a_store_failure`.
3. Then write one temporary test that sets `Fault::Hgetall` and calls
   `show("1")` on an existing job: observe exit 2 with
   `ERROR: no such job: 1` (the misleading message in item 1). Record
   the observation; do not change the code in this drill.

## Drill B — lost index (5 minutes)

1. Post two jobs, then `store_set_raw("muse-bus:tjobindex", "", None)`
   is not enough (a string, not a zset); instead construct a fresh
   `FakeStore` and post again to see the healthy board, then use a
   store wrapper whose `zrange` returns `Ok(vec![])`.
2. Expected: `list` → `NO_JOBS`; `show("1")` → the job; `claim("1")`
   → success. PASS = the board is blind while by-id work still works.

## Drill C — keyring loss after post (5 minutes)

1. Post with a real temp keyring file, then delete the file.
2. Run `claim("1", "", 1800, Some(path))` → exit 2,
   `ERROR: cannot read secret file`.
3. Run `job_get("1")` → the job exists, unsigned. PASS = the job is
   there and nothing retries the signature; record it as state drift.

## Drill D — clock jump (3 minutes)

1. Post, claim, then `clock.advance(1801)` and call `sweep("")`.
2. Expected: `REQUEUED 1`, status `open`, `attempts` incremented.
3. Advance a signed job past `expires_at` and call `verify` → `EXPIRED`
   with exit 1. PASS = both transitions, no panic.

## What a green drill means

A green drill means the failure paths return the documented codes and
messages and leave no invented state. It does **not** mean the queue is
production-ready: there is still no store transport (G1) and no CLI
(G3), and an announcement sink that is never drained (item 9).
