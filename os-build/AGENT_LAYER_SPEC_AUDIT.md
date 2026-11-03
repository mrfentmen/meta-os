# Layer 5 audit — the spec against the code (Bond, 2026-11-03)

Read: `os-build/AGENT_LAYER_SPEC.md`, then the header and exports of each file
named below. Nothing was executed. This is a map of what exists, not a proof
that it works.

Labels: **CODE-INSPECTED** (file read), **UNPROVEN** (code exists, no drill log
read), **DRAFT** (entry is a placeholder by design), **UNIMPLEMENTED** (no code
found for that promise).

| § | Promise | Code | Label |
|---|---|---|---|
| 1 | an agent has identity, lane, capabilities, budget, owner | `agents/registry.json` | CODE-INSPECTED |
| 3 | registry, one entry per agent | `registry.json`, `registry_validate.mjs`, `loadRegistry`/`validateEntry` in `runtime.mjs` | CODE-INSPECTED — 16 live entries with real programs, 7 drafts with **no command at all** (a placeholder is now a validation error) |
| 4 | watchman wakes a named agent with the job in hand | `agents/watchman.mjs` (polls a jobs dir, writes a heartbeat through `watchdog.mjs`) | CODE-INSPECTED |
| 4 | a failure is retried once, then named | `watchman.mjs` retry path: second spawn with the baton, then `retry: "exhausted"` plus an alarm | CODE-INSPECTED — 7 watchman tests (retry and refusal) pass |
| 4 | a person can hand over work | `agents/submit.mjs`, `iso/apps/agent-status/meta-ask.py` (`meta-ask --list`) | CODE-INSPECTED — 11 meta-ask tests pass; doctor FAILs if the binary is absent |
| 4 | a person can halt one agent | `stop/<name>.STOP`, checked by the watchman before the spawn; paused jobs resume by name | CODE-INSPECTED — 3 stop/resume tests pass, the hold survives a restart |
| 5 | a finished run can order its next job | `proposeJob` in `agents/jobs.mjs`, wired into the watchman; one hop, echo and limit refused | CODE-INSPECTED — 5 propose tests, and the `self-tasking` drill |
| 4 | timer sweep as backup | `node agents/watchman.mjs --once` drains the board once and exits | CODE-INSPECTED — the command exists; no unit in the image schedules it |
| 4 | who watches the watchman | `agents/watchdog.mjs` (`check`, `supervise`, restart budget) | UNPROVEN — the mechanism has tests, no cadence ran it before `oc2-health.timer` |
| 5 | baton pass, continuation never restart | `agents/baton.mjs`, `agents/continue.mjs` | CODE-INSPECTED |
| 6 | spawn and kill are real | `agents/runtime.mjs` header: real spawn/kill, STOP file, ledger | CODE-INSPECTED, **UNPROVEN** — no spawn/kill drill log was read here |
| 7 | bus-shaped messaging, named rooms | `agents/room1.mjs`, `agents/bridge.mjs` | PARTIAL — files exist; only `room1.mjs` was skimmed |
| 8 | per-agent memory with a size cap, append-only | `agents/memory.mjs`, wired into `spawnAgent`: allowlisted records only, cap checked before the process starts, spawn/stop/exit lines written, ledger appends with no rewrite call | CODE-INSPECTED — 16 tests, no drill |
| 9 | budgets: actions, calls, spend, wall clock; no self-raise | `preflightBudget` in `runtime.mjs`, `agents/clock.mjs`, `budget` fields in the registry | CODE-INSPECTED |
| 10 | watch targets, wake only on change | `runtime.mjs` watch path, `watchman.mjs` | CODE-INSPECTED |
| 10 | speak only on change | `agents/notify.mjs`: alarm dedupe by key over a 15-minute window, quiet notes always land, three sinks | CODE-INSPECTED — 10 tests |
| 11 | append-only JSONL receipt per run | `Ledger` in `runtime.mjs`, `ledger.jsonl` per run | CODE-INSPECTED |
| 12 | crash contained to its run, baton kept | `reconcile()` in `watchman.mjs`, `agents/deadends.mjs` | CODE-INSPECTED |
| 13 | capability allowlist, labelled simulation only | `agents/grants.mjs`, `agents/tools.mjs` | CODE-INSPECTED |
| 14 | a drill per section before it counts | `agents/drills.mjs` exists | **UNPROVEN** — no drill output was produced for this audit |

## What this means for 1.0

The layer is further along than "design only": spawn, kill, budgets, baton,
receipts, the watchman and now memory caps all have real code. The sweep has a
command (`--once`) but nothing schedules it, and the image has no such unit —
so no agent wakes on a clock yet.

The registry no longer lists the crew (rowan, hana, milo, buffy, bond, pax):
they are people working on the project, not processes. What remains is 16 live
agents with real programs and 7 drafts that carry no command, so nothing can
spawn them by accident.

## Not verified here

- No drill was run; no ledger line, heartbeat or receipt was inspected.
- `bridge.mjs`, `tools.mjs` and `grants.mjs` were not read past their headers.
- The kernel-side L5 path (§2) is Rowan's and stays unstarted.

## Where a hosted loop writes

A hosted loop keeps its state out of the checkout, because an install runs the code from a
read-only payload. `METAOS_STATE` names the root (default `~/.local/state/metaos`);
`musica-studio` writes `musica/session-<stamp>/` beneath it, the Science Lab duties write
`science-lab/<agent>-<stamp>.json`. Both accept `--check`, which proves they can read their
inputs and write their receipts without spending a run.
