# OC1B-s9 STATUS SNIPPET (opencode/500-s9 — coordinator merges; OPENCODE1_500_STATUS.md untouched)

Branch opencode/500-s9, base 94010c76 (opencode/500, incl. main 3452d244).
§9 commit 1f1cd65f, §10 commit 8f45dc91, §13 commit (this checkpoint) below.
Kernel never touched: no kernel/ edits on this branch (model-pipeline lane only).
Untracked runtime state (NOT committed, by design): server/queue/model_receipts.jsonl,
/tmp/oc1b-imperium/* (crew-data, logs). Guardrail total after all sections: $0.3108 of $75.

## §9 Model pipeline live proofs (OC1B-201..OC1B-225) — PROVEN with 3 named UNPROVEN
- PROVEN (21): 201 (296/296 baseline), 202 (key length 48, value never logged),
  203/204 (wonder chat "WONDEROK" + receipt), 205 (SAM box 10,0-599,353 on ignis-fire-1),
  206 (SAM-vs-Spark regions compared as they fell), 207 (oc1b-gen.webp 112,320 B webp + receipt),
  208/209 (live SAM segment step in patrol timeline, prompt = first observation description),
  210/211 (key-withheld segment error step, no region; incident still dispatched-simulated),
  214 (Wonder fallback reader spark + named fallback), 216 (judge deterministic side),
  217 (forced judge fallback named), 218 (all-flags timeline), 219 (loopback dispatch
  sim-localhost-001, service fire department, package simulated=true), 220 (transcribe
  raises EndpointUnresolvedError; no crew wiring), 221 (spend $0.038 Spark + estimates),
  222 (296/296 after), 223 (proof file), 224 (failures block).
- UNPROVEN with reason (3): OC1B-212/213 Wonder review reader — crew.py calls
  chat_image at default max_tokens=1600; Wonder spends 1598/1600 on reasoning
  (measured live, finish=length, content null) so the step falls back to Spark.
  With max_tokens=4000 Wonder answers the SAME prompt with a valid v2 ignis
  reading (structure fire, 5 obs) — budget, not wiring, is the blocker.
  OC1B-215 judge_mode "model" — same class: Spark spends 1198/1200 reasoning
  tokens on the judge prompt (finish=length); deterministic fallback PROVEN in
  its place. DEFECT filed in os-build/logs/OC1B-model-proofs.md for the crew lane.
- Spend §9: $0.097 guardrail-counted (Spark $0.053 actual-rate incl. assess reading).

## §10 Live cameras (OC1B-226..OC1B-250) — PROVEN (fetcher end to end, one wording wart)
- PROVEN (24): 226 (975 online), 227 (all entries id/name/area/nyctmc-imageUrl),
  228-235 (7 assessed readings: Brooklyn/Manhattan/Manhattan-ignis/Queens-medicus/
  Bronx/Staten Island all committed as dated frame+reading; Staten Island HAS cameras),
  236 (Belt Pkwy pick = sort-first, repeat-deterministic), 237 (count-3 snapshots),
  238 (7/7 v2 contract), 239 (all descriptions match their frames, viewed; 0 flags),
  240 refusal holds with wording note (URLError at list stage, NOT LiveCamError —
  module-owner wart, loud failure + no frame either way), 241 (error page rejected),
  242 (12/12 offline), 243 (spend ~$0.038), 244 (index, Pax row first), 245 (honest
  zero flags — valid result), 246 (no handoff), 247 (only webcams.nyctmc.org fetched),
  248/249 (failures + verdict in runs file).
- UNPROVEN/BLOCKED: none. All 25 tasks have verdicts; 240's wart is named, not a gap.

## §13 Imperium full live runs (OC1B-301..OC1B-325) — PROVEN with 2 named OPEN gaps
- PROVEN (23): 301 (8 gaps listed), 302 (heartbeat running/nyctmc-live/975),
  303 (camera_source nyctmc-live verbatim), 304 (10-batch: 10 baseline, 0 errors),
  305 (per-check table, lens rotation visible), 306 (honest zero — 0 flags/22 checks),
  307 (STAGED incident 15 steps -> dispatched-simulated, staged:true everywhere),
  308 (sim-8488ea6982679dd0, simulated=true, /police, SIMULATED police endpoint),
  309 (fence REFUSES external/IP, ALLOWS loopback), 310 (BOLO built, purge receipt
  files_removed 1), 311 (card ID: UNIDENTIFIED, descriptions+marks only, node-rendered),
  312 (cleared-by-review, closed-false-positive), 313 (inconclusive hold, 0 dispatches),
  314 (flagged-yellow-review, chain ends at flag), 315 (stop: max_actions 8),
  316 (paused-budget, 0 crew calls), 317 (paused_cameras [cam-1] in heartbeat),
  318 (SAM batch 3/3 baseline, no segment-eligible flag), 319 (5/5 JSON+timestamps),
  320 (296/296 after), 321 (spend +$0.1756), 322/323/324 (gaps closed/blockers/record).
- OPEN with reason (2): G2 natural-flag end-to-end (0 flags in 22 checks; staged runs
  cover the pipeline, labelled STAGED — a flag cannot be manufactured); G8 judge_mode
  "model" (same §9 starvation finding; deterministic fallback PROVEN in its place).
- No task in this lane points dispatch anywhere but the simulated loopback endpoint;
  no real emergency service was contacted (loopback HTTP receivers only).

## Proof paths committed
- §9: os-build/logs/OC1B-model-queue-baseline.txt, OC1B-model-key.txt,
  OC1B-model-proofs.md, OC1B-model-queue-after.txt, os-build/logs/oc1b-model-proofs/
  (wonder-chat.txt, sam-direct.json, sam-vs-spark.md, oc1b-gen.webp,
  sam-patrol-timeline.json, sam-failure-timeline.json, wonder-review-timeline.json,
  wonder-fallback-timeline.json, judge-model-timeline.json,
  judge-deterministic-timeline.json, judge-fallback-timeline.json,
  all-flags-timeline.json, transcribe-unresolved.txt)
- §10: os-build/logs/OC1B-livecams-list.txt, OC1B-livecams-runs.md,
  OC1B-livecams-index.md, OC1B-livecams-tests.txt,
  server/queue/livecam_records/live-20261102-1613*..161430-*.jpg/.json (17 files)
- §13: os-build/logs/OC1B-imperium-gaps.md, OC1B-imperium-live.md,
  OC1B-imperium-queue-after.txt, os-build/logs/oc1b-imperium/
  (staged-dispatch.json, fence-check.txt, bolo-purge.json, cleared-path.json,
  inconclusive-path.json, yellow-path.json, budget-stop.json)
