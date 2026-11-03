# OC1B demo shotlist (tasks 251-252) — kernel-only film, current tree

Source beats: DEMO_KERNEL_ONLY_PLAN (8 beats, 180s) + DEMO_SCRIPT fallbacks.
Backing rule: every shot names its committed log or live run; unbacked shots
are cut at list time, not at edit time. Tree 94010c76, image 58ed24c1.

| # | Shot (film segment) | Backing (committed) | Status |
|---|---|---|---|
| b1 | boot banner/alive/mem lines (s01, 22s) | os-build/demo/oc1b-beat1-serial.txt L1-2,19,20,23,26 (K1 live boot) | BACKED |
| b2 | loader lines, 3 user addresses, HELLO (s02, 25s) | same serial L32-43 | BACKED |
| b3 | hello exit 0, sleeper cycle, crasher line (s03, 23s) | same serial L34-44 | BACKED |
| b4 | fault line + sleeper continues + refusal + readkey got=5 typed live (s04, 22s) | same serial L45,48,55-56,75,409-410 | BACKED |
| b5 | status x2 (ticks 2073->3719), mem, ps 8 rows, live in one session (s05, 28s) | os-build/logs/OC1B-demo-beat5-serial.txt L2075-2089 (K2 live session) | BACKED |
| b5c | bad-syscall refusal close | K1 L75 + K2 L86 `user bad syscall 99 refused` | BACKED |
| b6a | fetch ribbon ASCII (s06, 9s) | beat5 serial L2096-2105 | BACKED |
| b6b | fetch facts: Mrfentmen, OS, Host, Uptime, Tasks, Mem, Programs (s07, 9s) | beat5 serial L2108-2115 | BACKED |
| b7a | livecam assessment terminal output, live (s08, 6s) | os-build/logs/OC1B-demo-beat6-live.txt (live run 11:14 EST) | BACKED |
| b7b | live frame full screen: 3 Ave @ 60 St still (s09, 8s) | os-build/demo/oc1b-beat6-frame.jpg (live fetch, sha in reading) | BACKED |
| b7c | reading scrolled: vigiles normal activity, uncertainties, spark (s10, 6s) | os-build/demo/oc1b-beat6-reading.json | BACKED |
| b7d | dispatch honest shape: none sent, SIMULATED endpoint, simulated=true (s11, 6s) | os-build/logs/oc1b-chain/live-baseline-chain.json (outcome baseline) | BACKED |
| b8 | close: status + ps stills, closing line (s12, 16s) | beat5 serial L2078,2088 | BACKED |
| cut | 180.000s assembly (22+25+23+22+28+9+9+6+8+6+6+16) | os-build/demo/oc1b-cut.txt + ffprobe in OC1B-demo-capture.md | BACKED |
| check | t=10/t=90/t=160 frame checks | os-build/demo/oc1b-check/t{10,90,160}.png + notes in OC1B-demo-capture.md | BACKED |

Cut at list time: none — every shot has committed backing (fresh K1/K2
serials this tree + capture-day live frame/reading/chain). Dropped from the
old script at plan level (not listed here): the retired R5 staged beat-6
reading and its sim- receipt (never presented as real anywhere).

Conditional beats (plan): K3/K4 log-gated inserts — NO gate logs committed
at capture time (no K3/K4 boot serial exists on this branch), beats absent.
KF graphics bonus — no KF-11 pack exists, absent. Film runs exactly 180s
without them.
