# Round 13 — program proof ledger

Bond's format: command, counts, evidence path. Only what actually ran appears with a count;
a blocked run says BLOCKED in its own row.

| lane | command | counts | evidence |
|---|---|---|---|
| A–D services contract/failure/restart/pairs | `os-build/layer1/pair_audit.py`, per-section scripts | 25 / 25 audited; 39 gaps; 25 / 25; 23 gaps, 2 observed; 10 / 10; 1 drilled, 9 gaps; 25 / 25; **0 pairs exist**, 1 live permission (dhcp→net, unused) | os-build/round13/{,failures/,restarts/,pairs/}SECTION_*.md |
| E OSV sweeps | `os-build/layer1/manifest_sweep.py` | 25 / 25; 10 real manifests, 15 missing, 107 refs, **0 findings**, control passed | os-build/round13/aegis/SECTION_E.md |
| F KEV cross-check | `os-build/layer1/kev_crosscheck.py` | 25 / 25; 0 findings to check, feed 2026.10.30 (1,766 entries), control passed | os-build/round13/aegis/SECTION_F.md |
| G secret counts | `os-build/layer1/secret_counts.py` | 25 / 25; 241 matches (240 env mentions, **1 bearer review item**), self-check passed | os-build/round13/aegis/SECTION_G.md |
| H surface/confusable | `os-build/layer1/surface_passes.mjs` | 25 / 25; 16 scanned (1.9 M chars), 9 missing artifacts, **0 findings** | os-build/round13/aegis/SECTION_H.md |
| I OSINT | `os-build/layer1/osint_passes.py` | 25 / 25; 15 passes run, 9 not implementable, 1 unavailable; **2 findings** (NXDOMAIN, soft 404) | os-build/round13/aegis/SECTION_I.md |
| J OPSEC | `os-build/layer1/opsec_checks.py` | 25 / 25; 20 decided, 3 not inspectable, 2 n/a; **4 failures, 6 findings** | os-build/round13/aegis/SECTION_J.md |
| K runtime drills | `node os-build/layer1/agent_drills.mjs` | 25 / 25; 19 observed, 2 refused, 1 not exercised, 3 gaps; **5 findings** | os-build/round13/agents/SECTION_K.md |
| L baton proofs | `node --test tests/agents-*.test.mjs` | 25 / 25; 4 proven by passing tests, **21 gaps** (no per-loop fixture, no tree diff) | os-build/round13/agents/SECTION_L.md |
| M–O loop drills | `node os-build/layer1/loop_drills.mjs` | M {"total":25,"OBSERVED-GAP":9,"OBSERVED":12,"GAP":4} · N {"total":25,"OBSERVED":21,"OBSERVED-GAP":2,"GAP":2} · O {"total":25,"OBSERVED":11,"GAP":5,"OBSERVED-GAP":9} | os-build/round13/agents/SECTION_M.md, SECTION_N.md, SECTION_O.md |
| P Hands-Free intake | `node --test handsfree/intake_cases.test.mjs` | {"total":25,"filed_ok":21,"refused":2,"fences_checked":3,"findings":14} | os-build/round13/handsfree/SECTION_P.md |
| Q Nuntius relay | `node --test relay/relay.round13.test.mjs` | {"total":25,"ok":17,"findings":8} | os-build/round13/nuntius/SECTION_Q.md |
| R Nuntius board | `node --test board/board.round13.test.mjs` | {"total":25,"ok":21,"findings":4} | os-build/round13/nuntius/SECTION_R.md |
| S userspace | `cargo check --manifest-path user/Cargo.toml` (BLOCKED) | {"total":25,"implemented":18,"partial":1,"abi_blocked":6,"cargo_check":"BLOCKED"} | os-build/round13/userspace/SECTION_S.md |
| T federation drills | `node federation/sim.mjs` | {"drills":15,"records":19,"handoffs":4} (all SIMULATED: true) | os-build/round13/federation/SECTION_T.md |

Full-lane run: 130 passing, 0 failing — `FULL_LANE_TEST_RUN.md`.
