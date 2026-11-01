# watchdog — missed heartbeats and who decides what happens next

Status: **WRITTEN** (not COMPILED — no Goose toolchain on this Mac; see
`services/BUILD.md`). Layer 4, service 7.

## The one thing this service does not do

It does not restart anything. It reports, and the supervisor's restart policy
(B-L1-21) decides. A watchdog that also restarts is a second controller over the
same process, with a second opinion, and no way to tell which one won.

## What it holds

```goose
struct Watch {
    handle: i64,        // opaque supervisor handle; 0 = free slot
    period_ms: i64,     // how often a beat is expected
    deadline_ms: i64,   // absolute uptime the next beat is due by
    grace_ms: i64,      // extra time before lateness counts
    miss_allow: i64,    // consecutive misses tolerated
    misses: i64,        // consecutive misses so far
    reported: bool,     // already escalated; a death is reported once
}
```

32 entries, static, no allocation — the same capacity as the supervisor's table,
because a watchdog that could watch more services than exist is capacity nobody
paid for and nobody checks.

## Why the deadline is an absolute value, not a duration

"Has it been 5 s?" needs a start point. Recomputing one on every check silently
extends the deadline whenever the check runs late, so a service that is hanging
gets declared healthy by the very loop that was supposed to catch it. A beat
pushes the stored absolute deadline forward; a check only compares.

## Misses are counted, not just detected

One late beat is a scheduling hiccup. Restarting on the first miss turns a busy
machine into a restart storm. `wd_check_one` counts whole elapsed periods, so a
check that runs rarely still reports the true lateness rather than one miss per
check, and returns:

| State | Meaning |
|---|---|
| `WD_FINE` | not due yet |
| `WD_SILENT` | late, still inside `miss_allow` |
| `WD_DEAD` | past the allowance — **this check is the escalation** |
| `WD_STILL_DEAD` | already escalated; still dead, nothing new to do |

The split between `WD_DEAD` and `WD_STILL_DEAD` is the "escalate once" rule made
visible in the return value. Without it `wd_next_dead` handed back the same
dead service on every scan — an escalation loop with extra steps — and the
caller could not tell a new death from one it had already restarted. Found while
writing the B-L1-53 test.

A clock that moved backwards is treated as fine and the deadline is pushed
forward from now: a wall-clock adjustment (B-L1-37) must not report every service
at once.

## The calls

- `wd_watch(handle, period_ms, grace_ms, miss_allow, now_ms)` — start watching.
  Refuses a second watch on the same handle rather than silently re-arming.
- `wd_beat(handle, now_ms)` — clears the miss count, because the question is "how
  long has it been silent", not "how often has it ever been late".
- `wd_next_dead(now_ms)` — at most **one** handle per call. Escalating a batch
  would restart a whole layer because one slow check collected them, and the log
  would not say which failed first.
- `wd_count(now_ms)` — healthy / dead / total missed beats, the numbers a health
  line quotes (B-L1-124).

## Deliberately absent

- No kill call; no restart call. Both belong to the supervisor.
- No per-service threads. One loop over 32 entries is cheaper than 32 wakeups,
  and Goose threads share nothing, so a per-service watchdog could not see the
  table it was watching.
- No history. The audit service (B-L1-41) owns that, and two histories disagree.

## Verification

Every form here is checked against `goose-mcp@1.1.0`: `struct` and `struct`
literals (`reference#32`), `T[..k]` static arrays, `while`/`if` chains, `T&`
reference parameters, multi-value returns. `E_INVAL` / `E_NOTFOUND` / `E_STATE` /
`E_NOROOM` are the names `common/err/err.goose` actually declares — an earlier
draft of this file used `E_NOENT`, which does not exist there, and that is the
kind of mistake a template will not catch.

Not compiled, not run.
