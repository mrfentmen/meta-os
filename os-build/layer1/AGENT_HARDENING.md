# Agent runtime hardening — A1 failure-injection report

Round 8, section A1. Scope: `agents/runtime.mjs` (spawn/kill/budget/STOP/ledger) and
`agents/watchman.mjs` (job intake). Pack: `tests/agents-hardening.test.mjs`.

    node --test tests/agents-hardening.test.mjs     → 7 pass, 0 fail
    node --test tests/agents-*.test.mjs             → 19 pass, 0 fail

Every case below is a real break, not a mock: the runtime spawns actual child processes and the
ledger is read off disk.

## What held (asserted, no change made)

| Case | Failure injected | What survived |
|---|---|---|
| A1.2 | `SIGTERM` mid-write of a 12 MB file | exactly one `stop-request`, one `exit`, and an `exit.stopped` reason — the run is *marked*, so a restart can tell "did not finish by itself" from "crashed" |
| A1.3 | `killAgent` called twice | one `stop-request`; the second call is a no-op, so the ledger cannot claim two stops for one run |
| A1.4 | `STOP` written after the child exited | no stop record. The poll interval is cleared on `done`, so a late STOP cannot manufacture a stop for a run that completed |
| A1.5 | 1 ms budget racing a ~5 ms exit | exactly one `exit`; the budget timer is cleared by `done`, so the race does not double-record |
| A1.6 | `budget.maxWallMs` of `-5`, then `0` | both refused at registry load; absent/null still means "no cap", which is the runtime's own default |
| A1.7 | a `.job.json` truncated mid-write | not claimed, not spawned, no crash; once completed, the job runs exactly once and the id lands in `watchman-state.json` |

## What broke — and is now fixed

**1. A torn ledger line made the entire run unreadable.** `Ledger.read()` mapped `JSON.parse`
over every line, so one append interrupted by a crash threw for the whole file: the records
*before* the torn line were lost too. In an audit trail, that is the opposite of what an
append-only log is for.

**2. Appending after a torn line fused the next record onto it.** The torn line has no trailing
newline, so the following `add()` produced `{"ts":…,"event":"exit"{"ts":…}` — one unparseable
line. The record written *after* the crash was lost as well, which turned a one-line tear into
two missing records.

Fix, in `agents/runtime.mjs`: `add()` separates with a newline when the file does not end in
one; `read()` skips a line it cannot parse and keeps the rest. Neither repairs nor reorders
anything — the page says so because "we recovered it" and "we kept what was whole" are different
claims.

## What still needs a fix

Two of the three items this report first listed were reachable only after a crash and were
permanent until A2 landed. Both are now fixed, in `agents/watchman.mjs`:

1. **Claim-before-spawn lost a job** — a claim with no bell is released by `reconcile()` and the
   job is picked up on the next poll.
2. **No run reaper** — a bell whose run has no `exit` record is marked `run-orphaned` and the job
   is re-queued to CONTINUE from that run's baton. Drill: `AGENT_RESTART_DRILL.md`.

Still open, and honestly Pax's to decide (runtime is his to edit):

3. **STOP is polled, not checkpointed.** The 100 ms interval is the runtime's only STOP surface.
   A child that never yields between checkpoints is killed up to 100 ms late with no record of
   where it was. The spec's "honoured at checkpoints" (S6) is satisfied in the weak sense only.
4. **Ledger growth is unbounded.** One JSONL per run is fine at this scale; nothing rotates or
   caps it, and the append-side one-byte read is O(1) only because the file is small.

## Evidence, on disk

- `tests/agents-hardening.test.mjs` — the seven cases, named A1.1–A1.7.
- `agents/runtime.mjs` — `Ledger.add` / `Ledger.read`, with the reason in a comment at each site.
- The run's own ledgers under the temp dirs the tests create (`agents-hardening-*`), each
  readable end to end after the injected failure.
