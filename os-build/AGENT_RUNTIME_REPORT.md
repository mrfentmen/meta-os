# Agent runtime — failure injection and restart (B3, B4)

Branch `buffy/agent-runtime-harden`, cut from `main` at `63db13c`, 2026-11-02.
Lane: `agents/runtime.mjs` (Pax's host runtime v1) + `tests/agents-runtime-failures.test.mjs`.
Spec: `os-build/AGENT_LAYER_SPEC.md` §9 (budgets), §11 (receipts), §12 (failure model).

**Status: DONE for B3 and B4, with two defects found and fixed.** Evidence is the test file
below, not this page.

```console
$ node --test tests/agents-runtime-failures.test.mjs
ℹ tests 11
ℹ pass 11
ℹ fail 0
$ node --test tests/agents-runtime.test.mjs      # Pax's original suite, unchanged
ℹ tests 6
ℹ pass 6
ℹ fail 0
```

## B3 — what was injected, and what happened

| Injection | What the runtime did | Verdict |
|---|---|---|
| Kill at ~150 ms into a writer agent's loop | Work file stops at a whole line; ledger gains `stop-request` then `exit` with `stopped: "test-mid-write"` | Holds. A kill loses work, not the receipt. |
| Ledger with a torn **last** line (the append in flight when the runtime died) | `Ledger.read()` returns every complete event and drops the tail | Holds — this is the crash case, and the history survives it. |
| Ledger with a torn **middle** line (a rewritten file) | `read()` throws `ledger: torn line 2` | Holds. Append-only is the point; a spliced file is refused, not silently truncated. |
| Registry `command: ["node", 42]` | Refused at load: `command must be strings` | **Prevention added** (see F3). |
| Registry `watch: [{type:"url", …}]` | Refused at load: `bad watch target` | **Prevention added** (see F3). |
| Registry command that does not exist (`ENOENT`) | Run marked `spawn-error`, `await done` settles with `{code:null, error:"…ENOENT…"}` | **Defect F1, fixed.** |
| Two `killAgent` calls racing | One `stop-request`, one `exit`, first reason wins | Holds. The `stopped` guard is a real mutex for this path. |
| `killAgent` after the run already exited | **Wrote a `stop-request` for a finished run** | **Defect F2, fixed.** |

### F1 — a spawn that never becomes a process took the runtime down

`spawnAgent` listened for `exit` and nothing else. A `command[0]` that does not exist (or a
`cwd` that is not there) makes `spawn` emit `error` and **never** `exit`. With no listener that
is an uncaught exception in the runtime's own process — and every other agent's parent lives
there, so one bad registry entry kills the crew. The opposite mistake was also available: a
listener that only logs leaves `handle.done` pending forever, and a supervisor awaiting the run
hangs with no receipt.

Fixed by handling both: `spawn-error` is appended to the run's ledger and `done` resolves with
`{code:null, signal:null, error}`. The brief is still written before the attempt, so the failed
run has its orders on disk and nothing to hand off.

### F2 — a stop for a run that had already finished

`killAgent` guarded on `handle.stopped` but not on whether the child had exited. The budget
timer and the STOP poll run on their own schedules, so a stop landing a few milliseconds after a
clean exit wrote `stop-request` into the ledger of a finished run. That is a receipt claiming the
runtime stopped something it never touched — exactly the kind of line that makes the rest of the
ledger arguable.

Fixed with `handle.exited`, set in both terminal handlers, and an early return in `killAgent`.
A stop that loses the race now adds nothing; the exit line already says how the run ended.

### F3 — two entries that were shaped right and named nothing

Neither threw where it happened:

- `command` was checked for length only, so `["node", 42]` passed load and threw inside
  `spawn()` — at spawn time, in a live process.
- `watch` was not validated at all. `pollWatch` throws `unsupported target type`, and it does so
  **inside a `setInterval`** at the watch cadence: one typo kills the watcher minutes later, far
  from the entry that caused it.

Both are now refused by `loadRegistry`, with the reason and the agent name. The rule behind
these: a registry is read once, at load, by something that can still refuse to start; validating
there costs nothing and moves every failure to the place a human can see it.

## B4 — restart semantics

A runtime that dies takes no children with it. Its runs keep running, and their ledgers stop
mid-story with no `exit` line — so after a restart every one of those runs reads as *still
going* to anything that scans `runs/`. Nothing marked them, and nothing could.

`reconcileRuns(root)` (also `node agents/runtime.mjs reconcile`) walks `runs/` and, for each run
whose last event is not terminal, appends:

```json
{"ts":"…","run":"left-behind-1","event":"orphaned","reason":"runtime-died","lastEvent":"action"}
```

What it does **not** do, deliberately:

- **It does not touch `brief.json`.** The brief is the agent's orders and what a baton hand-off
  reads; a recovery pass that rewrote it would be the runtime editing the agent's instructions.
  The test asserts the brief is byte-identical after reconciliation.
- **It does not repair a torn middle line.** That run is returned under `unreadable` with the
  line number and the CLI exits 2. A rewritten history is reported, never fixed: the only honest
  thing a recovery pass can say about it is "I cannot read this".
- **It is not a restart of the agent.** Marking a run orphaned is a statement about the record,
  not a retry. §12's "retry once with the record / hand the baton on" is still the watchman's job
  (task D2), and the record it needs is now there.
- **It is idempotent.** A second restart leaves marked runs alone; the test asserts one mark, not
  two.

## What this does not prove

- **No child was orphaned by a real runtime death.** The B4 tests build the on-disk state a death
  leaves (run dir, ledger, no exit line) rather than killing the runtime process; the runtime has
  no self-restart, so there is nothing to kill and restart *within* a test. What is proven is the
  reconciliation of that state, not the death itself.
- **`orphaned` is not in §11's list of ledger events.** §11 names spawn, wake, action, call,
  spend, stop, kill and baton writes. `orphaned` (and `spawn-error`) are additions this work
  needed; they should be added to §11 by whoever owns the spec (Pax), or renamed to fit it.
- **Budget is wall-clock only.** §9 also names max actions, max calls and max spend. The registry
  carries those numbers (`maxActions`, `maxCalls`, `maxSpendUsd` on `imperium-patrol`) and the
  runtime does not enforce them — no counter is incremented anywhere. That is a gap, not a
  failure: nothing claims otherwise, but a run with `maxActions: 8` is only bounded by its
  wall clock today.
- **The kill is POSIX-signal based.** `SIGTERM` then `SIGKILL` after a grace window; a child that
  ignores signals and holds a lock is not exercised, and Windows is not exercised at all.

## Reproduce

```sh
node --test tests/agents-runtime-failures.test.mjs
node --test tests/agents-runtime.test.mjs
node agents/runtime.mjs reconcile        # on a tree with runs/ in it
```

## Hand-off

B3 and B4 are done on `buffy/agent-runtime-harden`; the merge is Pax's. Two follow-ups belong to
someone else and are named here so they are not rediscovered: §11 should list `orphaned` and
`spawn-error`, and the action/call/spend budgets need an enforcement point inside the run (the
ledger already has the line to count).
