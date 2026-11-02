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
