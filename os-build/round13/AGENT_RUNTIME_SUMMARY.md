# Round 13 — agent runtime summary (Sections K–O)

| section | state | counts | evidence |
|---|---|---|---|
| agent runtime: supervisor | **COMPLETE** | 25 / 25; 19 observed, 2 refused, 1 not exercised, 3 gaps; **5 findings** | `os-build/round13/agents/SECTION_K.md` |
| baton-pass proofs | **COMPLETE** | 25 / 25; 4 proven by passing tests, **21 gaps** (no per-loop fixture, no tree diff) | `os-build/round13/agents/SECTION_L.md` |
| agent runtime: STOP/budget | **COMPLETE** | 25 / 25; 12 observed, 9 observed-gap, 4 gaps | `os-build/round13/agents/SECTION_M.md` |
| agent runtime: death/recovery | **COMPLETE** | 25 / 25; 21 observed, 2 observed-gap, 2 gaps | `os-build/round13/agents/SECTION_N.md` |
| chaos over the loops | **COMPLETE** | 25 / 25; 11 observed, 9 observed-gap, 5 gaps | `os-build/round13/agents/SECTION_O.md` |

## What the drills measured

- Baton: 21/21 agent tests pass; 4 handoffs proven, 21 cases have no per-loop fixture and are recorded as gaps.
- STOP: the runtime polls every 100 ms, every runnable loop finishes in under 40 ms, so the poll cannot win. `agents/hosted.mjs`'s pre-spawn gate is the only arm that halts these loops; both arms are recorded per row.
- Budget: every cap below the measured cost fired, wrote a receipt, killed the run and left no orphan.
- Death: `checkBeat()` detects a killed watchman in ~250–350 ms. **Nothing restarts it.** `agents/watchdog.mjs` alarms once and exits; every restart in Section N is a manual respawn by the drill.
- `patrol.py --once --max-checks 1` never terminates; it is the only loop that gives the STOP poll a live process, and it is a finding, not a pass.
- A missing working directory kills the process that called `spawnAgent` (no `'error'` listener on `spawn()`). Proved in a child probe, exit 7.
