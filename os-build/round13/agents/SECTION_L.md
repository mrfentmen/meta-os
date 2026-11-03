# Section L — Baton-pass proofs (R13-276..300)

Run:

```
node --test tests/agents-baton.test.mjs tests/agents-runtime.test.mjs \
  tests/agents-watchman.test.mjs tests/agents-restart.test.mjs tests/agents-gym.test.mjs
```

Result: **21 tests, 21 pass, 0 fail, 1,309 ms.** Transcript committed at
`os-build/round13/agents/baton-tests.txt`.

**25 / 25 addressed: 4 proven by a named passing test, 21 gap records.** The gaps are not
"untested behaviour" in the abstract — they are specific handoffs the list names that have no
fixture, no driver, and therefore nothing that could produce a before/after tree diff.

## What actually proved a baton pass

The four `A2.x` tests are the baton mechanism, and each one is a distinct failure the naive
version gets wrong:

| test | what it proves | which tasks it covers |
|---|---|---|
| `A2.1 a run that died mid-flight is marked and resumed from its baton` | a dead run is resumed, not restarted from zero | R13-276, R13-281 |
| `A2.2 a claim that was never spawned is released and retried` | a claim with no process behind it does not block the job forever | R13-282 |
| `A2.3 a completed job is never spawned again by a fresh watchman` | completion survives a new watcher — the duplicated-work failure | R13-283, R13-284 |
| `A2.4 a finished run whose result file was lost is not re-run` | a missing result is not read as "never ran" | R13-285 |

Plus the runtime tests that make the mechanism meaningful: `a claimed job is never spawned
twice`, `a job on the board wakes the named agent, briefed, and leaves a result`, and `the
graft: a lesson one agent teaches rides into the next agent's brief`.

## What is a gap, and why

The list names 25 handoffs across five loops — aegis, nervus, handsfree, imperium, cadence —
at specific steps (at step 2, at step 3, at step 4, at step 5), and asks for a **before/after
tree diff summary** as the proof that no file change was duplicated.

- The baton tests run in temporary directories with synthetic agents. They prove the handoff
  logic; they write no tree, so they produce no diff summary.
- No per-loop fixture exists: there is no aegis job that runs to step 2, no nervus job that
  runs to step 3, and so on. Naming a step does not create one.
- The loop drivers the tasks name (`gym.mjs` for imperium, `hosted.mjs` for cadence,
  `judge.mjs` for nervus) exist, but running them means spawning the real crew and writing
  shared ledger state — the same reason R13-271 was filed `NOT_EXERCISED` in Section K.

A restart disguised as a pass fails the task, per the list. Four of these are passes by test
name and assertion; twenty-one would be restarts dressed up, so they are recorded as gaps.

| tasks | loop named | status | why |
|---|---|---|---|
| R13-276, R13-281 | aegis | **OBSERVED** (A2.1) | resume-from-baton proven; the loop label is the list's, the test is generic |
| R13-282 | nervus | **OBSERVED** (A2.2) | claim released and retried |
| R13-283, R13-284 | handsfree / imperium | **OBSERVED** (A2.3) | completed job not re-spawned by a fresh watcher |
| R13-285 | cadence | **OBSERVED** (A2.4) | lost result file does not cause a re-run |
| R13-277, R13-278, R13-279, R13-280 | nervus, handsfree, imperium, cadence | GAP | no fixture that runs to the named step |
| R13-286 .. R13-300 | mixed | GAP | same: a step number is not a fixture, and no tree diff was produced |

## What this section cannot claim

- That a handoff at step 2 of the aegis loop is safe. The generic resume path is proven; the
  loop-specific step is not.
- That zero duplicated file changes is measured. The tests assert on ledger records and run
  state, not on a filesystem diff. The list's own proof standard (tree diff summary) was not
  met by any of the 25.
- That 21 gaps are a tooling problem rather than a product one. There is no aegis job that
  reaches step 2 in this tree; that is a fact about the tree.

## Per-ID records for R13-287..299

These thirteen handoffs were previously counted inside the 21 gap records
without a file each. They now have one. Every one is a gap for the same
measurable reason: no per-loop fixture reaches the named step, so nothing runs,
nothing writes a tree, and no before/after diff can exist.

| task | proof | loop | step | driver | state | record |
|---|---|---|---|---|---|---|
| R13-287 | 12 | nervus | 5 | `agents/watchdog.mjs` | GAP | `os-build/round13/agents/baton/R13-287.md` |
| R13-288 | 13 | handsfree | 2 | `agents/clock.mjs` | GAP | `os-build/round13/agents/baton/R13-288.md` |
| R13-289 | 14 | imperium | 3 | `agents/runtime.mjs` | GAP | `os-build/round13/agents/baton/R13-289.md` |
| R13-290 | 15 | cadence | 4 | `agents/watchman.mjs` | GAP | `os-build/round13/agents/baton/R13-290.md` |
| R13-291 | 16 | aegis | 5 | `agents/baton.mjs` | GAP | `os-build/round13/agents/baton/R13-291.md` |
| R13-292 | 17 | nervus | 2 | `agents/gym.mjs` | GAP | `os-build/round13/agents/baton/R13-292.md` |
| R13-293 | 18 | handsfree | 3 | `agents/hosted.mjs` | GAP | `os-build/round13/agents/baton/R13-293.md` |
| R13-294 | 19 | imperium | 4 | `agents/bridge.mjs` | GAP | `os-build/round13/agents/baton/R13-294.md` |
| R13-295 | 20 | cadence | 5 | `agents/judge.mjs` | GAP | `os-build/round13/agents/baton/R13-295.md` |
| R13-296 | 21 | aegis | 2 | `agents/lessons.mjs` | GAP | `os-build/round13/agents/baton/R13-296.md` |
| R13-297 | 22 | nervus | 3 | `agents/queue.mjs` | GAP | `os-build/round13/agents/baton/R13-297.md` |
| R13-298 | 23 | handsfree | 4 | `agents/room1.mjs` | GAP | `os-build/round13/agents/baton/R13-298.md` |
| R13-299 | 24 | imperium | 5 | `agents/safe-write.mjs` | GAP | `os-build/round13/agents/baton/R13-299.md` |

The remaining IDs in this section are covered by the rows above and by the
four passing `A2.x` tests named at the top of this file.

