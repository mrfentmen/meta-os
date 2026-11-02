# queue-core — failure drill (B117)

Written from the code. A drill another agent can run against
`MemoryBackend`, no emulator and no network. Expected lines are what
the code does today; a different result is a finding.

## Scenario: the consumer stops arriving

1. **Submit keeps succeeding.** `submit` has no liveness check
   (`lib.rs:398-418`). File 100 envelopes; the index zset gains 100
   members (`lib.rs:417`).
2. **First break: the queue grows silently.** `open_job_ids` returns
   all 100 (`lib.rs:428-437`). `MemoryBackend` has no size cap
   (`lib.rs:278-381`), so process memory grows with the queue. There is
   no log line and no error — a queue with no consumer looks healthy
   from inside the crate.
3. **Optional claim.** Claim one job (`lib.rs:444-462`). It leaves
   `open_job_ids`: the scan keeps only `status == "open"`
   (`lib.rs:432-435`), and the status is now `claimed`.
4. **Second break: a claimed job with no finisher is invisible.**
   After step 3, `open_job_ids` no longer lists the job, `get_result`
   is `None`, and `job_fields` still says `claimed`. The crate offers
   no query that lists claimed jobs, so a dead worker's job is neither
   open nor done.
5. **Lease expiry is lazy.** The claim key expires only when something
   reads it: `set_nx_ex` calls `live` (`lib.rs:322-331`), and `live`
   removes an expired key (`lib.rs:289-299`). A new `claim` after the
   lease succeeds. If nobody claims, the expired key sits until the
   next access; there is no sweeper.
6. **Result never written.** `get_result` stays `None`
   (`lib.rs:439-441`). The HTTP layer above would have to answer
   pending/unknown; the core cannot distinguish them, because that is
   `job_fields` inspection (`lib.rs:420-422`).
7. **Clock before epoch.** `now_secs` returns 0 (`lib.rs:273-275`);
   every lease is measured from 0 and reads as expired on first access.

## Drill steps (expected output)

```text
cargo test -p queue-core                       # 12 unit tests pass
# in a scratch integration test, using MemoryBackend + JobStore:
submit 100 jobs at now=1000
assert open_job_ids().len() == 100             # step 2
claim(job0, "w", 60, 1001) == true
assert open_job_ids().len() == 99              # step 3-4
assert job_fields(job0)["status"] == "claimed"
assert get_result(job0) == None                # step 6
claim(job0, "w2", 60, 2000) == true            # step 5, after lease
```

The two surprises to watch for are step 4 (claimed jobs disappear from
the only scan) and step 2 (no cap, no signal). Both are ported Python
behaviour (`server/queue/trio_store.py:413-419`), not new bugs.
