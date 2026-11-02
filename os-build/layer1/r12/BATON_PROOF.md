# Cadence baton pass and watchman death — R12-022 / R12-025

Run at 2026-11-02T15:05:16.146Z. **PASS**

| item | value |
|---|---|
| first run | `worker-mvze4riw` |
| kill | SIGKILL to process group 1443 (watchman + worker) |
| heartbeat age at check | 300 ms, fresh=false |
| alarm raised | **dead** — ALARM watchman heartbeat lost: last beat 0.3s ago (limit 0.1s, last 2026-11-02T15:05:15.610Z) |
| orphan records | 1 |
| baton-pass records | 1 |
| restart to result | 83 ms |
| `stage-1` lines | 1 |
| `continuation` lines | 1 |
| final exit | 0 |

Across the two runs the artifact has one stage-1 line and one continuation line: the handoff
continued the work, it did not redo it. The dead run is marked `run-orphaned`; the new run is
a different id.

## Limits

- Host processes, not the kernel. No scheduler, no address space.
- The alarm is `agents/watchdog.mjs` on a 150 ms threshold; the production default is larger.
- Only the Cadence loop is exercised here. Imperium's proof is `IMPERIUM_BATON.json`.
