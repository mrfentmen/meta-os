# OC1B §13 live record — Imperium full live runs (Mac, tree 94010c76, 2026-11-02)

Stack: queue_service.py :8935 (SIMULATED dispatch receiver) + trio_agent.py
(resident agent, real Spark assessments) + patrol.py, all on the local
SQLite fallback store (TRIO_STORE=local, TRIO_LOCAL_DB + TRIO_CREW_DATA_DIR
under /tmp/oc1b-imperium/ — no repo runtime state touched).
Agent log shows the production self-correction live: a medicus reply failed
validation (requires_human_review must be true) and the agent made its one
bounded correction retry.

## OC1B-302 crew-status heartbeat
service imperium-patrol, state running, at 2026-11-02T16:17:42Z (first
production visit), camera_source nyctmc-live, 975 cameras, guardrail
remaining $74.86 of $75. Heartbeat present and updating every cycle.

## OC1B-303 live source
patrol: camera list source: nyctmc-live (975 online cameras). The status
names the live NYCTMC list, not the fallback subset. Quoted verbatim.

## OC1B-304 patrol batch (10 checks)
patrol: counts: {'checks': 10, 'baseline': 10, 'flagged': 0, 'reported': 0,
'feed_errors': 0, 'job_errors': 0} (patrol-batch.log; a further 8 checks from
the harness-killed first attempt + 1 --once + 3 SAM batch = 22 production
checks total, all baseline, zero errors of any kind).

## OC1B-305 per-check table (batch of 10; lens rotates vigiles -> ignis -> medicus)
- vigiles | QBB @ Crescent St | baseline | normal activity
- ignis | 1 Ave @ 84 St | baseline | no hazard visible
- medicus | Pelham Shore Rd @ City Island Rd | baseline | normal activity
- vigiles | Canal Street @ Chrystie Street | baseline | normal activity
- ignis | Old Fulton St @ Vine St/Hicks St - quad - 156.24 | baseline | no hazard visible
- medicus | Central Park West @ 65 St | baseline | normal activity
- vigiles | Bay Pkwy @ 78 St (Kings Hwy) | baseline | normal activity
- ignis | Hillside Ave @ Little Neck Pkwy | baseline | no hazard visible
- medicus | GCP @ 31 ST | baseline | normal activity
- vigiles | Central Park West @ 86 St | baseline | normal activity
Rotation visible across the record: vigiles, ignis, medicus repeating.

## OC1B-306 natural flag
No-natural-flag line: 0 flags in 22 production checks — an honest zero.
(The §10 livecam section independently found 0 flags in 7 assessed readings.)

## OC1B-307 staged dispatch (STAGED in every artifact)
os-build/logs/oc1b-imperium/staged-dispatch.json: vigiles "person down" on a
STAGED frame, 15 timeline steps
(flag,decision,review,reported,decision,investigation x3+evidence,decision,
brief,bolo,dispatch), outcome dispatched-simulated, every step labelled
staged:true, incident carries staged:true.

## OC1B-308 receipt
receipt_id sim-8488ea6982679dd0, simulated=true, service_route /police,
destination "SIMULATED police endpoint (local stack route) — no real
emergency service is contacted by this system", service {police, /police}:
vigiles -> police routing PROVEN through the real production receiver.

## OC1B-309 fence
os-build/logs/oc1b-imperium/fence-check.txt: external host + bare IP REFUSED
with DispatchBoundaryError; 127.0.0.1/localhost ALLOWED. No task points
dispatch anywhere else.

## OC1B-310 BOLO + purge
os-build/logs/oc1b-imperium/bolo-purge.json: flagged "person down" with
visible-marks observation -> BOLO built via evidence.build_bolo (11 keys,
all in BOLO_KEYS) -> review cleared (baseline second reading) -> outcome
cleared-by-review, record closed-false-positive, purge receipt
{reason closed-false-positive, files_removed 1}, evidence files [] after.
Convention-shaped marks extract to ["red tattoo on left forearm; scar above
right eye"] (prompt convention: own observation beginning "Visible marks:").

## OC1B-311 UNIDENTIFIED card
boloCard render (js/surfaces.js, run live under node): header
"ID: UNIDENTIFIED", rows from BOLO_KEYS only (division, category,
camera_name, area, flagged_at, frame_files, face_crops,
person_descriptions, visible_marks, direction_note) — descriptions +
visible marks only, zero identity fields (no name/id/match anywhere; the
one "name" substring in the HTML is the camera_name key itself).

## OC1B-312 cleared path
os-build/logs/oc1b-imperium/cleared-path.json: outcome cleared-by-review,
record closed-false-positive, 0 dispatch steps.

## OC1B-313 inconclusive path
os-build/logs/oc1b-imperium/inconclusive-path.json: review error "STAGED
review job failed" -> verdict inconclusive, judge_mode deterministic,
judge_reasons ["the review reading failed or carried no category; the judge
does not confirm on a missing reading"], timeline [flag, decision, review,
decision], record monitoring, 0 dispatch steps — the hold, with NO dispatch
spent.

## OC1B-314 yellow path
os-build/logs/oc1b-imperium/yellow-path.json: "energetic movement"
(yellow-tier) -> outcome flagged-yellow-review, record yellow-review, NO
review step at all, 0 dispatch — chain ends at the flag.

## OC1B-315 budget governor
os-build/logs/oc1b-imperium/budget-stop.json: incident with 8 actions on its
timeline -> orchestrator decision "stop", reason "stop condition reached:
max_actions (8) — the incident already has 8 actions on its timeline; no
further action is ordered". The 8/12/$0.50 caps are enforced in code.

## OC1B-316 patrol budget pause
With remaining_usd $0.10 <= reserve $5: outcome paused-budget, crew
check_camera called 0 times (NOTHING filed), status paused-budget with the
reserve reason, patrol-status event recorded. PROVEN.

## OC1B-317 supervisor pause
cam-1 in paused-feeds.json -> outcome no-cameras, heartbeat state idle with
paused_cameras ["cam-1"] naming the skipped camera. PROVEN.

## OC1B-318 SAM batch over live cameras
TRIO_SAM_SEGMENT=1, 3 production checks: 3 baseline, 0 flagged — no segment
step landed because none could (segment is flag-gated by construction); the
all-baseline batch records exactly that. Full-session: 0 segment-eligible
flags in 22 checks.

## OC1B-319 records check
Last 5 event lines: each complete JSON with an "at" timestamp (5/5, no torn
writes); dispatches.jsonl holds sim-8488ea6982679dd0 (simulated true);
crew-status.json current (service imperium-patrol, state running).

## OC1B-321 spend (Spark-rate estimate)
§13 delta from guardrail state: 30 calls, +$0.1756 est (22 production
assessments incl. bounded medicus correction retries + staged/path runs'
stub seams cost $0). Guardrail total after §13: $0.3108 of $75.
