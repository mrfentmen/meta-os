# Round 12 — FINISH

Branch `buffy/round12`, main merged. **35 done, 9 partial, 0 not started, of 44.**

| task | title | state | evidence / why not |
|---|---|---|---|
| R12-001 | Aegis OSV sweep 1 | **DONE** | 23 manifests, 108 refs, 0 findings |
| R12-002 | KEV cross-check | **DONE** | 0 sweep findings; 7 non-sweep excluded |
| R12-003 | Second sweep + diff | **DONE** | 0 added / 0 removed / 7 unchanged |
| R12-004 | OSINT CT | **DONE** | 4 domains, counts recorded |
| R12-005 | OSINT DNS | **DONE** | 4 domains, 3 findings |
| R12-006 | Watch-target file | **DONE** | 169 targets, initially UNVERIFIED |
| R12-007 | Watch review format | **DONE** | fill-in ledger, checked dates |
| R12-008 | Imperium hosted loop | **DONE** | PASS, dispatch 201 |
| R12-009 | Cadence hosted loop | **DONE** | exit 0, receipt |
| R12-010 | Chaos over five loops | **DONE** | Musica/Officina NOT COVERED |
| R12-011 | Userspace hog | **DONE** | compiles; wiring proposal |
| R12-012 | Userspace quitter | **DONE** | compiles; ps note |
| R12-013 | IPC gap record | **DONE** | IPC_GAP.md |
| R12-014 | Nervus face gap record | **DONE** | NERVUS_FACE_GAP.md |
| R12-015 | Git-history secret scan | **DONE** | 1,881 commits, 14 category hits, counts only |
| R12-016 | Findings to ledger | **DONE** | 0 sweep findings, batch receipt written |
| R12-017 | Liveness checks | **DONE** | 168 LIVE, 1 UNREACHABLE, 0 DEAD |
| R12-018 | OPSEC checklist | **DONE** | 20 pass, 0 fail, 112 screenshots UNCHECKED |
| R12-019 | Aegis hosted cycle | **DONE** | sweep 23/108/0 → KEV 0 → ledger, registry entry |
| R12-020 | False-positive drill | **DONE** | 3 clean packages, 0 findings |
| R12-021 | Imperium baton | **DONE** | killed mid-run, resume exit 0, 1 dispatch |
| R12-022 | Cadence baton | **DONE** | 1 stage-1, 1 continuation, 1 baton-pass |
| R12-023 | STOP on every loop | **PARTIAL** | 5 halted mid-run, 3 finished before stop; no orphans |
| R12-024 | Budget-kill drill | **DONE** | 20 ms cap, budget receipt, registry cap unchanged |
| R12-025 | Watchman death drill | **DONE** | alarm raised, restart to result in 83 ms |
| R12-026 | Registry honesty | **DONE** | hosted entries real; drafts say why |
| R12-027 | Cluster 1 | **PARTIAL** | audit + drivers; restart gap filed |
| R12-028 | Cluster 2 | **PARTIAL** | audit + drivers; restart gap filed |
| R12-029 | Cluster 3 | **PARTIAL** | echo restart PASS; other rows gap |
| R12-030 | Cluster 4 | **PARTIAL** | heartbeat restart PASS; other rows gap |
| R12-031 | Cluster 5 | **PARTIAL** | mcp-host restart named, not drilled |
| R12-032 | Cluster 6 | **PARTIAL** | audit + drivers; restart gap filed |
| R12-033 | Cluster 7 | **PARTIAL** | audit + drivers; restart gap filed |
| R12-034 | Cluster 8 | **PARTIAL** | audit + drivers; restart gap filed |
| R12-035 | Second-ring summary | **DONE** | 38 services; 2 restarts proven; 35 gap |
| R12-036 | Nervus record schemas | **DONE** | five operations, types + JSONL shape |
| R12-037 | No stub renders real | **DONE** | every ledger line and receipt labelled stub |
| R12-038 | Hands-Free → Cadence | **DONE** | real child exit 0, brief, latency |
| R12-039 | Intake refusals | **DONE** | malformed, empty, oversized recorded |
| R12-040 | Voice seam | **DONE** | 404 and model_not_found probe cited |
| R12-041 | Proof ledger | **DONE** | PROOF_LEDGER.md updated |
| R12-042 | Full-lane test run | **DONE** | 119 tests, 119 pass, 0 fail |
| R12-043 | Round-12 FINISH | **DONE** | this file |
| R12-044 | Blocker message | **DONE** | PAX_BLOCKERS_R12.md |

## What is proven

- Section A's 14 blockers are closed with measured records.
- Section B: 1,881-commit history scan (counts only), zero findings still receipted, 169 targets
  checked (168 live, 1 unreachable), OPSEC 20/20 with screenshots named unchecked, hosted Aegis
  cycle ran all three stages, and clean input stayed clean.
- Section C: Imperium resumed with one dispatch; Cadence continued one artifact course; a killed
  watchman was detected and restarted in 83 ms; 8 hosted loops got a STOP outcome with no
  orphans; a 20 ms budget cap was enforced with a receipt and no self-raise.
- Section D: 38 services inventoried; 31 with measured drivers; 5,853 assertions attributed;
  echo and heartbeat killed and restarted with state recorded.
- Lane suite: **119 tests, 119 pass, 0 fail**.

## What is a record, not a result

- OSV/OSINT counts are host-run records; no network scan of third parties.
- Imperium dispatch is simulated loopback only; no model call, no assessment.
- The service audit is mechanical; 35 service restarts cannot run on a host.

## Still a gap

- R12-023: 3 fast loops finished before the STOP landed (their pre-spawn STOP is proven).
- 35 of 38 service restarts: no runnable main; needs the K5/K6 supervisor.
- mcp-host restart is named but not drilled.
- No kernel compile/boot here; no model; transcription endpoint unresolved.
