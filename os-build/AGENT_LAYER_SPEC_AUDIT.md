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
| 3 | registry, one entry per agent | `registry.json`, `registry_validate.mjs`, `loadRegistry`/`validateEntry` in `runtime.mjs` | CODE-INSPECTED — but the crew entries carry `command: ["true"]`, `draft: true` and a `draftReason`, so they are **DRAFT**, not agents that can work |
| 4 | watchman wakes a named agent with the job in hand | `agents/watchman.mjs` (polls a jobs dir, writes a heartbeat through `watchdog.mjs`) | CODE-INSPECTED |
| 4 | timer sweep as backup | `node agents/watchman.mjs --once` drains the board once and exits | CODE-INSPECTED — the command exists; no unit in the image schedules it |
| 4 | who watches the watchman | `agents/watchdog.mjs` (`check`, `supervise`, restart budget) | UNPROVEN — the mechanism has tests, no cadence ran it before `oc2-health.timer` |
| 5 | baton pass, continuation never restart | `agents/baton.mjs`, `agents/continue.mjs` | CODE-INSPECTED |
| 6 | spawn and kill are real | `agents/runtime.mjs` header: real spawn/kill, STOP file, ledger | CODE-INSPECTED, **UNPROVEN** — no spawn/kill drill log was read here |
| 7 | bus-shaped messaging, named rooms | `agents/room1.mjs`, `agents/bridge.mjs` | PARTIAL — files exist; only `room1.mjs` was skimmed |
| 8 | per-agent memory with a size cap, append-only | none found. `lessons.mjs` and `gym.mjs` are learning loops, not agent memory | **UNIMPLEMENTED** |
| 9 | budgets: actions, calls, spend, wall clock; no self-raise | `preflightBudget` in `runtime.mjs`, `agents/clock.mjs`, `budget` fields in the registry | CODE-INSPECTED |
| 10 | watch targets, wake only on change | `runtime.mjs` watch path, `watchman.mjs` | CODE-INSPECTED |
| 11 | append-only JSONL receipt per run | `Ledger` in `runtime.mjs`, `ledger.jsonl` per run | CODE-INSPECTED |
| 12 | crash contained to its run, baton kept | `reconcile()` in `watchman.mjs`, `agents/deadends.mjs` | CODE-INSPECTED |
| 13 | capability allowlist, labelled simulation only | `agents/grants.mjs`, `agents/tools.mjs` | CODE-INSPECTED |
| 14 | a drill per section before it counts | `agents/drills.mjs` exists | **UNPROVEN** — no drill output was produced for this audit |

## What this means for 1.0

The layer is further along than "design only": spawn, kill, budgets, baton,
receipts and the watchman all have real code. One promise has no code at all —
per-agent memory caps. The sweep has a command (`--once`) but nothing
schedules it, and the image has no such unit.

The crew entries being `draft` matters: the registry validates and lists them,
but a draft entry runs `true`, so a spawn of "rowan" succeeds and does nothing.
Any claim that the crew runs from this registry would be wrong.

## Not verified here

- No drill was run; no ledger line, heartbeat or receipt was inspected.
- `bridge.mjs`, `tools.mjs` and `grants.mjs` were not read past their headers.
- The kernel-side L5 path (§2) is Rowan's and stays unstarted.
