# Wave2 Section 5 — Tasks 41-50 Findings

Date (UTC): 2026-11-02
Sources (in /tmp/round6, NOT /tmp/wave2): `os-build/logs/R5-imperium/`, `os-build/logs/R6-imperium-ignis/`, `/tmp/med-out/` (= `face-medicus` mirror in /tmp/wave2), `server/queue/judge.py` + `crew.py` + `queue_service.py`.

## Live loops (41-43)
- 41 R5 vigiles (R5-4 LIVE LOOP GREEN): incident `incident-27e9cfbd46e8078d`, cam-a `1 Ave @ 84 St`, `person down` / vigiles → outcome `dispatched-simulated`.
- 42 R6 ignis (R6-3 IGNIS LIVE LOOP GREEN): incident `incident-2eceddca76f1e61f`, cam-b `Central Park West @ 65 St`, `visible flame` / ignis → outcome `dispatched-simulated`.
- 43 Medicus (FACE-45 MEDICUS LOOP GREEN): incident `incident-725c546b990dd1b4`, cam-c `Broadway @ 45 St`, `person on ground` / medicus → outcome `dispatched-simulated`.

## Ids + outcomes (44-46)
- 44 Incident ids: `27e9cfbd46e8078d` (R5), `2eceddca76f1e61f` (R6-ignis), `725c546b990dd1b4` (medicus). Each: 1 recorded, status `dispatched-simulated`, timeline `flag,decision,review,reported,decision,investigation(x5+evidence),decision,brief,bolo,dispatch`.
- 45 Receipt ids (all `simulated=true`): `sim-6623d237a90b3d9d` (R5), `sim-9da0ad66d87add2e` (R6-ignis), `sim-5f894be30820178f` (medicus).
- 46 Packages: R5 `dispatch_mode:auto human_verify:False` (older shape, no `service` block); R6-ignis same auto shape; medicus `dispatch_mode:judge-confirmed human_verify:True judged_by:imperium-judge`, picture frame set, evidence_crop null. All `destination` = SIMULATED local-stack only.

## Judge routing (47-50)
- 47 `server/queue/judge.py:40-53` SERVICES: vigiles→`police` `/police`, ignis→`fire department` `/fire`, medicus→`hospital (EMS receiving)` `/hospital`; `service_route()` returns None for unknown (never guesses).
- 48 `judge.combine()`: confirmed (two flagged readings agree or both flagged), cleared (review baseline), inconclusive (review missing/failed/unparseable). Medicus review step shows `verdict:confirmed judged_by:imperium-judge` with reason `two independent readings agree on 'person on ground'`; R5/R6 review steps `verdict:confirmed` (pre-judge-reasons shape).
- 49 `crew.py:621-643,698-724`: route=`judge.service_route(division)`, package `simulated:True judged_by:imperium-judge dispatch_mode:judge-confirmed requires_human_review:True` (post-hoc audit, not a gate); dispatch step records `service` + `receipt_id`.
- 50 `queue_service.py:165`: receiver stamps `service_route` from path suffix (`/default` when posting to `/dispatch-simulated`), refuses non-`simulated:true`; medicus dispatch step records `service:hospital (EMS receiving)`. Loopback-only guard in crew (no real service contacted).
