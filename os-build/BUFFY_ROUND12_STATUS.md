# Buffy — Round 12 status

Branch `buffy/round12`, merged with main. Task list: `BUFFY_TASKS_ROUND12.md` (44).

| section | state | counts | evidence |
|---|---|---|---|
| A — the 14 | **DONE** | 14 / 14 | `r12/SECTION_A.md` |
| B — Aegis live fire | **DONE** | 6 / 6 | `aegis/HISTORY_SCAN.md`, `LIVENESS.md`, `OPSEC_R12.md`, `r12/AEGIS_CYCLE.json` |
| C — loops hardened | **DONE** | 6 / 6 | `r12/IMPERIUM_BATON.json`, `BATON_PROOF.json`, `LOOPS_DRILL.json` |
| D — services second ring | **PARTIAL** | restart 3 / 38 | `r12/SECOND_RING.md`, `RESTART_PROOF.json`, `RESTART_GAP.md` |
| E — Nervus + Hands-Free | **DONE** | 5 / 5 | `r12/VOICE_SEAM.md`, `r12/HANDSFREE_CADENCE.json` |
| F — proof and closeout | **DONE** | 4 / 4 | `r12/PROOF_LEDGER.md`, `r12/FINISH.md`, `r12/PAX_BLOCKERS_R12.md` |

## Measured on this branch tip

- Lane suite: **119 tests, 119 pass, 0 fail** (19 files).
- Native services: **86 programs, 86 RUNS, 0 FAILS, 3,804 assertions**.
- History scan: **1,881 commits**, 14 category hits, no values recorded.
- Liveness: **169 targets — 168 LIVE, 0 DEAD, 1 UNREACHABLE** (clipraiders.com).
- OPSEC: **20 pass, 0 fail, 112 screenshots UNCHECKED** (no OCR).
- Aegis cycle: sweep **23 manifests / 108 refs / 0 findings**, KEV 0, ledger batch written.
- FP drill: **3 clean packages, 0 findings**.
- Baton: Imperium **1 dispatch** after resume; Cadence **1 stage-1 + 1 continuation**, restart **83 ms**.
- STOP: early pass **8/8 halted**; late pass 5 halted, 2 finished, 1 exited before the poll; 0 orphans.
- Budget: **20 ms** cap, receipt written, registry cap unchanged at 120,000 ms.
- Restart: **echo, heartbeat, mcp-host PASS**; 35 services have no runnable main.

## Not claimed

- No kernel compile or boot; no QEMU log.
- No model, no voice transcription, no real dispatch.
- No restart for the 35 svc_entry/library services; no line-by-line service contract read.
