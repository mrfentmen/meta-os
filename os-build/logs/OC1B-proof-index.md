# OC1B-477/491/494 — proof index (this lane's claims only)

Every claim this lane makes → its committed file. All paths under
os-build/ on branch opencode/500-s17. Counts by type (OC1B-491): 20 .txt/.md
logs + 1 decision-pack .md + 1 status snippet = 22 files; 0 screendumps, 0
receipts (no captures, no live model calls in this lane); 3 gate outputs
(closeout-gate/node/queue). Total proofs committed by this lane: 22.
(OC1B-494: every path below was written by this lane in this session and is
staged/committed in the section checkpoints; any path that fails to resolve
after commit is struck — none at assembly time.)

## §17 decision-pack execution support (OC1B-401..425, minus status-file proofs)
| Task | Claim | File |
|---|---|---|
| 401/403/404/423 | baseline 2071/2015/56, settled count + reconciliation + newcomer + 3.4s timing | os-build/logs/OC1B-native-baseline.txt |
| 402 | 56 failing lines, file :: test | os-build/logs/OC1B-native-failures.txt |
| 405/406/414 | per-file counts, per-surface counts, sum check = 56 | os-build/logs/OC1B-native-groups.md |
| 407 | G1 run: 83/83/0 | os-build/logs/OC1B-native-g1.txt |
| 408 | G2 run: 6/0/6 | os-build/logs/OC1B-native-g2.txt |
| 409 | G3 run: 31/20/11 | os-build/logs/OC1B-native-g3.txt |
| 410 | G4 run: 6/0/6 | os-build/logs/OC1B-native-g4.txt |
| 411 | G5 run: 20/13/7 (1 out-of-suite noted) | os-build/logs/OC1B-native-g5.txt |
| 412 | G6 run: 28/23/5 | os-build/logs/OC1B-native-g6.txt |
| 413 | G7 run: 78/69/9 | os-build/logs/OC1B-native-g7.txt |
| 414-supp | SUPP run: 150/137/13 | os-build/logs/OC1B-native-supp.txt |
| 415/416/417/418/421/422 | update + carve-out tables, costs, PREP disagreements, no-edit attestation, no hidden regression | os-build/logs/OC1B-native-pack.md |
| 419 | refreshed decision pack with per-group evidence | os-build/NATIVE_55_DECISION_PACK.md |
| 420/424 | one-line summary + still-waiting ruling line | OC1B-s17-STATUS-SNIPPET.md (status text lives with coordinator) |
| 425 | section commit | commit sha reported back (branch opencode/500-s17) |

## §19 submission prep (OC1B-451..475, minus status-file proofs)
| Task | Claim | File |
|---|---|---|
| 451/452/453/454/456/457/463/464/467/468/471/473/474 | 7-item walk, readiness, verdict | os-build/logs/OC1B-submission-walk.md |
| 455 | library attributions | os-build/logs/OC1B-submission-attributions.md |
| 458 | secret scan, 0 live | os-build/logs/OC1B-submission-secrets.txt |
| 459/460/461/472 | state snapshot, clause map, reasons, lineage | os-build/logs/OC1B-state-snapshot.md |
| 462 | form fields dry-run, DEL-ONLY marks | os-build/logs/OC1B-submission-fields.md |
| 465/466 | rehearsal BLOCKED + gaps | os-build/logs/OC1B-submission-rehearsal.md |
| 469 | DEL-ONLY list | OC1B-s17-STATUS-SNIPPET.md |
| 470 | timeline to Nov 4 21:00 ET | os-build/logs/OC1B-submission-timeline.md |
| 475 | section commit | commit sha reported back |

## §20 closeout (OC1B-476..500, minus status-file/final-commit proofs)
| Task | Claim | File |
|---|---|---|
| 476 | gate ledger | os-build/logs/OC1B-gate-ledger.md |
| 478/494 | struck-path sweep: none struck at assembly | this file (OC1B-proof-index.md) |
| 479 | UNIMPLEMENTED list | os-build/logs/OC1B-unimplemented.md |
| 480 | UNPROVEN list | os-build/logs/OC1B-unproven.md |
| 481/484/485 | secrets 0-hit + syscalls history + no kernel edits | os-build/logs/OC1B-closeout-secrets.txt |
| 482/483 | no >1MB lane files; no binaries committed | os-build/logs/OC1B-closeout-largefiles.txt |
| 486 | soak collection (observed, not owned) | os-build/logs/OC1B-unproven.md (soak rows) |
| 487 | demo inventory + film sha | os-build/logs/OC1B-demo-inventory.md |
| 488 | final gate.sh: GATE GREEN | os-build/logs/OC1B-closeout-gate.log |
| 489 | final node: 2071/2015/56 identical | os-build/logs/OC1B-closeout-node.txt |
| 490 | final queue: 296 OK | os-build/logs/OC1B-closeout-queue.txt |
| 492/495/496/498/499 | handoff, spend, time, attestations | os-build/logs/OC1B-handoff.md |
| 493/497/500 | status-file pass + final commit + last line | coordinator-owned (see snippet); lane fence: no opencode/500 commit |

## OC1B-478 sweep result
All 22 paths above exist at their named locations at assembly time. Struck: none.
