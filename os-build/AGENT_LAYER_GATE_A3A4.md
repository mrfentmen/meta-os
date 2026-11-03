# AGENT LAYER GATE — A3 (spec vs C1–C22) + A4 (scoreboard rows)

Gate: Milo, 2026-11-02. Spec gated: `os-build/AGENT_LAYER_SPEC.md`
(Pax, 2026-11-02, on main 63db13c). Questions gated:
`MILO_OS_BUILDOUT.md` §C, C1–C22. Tasks: `os-build/AGENT_LAYER_TASKS.md`
A3/A4. Runtime checked: `agents/runtime.mjs` + `agents/registry.json`
+ `tests/agents-runtime.test.mjs` on main 63db13c.

Verdict words: ANSWERED = the spec settles the question at design
level. PARTIAL = the spec touches it but leaves a named hole.
OPEN = the spec does not answer it; the follow-up task is named.
Nothing here is a boot or kernel verdict: the in-kernel road (§2)
is explicitly not started, and no claim in this file depends on it.

## A3 — every C answered or named open

| C | Question (MILO_OS_BUILDOUT §C) | Spec answer | Verdict | Evidence / follow-up |
|---|---|---|---|---|
| C1 | Agent process model v1: what an agent is (task? service? Lobster host?) — options + recommendation | §1 defines an agent (nick, lane, capabilities, budget, memory, owner; a process, not a window/chat). §2 recommends host runtime v1 now, in-kernel road later. Lobster-host option is NOT weighed as an option. | PARTIAL | Recommendation given; the options comparison (task vs service vs Lobster host) is not written. Follow-up: one paragraph weighing the three, or drop the Lobster-host option explicitly. |
| C2 | Spawn model: who may start an agent, with what limits | §6: only the runtime spawns, from registry entries; budget written into the job record BEFORE start; spawn returns a run id. | ANSWERED | Implemented slice 1: `agents/runtime.mjs`, tests 6/6 (reproduced this gate). |
| C3 | Kill model: who may stop one; what the agent sees first | §6: graceful (stop signal/file + grace window to write the baton record) then hard; killers: owner, runtime (budget/STOP), boss. Agent sees the stop request + reason in its job record first, never a silent death. | ANSWERED | Implemented slice 1: graceful-then-hard kill + STOP file, tests 6/6 (reproduced this gate). |
| C4 | Message model between agents (bus-shaped; rooms; ordering) | §7: named rooms, plain-text lines, ordering by arrival, no delivery promises beyond the ledger; messages are part of the agent's record; private data never crosses unopened rooms. | ANSWERED | Design level only: no messaging code or test in slice 1. Proof owed: §14 names no messaging drill (see C14). |
| C5 | Memory model: what an agent may persist, where, how much | §8: job records, baton state, ledger only, by default; under the agent's own directory; per-agent size cap (registry field); append-only, no rewriting own history. | ANSWERED | Design level only. Note: `agents/registry.json` on main carries no memory-cap field yet — the cap is spec'd, not yet a registry field. |
| C6 | Budget model: calls/time caps per agent (mirror the queue's) | §9: max actions, max calls, max spend, max wall-clock; hitting any one stops the run, writes the receipt, reports UP (quiet note / full alarm by size). No agent may raise its own budget; money movement always needs the boss. | ANSWERED | Implemented in part slice 1: actions/wall-clock caps + STOP tested 6/6. Spend/call caps are spec'd, not yet exercised by a test. |
| C7 | Permission model: filesystem, network, dispatch — default deny | §13: an agent may only call endpoints its manifest lists; simulated endpoints must carry their marker; announce-before-send holds for anything in the boss's name. §6 adds an environment allowlist at spawn. | PARTIAL | No explicit default-deny statement for filesystem, network, or dispatch, and no enforcement in slice 1 (registry `capabilities` are free-form strings; the runtime does not check them). Follow-up: a default-deny paragraph + a capability-check test, or name it as a B-slice task. |
| C8 | Failure model: agent crash isolation proof obligations | §12: crash contained to its run; runtime marks it failed, preserves ledger + baton, applies the failure matrix (retry once with the record / hand the baton on / escalate). Crasher-isolation rule stated. | PARTIAL | Model stated; proof not yet run. Tasks B3 (failure injection) and B4 (restart semantics) are assigned to Buffy and unstarted; §14 names no failure drill. |
| C9 | Lobster binding review vs Buffy's LOBSTER_BINDING.md: gaps | No section reviews a Lobster binding. The spec never cites Lobster as a binding, and no `LOBSTER_BINDING.md` file exists on main (only `lobster/README.md` + scripts, e.g. `lobster/memory.lobster`, `lobster/budget.lobster`). | OPEN | Follow-up: either write the binding review (what the Lobster scripts prove, what they do not) or record that the host runtime supersedes the Lobster binding for v1 and retire C9 explicitly. Do not claim it answered. |
| C10 | Spec the five syscalls an agent host needs beyond the F1 table | §2 says the manifest/ledger/budget contracts move down unchanged when the kernel grows spawn/kill, but it does NOT enumerate five syscalls, and does not cite the F1 table. | OPEN | Owned and named: TASKS F1 (spec the agent syscalls beyond the F1 table; Milo C10 feeds it; Rowan, post-demo). No claims until booted. |
| C11–C20 | One test-obligation spec per C1–C10 (what proof would close it, on which layer, run by whom) | §14 names proof per spec section, not per C, and names no layer or runner: spawn/kill by drill log, wake by hands-free drill, baton by zero-duplication pass, budgets by a cap-hit run, watch by change-wakes / quiet-hour-does-not. | PARTIAL | Covered by §14: C12/C13 (spawn/kill drill), C16 (budget drill). NOT covered by §14: C11 (identity/process-model proof), C14 (messaging proof), C15 (memory/cap proof), C17 (permission proof), C18 (failure proof), C19 (Lobster proof), C20 (registry proof — though registry loading is tested 6/6, §14 does not name it). Follow-up: extend §14 with one line per missing C, naming layer + runner. |
| C21 | Agent registry format (name, lane, caps, owner) — draft | §3: one JSON entry per agent — name, lane, command, capabilities, budget, owner, wake sources. Draft format: `agents/registry.json`. | ANSWERED | Draft exists on main with all 10 entries (6 crew + 4 loops). Defect: §3 cites a schema in `agents/README.md`, but that file does NOT exist on main (`agents/` holds only `registry.json` + `runtime.mjs`). Fix: write the README or drop the citation. |
| C22 | Crew-as-agents mapping: Rowan/Hana/Buffy/Pax entries drafted | §3 lists the crew as the first entries: Rowan (kernel), Hana (UI/surfaces), Milo (gates/records), Buffy (services), Buffy 2 (verification), Pax (dispatch/merge), plus resident loops (imperium-patrol, musica-studio, officina-faber, watch). | ANSWERED | `agents/registry.json` on main matches §3 (10 entries; lanes/owners/capabilities as spec'd). All slice-1 commands are `["true"]` placeholders — the registry is a draft, not live loops, and this gate does not claim otherwise. |

A3 tally, counting C11–C20 as one block: ANSWERED 7
(C2–C6, C21, C22), PARTIAL 4 (C1, C7, C8, C11–C20 block),
OPEN 2 (C9, C10). The spec is gateable as a design: no C is
silently dropped — every gap above is named with its follow-up
owner (C7: Milo/B-slice; C9: Milo; C10: F1/Rowan post-demo;
C11–C20 gaps: §14 extension).

## A4 — scoreboard rows per spec section (spec §14)

Rule applied from §14 and TASKS A4: until a section's named drill
exists, the section is UNIMPLEMENTED in scoreboard language, even
where unit tests pass. A unit test is not the §14 drill. This keeps
the scoreboard from rounding up.

| Spec § | Section | Proof obligation (§14) | Evidence today (main 63db13c) | Status |
|---|---|---|---|---|
| §1 | What an agent is | None named in §14 (gap, see C11) | Spec text only | UNIMPLEMENTED |
| §2 | Where it sits (L5, host v1 / in-kernel road) | None named in §14 | Host runtime slice 1 exists; in-kernel road not started | UNIMPLEMENTED (road: NOT STARTED) |
| §3 | Agent record (registry) | None named in §14 (gap, see C20) | `agents/registry.json` draft, 10 entries; registry load/reject tests pass (part of 6/6) | UNIMPLEMENTED (draft + tests, no §14 drill) |
| §4 | Wake layer (watchman, timer sweep, watchdog, fleet) | Hands-free drill: dark machine lights up and starts work unprompted | No watchman code; tasks C1–C3 assigned to Pax, unstarted | UNIMPLEMENTED |
| §5 | Baton pass | Zero-duplication pass | No baton record format yet; task D1 assigned to Milo, unstarted | UNIMPLEMENTED |
| §6 | Spawn and kill | Drill log | Real spawn/kill + graceful-then-hard + STOP file, tests 6/6 reproduced this gate — but no §14 drill log artifact exists | UNIMPLEMENTED (tested, drill log owed) |
| §7 | Messaging | None named in §14 (gap, see C14) | Spec text only; no messaging code | UNIMPLEMENTED |
| §8 | Memory | None named in §14 (gap, see C15) | Spec text only; registry carries no memory-cap field yet | UNIMPLEMENTED |
| §9 | Budgets and stops | A run hits its cap and stops; receipt shows why | Wall-clock cap + STOP tested 6/6; no cap-hit drill run/receipt artifact | UNIMPLEMENTED (tested, drill owed) |
| §10 | Watch capability | One change wakes; one quiet hour does not | File-change watch tested 6/6 (change wakes; quiet stays quiet in-test) — but no quiet-hour drill artifact | UNIMPLEMENTED (tested, drill owed) |
| §11 | Receipts (ledger) | Ledger lines back every claim (the discipline, §11 itself) | JSONL ledger written by slice 1 (spawn test asserts brief + ledger) | UNIMPLEMENTED (ledger exists, no §14 drill) |
| §12 | Failure model | None named in §14 (gap, see C18) | Model text only; B3/B4 assigned to Buffy, unstarted | UNIMPLEMENTED |
| §13 | Safety rails | None named in §14 (gap, see C17) | Spec text only; no capability enforcement in slice 1 | UNIMPLEMENTED |
| §14 | Proof obligations (this table's rule) | Self-referential: the drills above | This file is the A4 row set; drills themselves do not exist yet | UNIMPLEMENTED |
| §15 | What exists today (honest baseline) | Baseline, not a build section | Baseline text matches main 63db13c as checked this gate (registry, runtime, tests 6/6) | BASELINE (no proof obligation) |

A4 note for the main scoreboard (`os-build/SCOREBOARD.md` L5 row):
that row still reads DRAFT from the pre-agent-layer process model.
This file does not edit it — the L5 row update is Pax's merge-time
step, so this branch cannot collide with concurrent scoreboard
edits. When Pax merges this branch, the L5 row should move from
DRAFT to: "SPEC'D + slice 1 tested (6/6); all §14 drills owed;
C9/C10 open; §3 README citation defect open."

## What this gate did NOT do

- No kernel verdict, no boot verdict, no Mac check. In-kernel L5
  is road, not claim.
- No re-gate of Pax's B1/B2 beyond reproducing the 6/6 tests in a
  scratch worktree on this VM; the tests are Pax's artifact, and
  this file cites them as such.
- No change to the spec, the tasks file, the registry, or the
  runtime. Pax merges; Milo gates.
