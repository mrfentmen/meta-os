# W5 — The Gym, first slice (Milo, BUILD_WAVE 2026-11-02)

Agents train before real work. First drill: one agent, three tasks,
scores in the ledger, the record riding the agent's registry entry.

## What landed

- `agents/gym.mjs` — drill runner against the real agent runtime
  (`agents/runtime.mjs`, no mocks). Three tasks, each scored 0/1:
  1. `registry-entry` — the entry loads with a name, a command, a budget.
  2. `spawn-clean-exit` — a real spawn exits 0 and writes its brief.
  3. `ledger-complete` — the run ledger reads back spawn then exit.
  `node agents/gym.mjs drill <name> [--record]`; `--record` writes the
  gym record onto that agent's registry entry and appends the scores to
  `agents/gym-ledger.jsonl` (append-only, one event per task + a total).
  Record updates keep registry.json's existing style (1-space indent,
  no trailing newline, non-ASCII escaped) so only the drilled entry
  changes.
- `tests/agents-gym.test.mjs` — 5 tests, all pass, including a failing
  agent losing only the spawn task (scores 1/0/1) and a record update
  touching only the drilled entry.
- First drill, agent `watch` (the capability demo agent): 3/3.
  Scores in `agents/gym-ledger.jsonl` (gym-task-score x3 + gym-total);
  the record rides `watch`'s entry in `agents/registry.json`.

## Honest gaps (not invented, not hidden)

- One agent drilled, not the crew. The drill exercises runtime
  mechanics; it does not prove real agent work — every registry command
  here is still the `true` placeholder, so a 3/3 says "the runtime
  works", not "the agent is good at its job".
- Drill runs spawn into a temp dir, so the spawn's own run ledger is
  not committed; the committed score trail is the gym ledger + the
  registry record.
- Save Points / Forge / Party XP stay design notes (IDEAS_BUILD_LIST),
  per the wave doc, until a later Gym slice lands them.

## Verification

- `node --test tests/agents-gym.test.mjs tests/agents-runtime.test.mjs`:
  12 pass, 0 fail.
- `node agents/gym.mjs drill watch --record`: 3/3, recorded.
- `node agents/runtime.mjs list` still lists all 12 agents clean.
- Diff vs main f215a1c: 4 files, pure addition except the gym record
  on `watch`'s registry entry. No excluded files touched, no mocks.
