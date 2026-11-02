# Round 12 — program proof ledger (Bond's format)

Only commands that ran. A row with no command is not here.

| lane | command | result | evidence |
|---|---|---|---|
| Aegis OSV sweep 1 | `node aegis/run-sweep.mjs --direct` (direct API, Pax's written exception) | 23 manifests, 108 versioned refs, 2 batches, **0 findings** | `os-build/aegis/SWEEP.md` |
| Aegis KEV cross-check | `node aegis/run-kev.mjs` | **0 sweep findings** checked, 0 flagged; 7 non-sweep OSINT records excluded by name | `os-build/aegis/KEV.md`, `KEV.json` |
| Aegis second sweep + diff | `node aegis/run-sweep.mjs --direct` then `node aegis/sweep-diff.mjs` | 108 refs, 0 findings; diff 0 added / 0 removed / 7 unchanged (MECHANICS PROOF) | `os-build/aegis/SWEEP_DIFF.md` |
| Aegis OSINT | `node aegis/run-osint.mjs` | 4 domains; CT certs 0/2/0/8, names 0/2/0/5; **3 findings**; clipraiders.com does not resolve | `os-build/aegis/OSINT.md` |
| Aegis watch targets | `node aegis/run-sweep.mjs --watch` / `watch-targets.mjs` | **169 targets** (165 repos + 4 pages), all UNVERIFIED | `os-build/aegis/WATCH_REVIEW.md` |
| Imperium hosted loop | `python3 server/queue/hosted_imperium.py` via the real registry command | **PASS** — queue up, resident agent exit 0, dispatch HTTP **201** | `os-build/layer1/r12/IMPERIUM_RECEIPT.json` |
| Cadence hosted loop | `node agents/watchman.mjs --once` | exit 0, receipt filed | `os-build/layer1/r12/CADENCE_RECEIPT.json` |
| Userspace programs | nightly `cargo build` with `x86_64-unknown-none` | `hog` and `quitter` compile; neither is in `BINS`, nothing booted | `os-build/userspace/WIRING_PROPOSAL_R12.md` |
| Services native pass | `os-build/layer1/run_native.sh` | **86 programs, 86 RUNS, 0 FAILS, 5 built-not-run; 3,804 assertions passed** | `os-build/layer1/r12/SECOND_RING.md` |
| Hands-Free → Cadence | `node --test tests/handsfree-cadence.test.mjs` | one typed order → job → real watchman run → exit 0 → brief; latency recorded | `os-build/layer1/r12/HANDSFREE_CADENCE.json` |
| Nervus record shapes | `node --test tests/nervus-ledger-shape.test.mjs` | 5 operations validate; every ledger line `stub:true`, `result.source:STUB` | `tests/nervus-ledger-shape.test.mjs` |
| Lane test run | the 18-file command in `BUFFY_ROUND12_STATUS.md` | **110 tests, 110 pass, 0 fail** | `/tmp/r12-lane.log` (this run) |

## Not in this ledger

- No kernel compile or boot on this machine; no QEMU log was produced.
- No model run: Nervus is the STUB runner, and its receipt says so.
- No service restart: no host supervisor, nothing was killed and restarted.
- No voice: the transcription surface is unresolved (R12-040).

## Sections B–D additions

| lane | command | result | evidence |
|---|---|---|---|
| History scan | `node aegis/history-scan.mjs` | 1,881 commits, 14 category hits, counts only | `os-build/aegis/HISTORY_SCAN.md` |
| Finding receipts | `node aegis/findings-receipts.mjs` | 0 sweep findings, batch receipt | `os-build/aegis/FINDINGS_LEDGER.md` |
| Liveness | `node aegis/check-liveness.mjs` | 169 targets: 168 LIVE, 0 DEAD, 1 UNREACHABLE | `os-build/aegis/LIVENESS.md` |
| OPSEC | `node aegis/opsec-r12.mjs` | 20 pass, 0 fail, 112 screenshots unchecked | `os-build/aegis/OPSEC_R12.md` |
| Aegis cycle | `node aegis/cycle.mjs` via hosted runtime | sweep 23/108/0 → KEV 0 → ledger | `r12/AEGIS_CYCLE.json` |
| False-positive drill | `node aegis/fp-drill.mjs` | 3 clean packages, 0 findings | `r12/FALSE_POSITIVE_DRILL.json` |
| Imperium baton | `node r12/imperium-baton.mjs` | killed mid-run, resume exit 0, 1 dispatch | `r12/IMPERIUM_BATON.json` |
| Cadence baton + death | `node r12/baton-proof.mjs` | 1 stage-1, 1 continuation, restart 83 ms | `r12/BATON_PROOF.json` |
| STOP + budget | `node r12/loop-drills.mjs` (early and late) | early 5 ms: **8/8 halted**, 0 orphans; late 40 ms: 5 halted, 2 finished, 1 exited first; budget cap 20 ms with receipt | `r12/LOOPS_DRILL.json`, `r12/LOOPS_DRILL_LATE.json` |
| Service restart | `node r12/restart-proof.mjs` | echo, heartbeat, mcp-host all PASS (heartbeat log grew; mcp-host host.log appended; STOP clean) | `r12/RESTART_PROOF.json` |
| Lane suite | 19-file command in STATUS | 119 tests, 119 pass, 0 fail | this run |
