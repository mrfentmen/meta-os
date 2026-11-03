# AGENT LAYER GATE — D1 (baton record format vs the spec)

Gate: Milo, 2026-11-02. Spec gated: `os-build/AGENT_LAYER_SPEC.md`
§5 (the baton pass), with §6 (spawn/kill), §12 (failure model),
§13 (safety rails) and §14 (proof obligations) where they touch the
baton. Format gated: `agents/baton.mjs` + `agents/watchman.mjs`
(continuation path) + `tests/agents-baton.test.mjs`, on main
e942f01. Task: `os-build/AGENT_LAYER_TASKS.md` D1 — "Milo: gate it
against the spec." This gate follows Pax's 04:27 sequencing: D1 is
the call after C7, before the C9 plan-doc review and the C7
capability-check test.

Verdict words: PASS = the spec claim holds in the code and the
test. PARTIAL = the code covers the claim but leaves a named hole.
OPEN = the spec's proof standard is not met; the follow-up is named.
Nothing here is a kernel or boot verdict, and nothing here changes
the spec, the tasks file, the registry, or the runtime. Pax merges;
Milo gates.

## What was reproduced

In this worktree, on main e942f01, unchanged code:

- `node --test tests/agents-baton.test.mjs` — 2/2 pass:
  "baton record round-trips" and "the pass: agent B continues from
  agent A's baton, briefed by the watchman". These are Pax's tests,
  cited as such, not Milo's.
- The pass test asserts what it asserts and no more: the
  continuation brief contains "Continuation of run", A's next step
  ("finish the west wall"), B's own orders ("mind the gate"), and
  the ledger carries a `baton-pass` event. All four reproduced.

## Gate table — spec §5 claims vs the implementation

| # | Spec claim | Implementation | Verdict | Evidence / follow-up |
|---|---|---|---|---|
| 1 | Baton record carries state, artifacts, next step (§5) | `writeBaton` writes `baton.json` with exactly those three fields (defaults `""` / `[]` / `""`) plus a `ts` timestamp; `readBaton` returns it, or `null` when absent. | PASS | Round-trip test covers state + next step; artifacts covered by the pass test (`['wall.txt']`). |
| 2 | Workers deposit progress AS THEY GO (§5) | `writeBaton` overwrites the single `baton.json` in the run dir on every call: latest write only, no history, no version, no append. No mid-run deposit is demonstrated — the test writer writes once, at the end. | PARTIAL | The format supports repeated writes, but "as they go" history is lost. Follow-up: either keep a deposit history (append-only, §8's own rule) or state explicitly that latest-only is the design. |
| 3 | On reassignment the watchman composes a continuation brief from the record (§5) | `watchman.mjs` reads `runs/<continuesFrom>/baton.json`, builds orders with `continuationOrders` (header + state + artifacts + next step + B's own orders), logs `baton-pass`. | PASS | Pass test reproduces all four asserted strings (see above). |
| 4 | Continuation, never restart (§5) | True when a baton exists. When it does NOT exist, the watchman logs `baton-missing` and spawns B with its original orders only — a fresh start, silently. | PARTIAL | The missing-baton path contradicts "never restart" for exactly the case where continuation matters most. Follow-up: apply the §12 failure matrix here (retry once with the record / hand on / escalate) instead of silently starting fresh, or name silent-fresh-start as the designed behaviour. |
| 5 | Proof standard: the job completes with zero duplicated file changes (§5, §14) | The pass test's two programs are disjoint by construction (A writes `baton.json`, B reads `brief.json` and writes `done.txt`): no shared mutable file exists to duplicate, and no assertion checks that B skips work A already did. | OPEN | In §14's language §5 is still UNIMPLEMENTED: the drill owed is a pass over a shared file where B's brief names A's completed step and the test asserts that step is not redone. D3's host drill passing is not that drill. |
| 6 | Graceful kill gives the agent a window to write its baton record (§6) | `runtime.mjs` `killAgent` sends SIGTERM, waits 800 ms, then SIGKILL, and logs `stop-request`. Nothing checks that a baton was written in the window, and no test kills an agent and then continues from its baton. | OPEN | Unproven, not disproven. Follow-up: a kill-then-continue test (SIGTERM -> baton written -> watchman continues B from it), or name it as a B-slice drill. |
| 7 | Artifacts named in the baton are the work so far (§5) | No existence or type check anywhere: a baton may list files that do not exist, and the brief will name them anyway. Worse, a non-array `artifacts` value crashes the brief builder: `continuationOrders` with `artifacts: 'wall.txt'` throws `TypeError: baton.artifacts.join is not a function` (reproduced this gate, scratch node run against the unchanged module). | PARTIAL | Follow-up: validate `artifacts` as an array in `writeBaton` (reject or coerce), and either check artifact existence at brief time or label listed artifacts as claimed, not verified. |
| 8 | A baton record identifies its own run | `baton.json` carries no run id, no agent name, no author — only state, artifacts, next step, ts. Identity comes solely from the directory path (`runs/<runId>/baton.json`). | PARTIAL | A copied baton loses provenance. Follow-up: stamp `runId` (and agent) into the record at write time; cheap, and it makes the `baton-pass` ledger line auditable without the path. |
| 9 | The baton does not widen permissions (C7 default-deny, this job's 04:18 gate) | The baton carries no capabilities, no endpoints, no budget: only state, artifacts, next step. The continuation agent runs under its own registry entry, so a baton cannot grant what the registry does not. | PASS | Design level. The C7 capability-check test (the B-slice, after C9 per Pax sequencing) is still the enforcement proof; this gate does not claim it. |
| 10 | Cross-program pass (TASKS D3 stretch line) | Not built, not tested: the pass test runs two node programs under one watchman on one machine. | OPEN (stretch) | Explicitly not claimed. Cross-program (Muse -> Freebuff shape) stays the stretch line from TASKS D3. |

## Tally

PASS 3 (#1, #3, #9). PARTIAL 4 (#2, #4, #7, #8).
OPEN 3 (#5 zero-duplication drill, #6 kill-then-continue drill,
#10 cross-program stretch). The baton format is gateable as a
design and as a host drill: the record fields, the watchman brief,
and the permission boundary all hold. The §14 proof standard does
not yet hold — §5 stays UNIMPLEMENTED in scoreboard language until
the zero-duplication drill (#5) exists, and the missing-baton and
artifact-validation holes (#4, #7) should be closed before any
merge that calls the baton pass proven.

## What this gate did NOT do

- No change to `agents/baton.mjs`, `agents/watchman.mjs`,
  `agents/runtime.mjs`, the spec, or the tasks file. The
  string-artifacts crash (#7) was reproduced in a scratch node run
  against the unchanged module; no fix is committed here — the fix
  belongs to the runtime lane (Pax/Buffy), gated after.
- No kernel verdict, no boot verdict, no Mac check.
- No re-gate of B1/B2 runtime tests beyond the baton file; the
  2/2 result above is the baton test file only.
- Scoreboard note for Pax's merge-time step (not edited here, to
  avoid colliding with concurrent scoreboard edits): when this
  branch merges, the agent-layer §5 row should read "format +
  host drill 2/2; §14 zero-duplication drill owed; missing-baton
  path silently restarts; artifact validation owed."
