# The Meta OS agent layer — agentic execution, enforced

An agent is not a model with tools. It is a loop that observes, chooses, acts, verifies, and
updates its plan — and the observation must bind the next choice. The runtime in
`agents/runtime.mjs` already spawns a bounded process, kills it on a wall-clock cap, honours
the STOP file, and writes an append-only ledger. That is a job runner. This document describes
the layer that makes the run *agentic*: a contract the run cannot skip, an inner loop that
takes one transition at a time, enforced grants, shared dead ends, lesson accounting, and a
bounded way to ask for another slice.

Everything below is in the tree and exercised by the checks in the last section.

## Pieces

| Piece | File | What it enforces |
|---|---|---|
| Run contract | `agents/contract.mjs` | observe → decide → act → verify ordering, evidence, and the finish gate |
| Inner loop | `agents/loop.mjs` | one transition at a time; a refusal leaves the contract resumable |
| Grants | `agents/grants.mjs` | path, command, network, spend, and wall permissions; narrowing only |
| Dead ends | `agents/deadends.mjs` | an approach that failed carries its evidence; silent retry is refused |
| Lesson accounting | `agents/learning.mjs` | every applied lesson is counted against the lesson that taught it |
| Bounded continuation | `agents/continue.mjs` | a run can ask to continue, but only within named limits |
| Relay hook | `agents/watchman.mjs` | queues a continuation job, claims the request exactly once |
| Judgment drills | `agents/drills.mjs` | refusals are tested, not assumed |

These sit on the existing primitives: `runtime.mjs` (spawn, budget, STOP, ledger),
`watchman.mjs` (job board and bells), `baton.mjs` (continuation without restart),
`lessons.mjs` (the Graft), `watchdog.mjs` (liveness), `judge.mjs` (inconclusive instead of a
coin flip), `safe-write.mjs` (short writes fail loudly), and `clock.mjs` (a backwards clock
does not become a budget).

## The run contract

A contract is JSON on disk in the run directory. It is the artifact the loop gates on, and
`validateContract()` can reject a tampered one.

```json
{
  "version": 1,
  "goal": "fix the flaky clipboard test",
  "done_condition": { "cmd": "python3 -m unittest tests.test_clipboard", "expect_exit": 0 },
  "max_steps": 50,
  "status": "open",
  "seq": 4,
  "steps": [
    {
      "id": "s1",
      "observation": { "id": "obs-1", "cmd": "python3 -m unittest tests.test_clipboard", "exit": 1, "tail": "FAIL on run 7 of 20" },
      "considered": [{ "action": "add a sleep", "why_not": "hides the race, does not close it" }],
      "chose": { "action": "add a barrier", "why": "obs-1 shows interleaving", "because": "obs-1" },
      "result": { "exit": 0, "ok": true, "evidence": "barrier added; 20/20 green", "closed_seq": 3 },
      "plan_revision": null,
      "lessons_applied": [],
      "opened_at": "2026-11-03T06:00:00.000Z",
      "closed_at": "2026-11-03T06:04:00.000Z"
    }
  ],
  "done_checks": [],
  "revisions": [],
  "stops": [],
  "reopens": [],
  "created_at": "2026-11-03T06:00:00.000Z",
  "updated_at": "2026-11-03T06:04:00.000Z"
}
```

The rules, in the order they bind:

1. **Observation first.** `recordObservation` opens a step; `recordDecision` on a step with
   no observation is refused (`no-open-step` / `observation-required`).
2. **A choice names what it rejected.** `considered` must contain at least one
   `{action, why_not}`. The chosen action cannot also appear as rejected
   (`contradictory-decision`).
3. **A choice cites the observation.** `chose.because` must equal this step's observation id
   (`obs-N`). An adjective is not a citation (`citation-required`).
4. **Evidence closes a step.** `recordResult` refuses an empty `evidence`. A failed result is
   a valid close: the next observation is the retry (`evidence-required`).
5. **Done means the check ran after the work.** `finish` requires a done check whose command
   is exactly the contract's, whose exit matches `expect_exit`, and whose `seq` is greater
   than the last step's `closed_seq`. Sequence numbers, not timestamps, prove the order — two
   events in the same millisecond cannot fake it (`done-not-run`, `done-command-mismatch`,
   `done-stale`, `done-failed`).
6. **A stopped run is resumable, but visibly.** `abandon()` records the reason and status.
   `reopen()` requires a reason and enough headroom under `max_steps`; both acts are appended
   to the contract (`stops`, `reopens`).
7. **A lesson cited by a decision is on that step.** `recordLessonApplied` attaches
   `{lesson, outcome}` to the step and refuses duplicates.

`canFinish()` returns `{ok, code, reason}` without throwing, so a caller can report why a run
is not done. `finish()` is the throwing gate. `saveContract`/`loadContract` validate on the
way in and out; a contract with a decision citing an observation that is not in its step fails
`assertContract` with `invalid-contract`.

## The inner loop

`runLoop` does not know how to call a model or a shell. The caller supplies the adapters, and
the loop records every transition before allowing the next one.

| Adapter | Called with | Must return |
|---|---|---|
| `observe` | `{contract}` | `{cmd, exit, tail}` |
| `decide` | `{contract, step, observation}` | `{considered: [...], chose: {action, why, because}}` |
| `act` | `{contract, step, chose, observation}` | `{exit, evidence, ok?}` |
| `checkDone` | `{contract}` | `{cmd, exit, tail}` — the command that actually ran |

```js
import { emptyContract } from "./agents/contract.mjs";
import { runLoop, shellCheck } from "./agents/loop.mjs";

const result = await runLoop({
  contract: emptyContract({
    goal: "make the clipboard test pass 20 runs",
    doneCondition: { cmd: "python3 -m unittest tests.test_clipboard" },
  }),
  checkDone: shellCheck({ cwd: process.cwd() }),
  observe: async () => ({ cmd: "python3 -m unittest tests.test_clipboard", exit: 1, tail: "FAIL on run 7" }),
  decide: async ({ observation }) => ({
    considered: [{ action: "add a sleep", why_not: "hides the race" }],
    chose: { action: "add a barrier", why: "obs-1 shows interleaving", because: observation.id },
  }),
  act: async () => ({ exit: 0, evidence: "barrier added; test passes 20/20" }),
  saveTo: "runs/contract.json",
});
```

What the loop guarantees:

- **The done gate runs only when no step is open.** A goal whose condition is already true
  finishes with zero invented steps. A check taken mid-step would necessarily be
  `step-open`, and recording it would make the real check stale.
- **The step cap blocks a new observation, never the closing of one already taken.** A run is
  never stopped between observing and acting, leaving a half-recorded step.
- **A thrown action is evidence.** It closes the step as failed with `action threw: ...`, and
  the next turn observes again. A loop that crashes leaves no reason on disk; this one does.
- **A bad adapter is a `blocked` result, not a crash.** An uncited decision leaves the
  observation on disk, so a human or a later run can resume from exactly there.
- **Deadlines stop before any work and record `deadline` in `stops`.** The clock is injectable
  for tests.

`resumeLoop(file, options)` loads the contract and continues it. `shellCheck()` runs the
contract's done command through `/bin/sh -c` (or `cmd.exe /c`) with a timeout that becomes exit
124. Only load contracts from trusted runs: the done command is executed.

## Grants

`capabilities` in the registry is a dispatch label. A grant set is a permission. It denies by
default, and composition can only narrow it.

```js
import { assertGranted, guardedExec, guardedWrite, normalizeGrants } from "./agents/grants.mjs";

const grants = normalizeGrants({
  write: ["runs/agent"],
  commands: [process.execPath],
  hosts: [{ host: "api.example.com", ports: [443] }],
  maxSpendUsd: 2,
  maxWallMs: 60000,
}, { root: process.cwd() });

guardedWrite(grants, "runs/agent/notes.txt", "ok\n", { root: process.cwd() });
guardedExec(grants, [process.execPath, "-e", "console.log('hi')"], { root: process.cwd() });
assertGranted(grants, { kind: "network", host: "api.example.com", port: 443 });
```

- **Paths** are resolved, and the nearest existing ancestor is realpath'd. A symlinked parent
  cannot smuggle a write outside the granted root; `..` is resolved before the check.
- **Commands** are matched by real path, not by name. `node` and `/usr/local/bin/node` are
  the same program; `/bin/sh` is not. Later argv entries may be empty strings.
- **Network** requires an explicit host and port. `*.example.com` matches subdomains, not the
  apex; a host without ports is refused rather than given a silent default.
- **Spend and wall** have no grant unless written. A zero-dollar request is allowed; any
  positive request without a cap is `spend-not-granted`.
- **Narrowing only.** `narrowGrants(parent, child)` throws `grant-widening` if the child names
  a path outside the parent, a different program, an uncovered host or port, or a larger cap.
  An omitted category inherits the parent.
- **The guarded tools are the enforcement point.** `guardedWrite`, `guardedAppend`, and
  `guardedExec` check before touching the filesystem or the process. A refusal leaves no
  partial file and no orphan command.

## Dead ends and lesson accounting

The crew should not pay twice for the same failed idea.

```js
import { assertFresh, recordDeadEnd } from "./agents/deadends.mjs";
import { recordApplied } from "./agents/learning.mjs";

recordDeadEnd("/var/lib/metaos/crew", {
  task: "fix the flaky clipboard test",
  approach: "add a sleep",
  why_failed: "the race moved, it did not close",
  evidence: "run 7 of 20 still failed with the sleep",
});

assertFresh("/var/lib/metaos/crew", {
  task: "fix the flaky clipboard test",
  approach: "add a sleep",
}); // throws known-dead-end

assertFresh("/var/lib/metaos/crew", {
  task: "fix the flaky clipboard test",
  approach: "add a sleep",
  override: "the race is now a different one",
}); // records the override and returns

recordApplied("/var/lib/metaos/crew", {
  agent: "milo",
  lesson: { ts: "2026-11-03T05:00:00.000Z" },
  outcome: "used",
  run: "milo-abc",
});
```

Dead ends are keyed by a case- and whitespace-insensitive task signature plus the normalized
approach. Recording the same dead end twice is a no-op, not a second lesson. Torn JSONL lines
are skipped and counted, never repaired and never allowed to erase the good records. The
`lesson-applied.jsonl` ledger joins the Graft's lessons to their use; `lessonBoard(root)` shows
a lesson with zero applications as untouched instead of assuming it helped. A contract step
also carries its own `lessons_applied` entries, so the run's account and the crew's ledger can
be compared.

## Bounded continuation

A run that stops mid-way has two honest choices: pass a baton, or ask to continue. The request
is a file in the run directory:

```json
{
  "outcome": "continue",
  "reason": "half the west wall is up",
  "next": "finish the west wall",
  "baton": { "stepIndex": 1, "state": "west wall half built", "artifacts": ["wall.txt"], "nextStep": "finish the west wall" },
  "requested_at": "2026-11-03T06:10:00.000Z"
}
```

`continueDecision()` refuses in this order: no request, STOP file, nonzero exit, cycle cap,
wall cap, cost cap. The defaults are `maxContinues = 4`; a job can carry a lower
`maxContinues`. The request is claimed by atomic rename, so two relays cannot both continue
the same run.

`watchman.mjs` reads the request after a clean exit, writes the next job
(`<job>~c<n>-<run>`), and only then archives the request. The job write is deterministic and
`writeIfChanged`, so a relay that crashes between writing the job and archiving the request
replays the same bytes instead of losing or duplicating the continuation. A refused request is
recorded as `continue-refused` with its reason, not silently dropped.

## Judgment drills

Plumbing tests prove an agent can be spawned. The drills prove the refusals:

```sh
node agents/drills.mjs
```

Eleven drills: an already-true goal, a decision before observation, an uncited decision, a
verified step that is not a finished run, a stale done check, an action that exits 0 while the
done condition still fails, a recorded dead end retried silently, a write outside a grant
(including through a symlink), a continue past its cap, a lesson that is counted, and a
tampered contract. The runner prints `PASS`/`FAIL` per drill and exits 1 if any fail.

## Checks

Run from `meta-os/`:

```sh
node --test tests/agents-agentic.test.mjs   # 22 focused cases
node agents/drills.mjs                      # 11/11 judgment drills
npm run test:agents                         # 158 existing agent-layer tests
```

The focused suite executes the contract, the loop, the grants (including a real spawned
process and a symlink escape), the dead-end and learning ledgers, the continue bounds, and a
real watchman continuation cycle. The drills are the same refusals in a human-readable run.

## Honest limits

- **The layer is a library, not a scheduler.** `runtime.spawnAgent` still spawns a command;
  it does not construct a contract for it. A worker opts in by using `runLoop`. The layer
  enforces shape, not judgment: `decide` and `act` are the caller's code.
- **Grants bind only where they are called.** `assertGranted` and the `guarded*` helpers are
  the enforcement point. A raw `fs.writeFileSync` or `child_process.spawn` bypasses them. A
  future tool dispatcher must route every tool through the guard; that dispatcher does not
  exist in this tree yet.
- **Continuation requires a clean exit.** A killed or signaled run is resumed through the
  baton, not through `continue.json`; continuing a failed run would turn a kill into a retry.
- **Dead ends are not consulted automatically.** `runLoop` does not call `assertFresh`; the
  caller must check an approach before acting on it. Making the loop do it would require the
  loop to understand what an "approach" is, which is the caller's domain.
- **Lesson accounting is two records.** A contract step's `lessons_applied` and the
  `lesson-applied.jsonl` ledger are written separately. A caller that records one and not the
  other has an incomplete account, and no code here can infer the missing one.
- **`shellCheck` executes a shell command from the contract.** The contract is trusted input.
  Do not load one from a run you would not execute.
