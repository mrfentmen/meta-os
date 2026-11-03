# MT-02 in full detail — agentic loop, live frames (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 21:58 EST. This is a fixture/spec, not a
run. No live-key call has been made from Milo's VM for this slice, no live
frame has been assessed under MT-02, and nothing below is a pass. Firing
waits on BOTH: (1) Del tops up Meta API billing (HTTP 402 during Pax's live
hunt #3), and (2) Del picks a key route (Route A: key placed on Milo's VM;
Route B: Milo specs, Pax executes the live run and posts the receipt, Milo
verdicts it). Pax confirmed 2026-11-02 ~21:40 that no standing route is
declared, both routes' specs are to be prepped, and neither is fired until
Del picks AND the 402 is cleared. Spend cap $10 total for the whole
directive, guardrail-tracked; cost for MT-02 is TBD at fire time from the
published Spark rates, never invented here. Dispatch is simulated loopback
only, labelled SIMULATED everywhere; nothing dials a real service, ever.

## Pax's taxonomy call for MT-02, 2026-11-02 21:56 EST

This call closes the open mapping question left in eval/vigiles/scenarios.json
at fixture time, and it is applied here verbatim:

- MT-02 scores VIG-F03 against the manifest label verbatim:
  "public disturbance / altercation". It does NOT score VIG-F03 against a
  guessed category in js/products.js.
- The closest products.js categories, "possible altercation" and "physical
  contact", are NOT the mapping. They are named here only so the firing
  run does not silently substitute one of them for the manifest label.
- A model answer that names "crowd gathered" on a protest-confrontation
  frame is NOT a match for VIG-F03: the crowd description is true of the
  scene, but the altercation class was not committed to. That outcome is
  recorded as HELD (unconfirmed), routed to human review, exactly as
  EVAL4 batch 6 recorded it. HELD is a designed safe outcome, not a miss
  and not a match.
- The other two fixture rows keep their exact products.js matches:
  VIG-F01 scores against "crowd gathered", VIG-F02 against "normal
  activity". VIG-F02 is a match only on "normal activity": calling
  ordinary pedestrian traffic "crowd gathered" is the batch 4 false
  flag, fixed in batch 5 by narrowing "crowd gathered" to a stationary
  assembled crowd, and it must not be repeated as a match.
- The three unlabelled vigiles frames (fireworks, knife, rifle) are NOT
  scored in MT-02. They have no manifest entry and no EVAL4 verdict, so
  there is no ground truth to score them against. Labelling them first
  needs a manifest entry and a recorded adjudication, which is a
  separate task, not a label written here.
- VIG-F03 carries alert_expected true and review_expected true in the
  fixture. A live vigiles flag that matches the VIG-F03 pattern therefore
  ends in human review as well as in the simulated-dispatch step below;
  review does not replace the sim- receipt rule.

## What the check is

The same five-step agentic loop as MT-01, run over LIVE DOT cameras
instead of staged frames, through the hunt machinery in
server/queue/livehunt.py. A hunt is a BOUNDED pass with a written record,
not patrol's endless cycle. Per the module's own header:

1. Budget governor first: the Spark guardrail state is read before every
   check; when the remaining test budget reaches the reserve (default
   $5), the hunt stops BEFORE spending and the stop is recorded, never
   silent.
2. One crew check per frame (crew.Crew.check_camera) under a rotating
   lens (vigiles, then ignis, then medicus), through the production
   assessment: spark_gen.generate, the same function the livecams
   assess-one path uses. A hunt reading is a production reading, not a
   new path.
3. The outcome is appended to the hunt record verbatim: baseline,
   feed-error, job-error, cleared-by-review, flagged-unconfirmed, and
   dispatched-simulated are all filed, none hidden.
4. The hunt stops at the FIRST check whose outcome is
   "dispatched-simulated": the incident id and the simulated endpoint's
   receipt id are read back from the incident's own timeline
   (crew_records). A receipt is only ever reported from the record the
   dispatch step itself wrote.
5. Nothing here can manufacture a flag: the assessment is the model's,
   the flag rule is js/command-flag.js, and the judge's ruling is the
   crew's own.

Frame sources, named on the record, never blurred: live means
crew_common.load_cameras plus crew_common.fetch_snapshot, the NYCTMC
live list and per-camera stills fetched directly. Staged means
StagedFrames, stills captured from the LIVE DOT list minutes earlier
into a local directory (manifest.json plus one <camera-id>.jpg per
camera). A staged frame is never described as fetched live by the
process that ran it; the record repeats the capture time from the
manifest.

The five MT-01 steps apply in order, per frame, with the live additions
in brackets:

1. patrol: select the live cameras for this pass and record each
   camera's id, name, and area.
2. review: record the visible scene per frame, in the division's own
   scene-awareness terms (no diagnosis, cause, severity, triage, or
   treatment language anywhere, medicus included).
3. judge: one verdict per frame, flag or baseline, with judge_mode
   recorded. A judge verdict with no recorded judge_mode is an
   incomplete record, not a pass.
4. investigation: for every flagged frame, a second look that either
   confirms the flag with the visible evidence named, or downgrades it
   with the reason named. Baseline frames need no investigation step,
   but the record must say so explicitly per frame, not by omission.
   A flagged-unconfirmed outcome is filed as such, not upgraded.
5. simulated dispatch: for every flag that survives investigation, one
   dispatch attempt against the simulated loopback endpoint
   (crew.routed_dispatch through crew.dispatch_url, loopback-checked,
   SIMULATED endpoint only). The only acceptable receipt is a sim-
   receipt from that endpoint, read back from the incident timeline.
   A flag that ends anywhere else is a FAIL for that frame, reported
   as failed, never faked and never relabelled as baseline.

An honest zero is a passing shape only if the loop ran clean: every
frame's outcome filed verbatim, every judge_mode recorded, no flag
left without a sim- receipt or an explicit downgrade, and any budget
stop recorded where it stopped. A run with a missing step, a missing
judge_mode, a hidden feed-error or job-error, or an unreceipted
surviving flag is BLOCKED (incomplete record) or FAIL (flag
mishandled), never a pass. A run that stops at the budget reserve is
partial, and the record says where it stopped and what never ran.

## Run record shape — one hunt-format record

One record, landed on main by Pax (Route B) or by Milo (Route A),
named so the check is in the filename, for example
server/queue/livecam_records/mt02-live-<date>.json (the exact filename
is set at fire time; what matters is that the record exists and is
findable from MILO_TEST_STATUS.md). It keeps the hunt-record shape Pax
already lands on main (kind, started_at, camera_source, frame_source,
max_frames, budget_reserve_usd, outcomes) and ADDS the MT-01 timeline
and scoring fields; a record that copies the hunt shape without the
timeline and without the VIG-F03 scoring rule does not satisfy MT-02.

Each record contains, verbatim field names:

- `kind`: the hunt kind already used on main, plus `check`: `"MT-02"`.
- `main_tip`: the origin/main commit the run was fired from.
- `route`: `"A"` or `"B"`, plus who executed the live steps and who
  issued the verdict (Route B: Pax executed, Milo verdicts from the
  receipt; Route A: Milo executed and verdicts).
- `spend_usd`: actual spend for this record; running total against
  the $10 cap is updated in MILO_TEST_STATUS.md at fire time.
- `frame_source`: `"live fetch via crew_common.fetch_snapshot"` or
  the staged-dir form, with the staged manifest capture time repeated
  when staged. Never the wrong one.
- `outcomes`: one entry per live reading, in patrol order, each with:
  `camera_id`, `camera_name`, `area`, `division`, `outcome` (baseline,
  feed-error, job-error, cleared-by-review, flagged-unconfirmed, or
  dispatched-simulated, verbatim), `category`, `incident_id` (null for
  baseline), plus `judge_mode`, `investigation` (null for baseline
  with reason "no flag", or the confirm/downgrade outcome with
  evidence for a flag), and `dispatch` (null for baseline/downgraded,
  or the sim- receipt string for a surviving flag, labelled
  SIMULATED, read back from the incident timeline).
- `vigiles_scoring`: for any vigiles outcome, the fixture row it was
  scored against (VIG-F01, VIG-F02, or VIG-F03) or null with the reason
  when no fixture row applies; for VIG-F03, the scored label is the
  manifest label "public disturbance / altercation" verbatim, never a
  guessed products.js category, and a "crowd gathered" answer on that
  row is recorded HELD, not MATCH.
- `timeline`: the five steps in order (patrol, review, judge,
  investigation, simulated dispatch), each with a started/completed
  marker. A step with no marker did not happen for this record.
- `outcome`: `"pass"` | `"fail"` | `"partial"` — pass only when every
  reading has every applicable step, every judge_mode is recorded,
  every surviving flag holds a sim- receipt, and no outcome was
  hidden. Partial means the run stopped at the budget reserve or on
  an error mid-pass; the record says where it stopped.
- `failures`: every failure named, none hidden, including flags that
  ended without a receipt, frames whose judge step is missing a mode,
  and every feed-error and job-error with its camera named.

## Firing steps, by route (same steps, different hands)

Route B (the route that works once credits exist, no key movement):
Pax executes the bounded live pass, posts the hunt-format record plus
the receipt, and Milo verdicts it against the pass rules and the
VIG-F03 scoring rule above, in his own words, on room 1 and in
MILO_TEST_STATUS.md.

Route A (only after Del places the key on Milo's VM): Milo executes
the same bounded pass himself, inside the cap, posts the record, and
verdicts it the same way.

Either route: if the 402 is still present at fire time, the run does
not start; MT-02 stays BLOCKED and the attempt (not a result) is noted
in MILO_TEST_STATUS.md. If the cap or the $5 reserve is hit mid-pass,
the pass stops, the record is marked partial, and the tally is posted
to room 1.

## What this prep does NOT claim

- No MT-02 run has happened. No live frame has been judged under MT-02.
- No sim- receipt exists yet. No spend has occurred ($0 on this slice).
- No vigiles frame beyond the fixture's three rows has been labelled,
  and no products.js category has been invented for VIG-F03.
- The 12-hour brand-kit audit is NOT started here: Pax's 21:56 note
  says it runs when OC1's kit commit lands, and no such commit is
  named in that note. That lane stands by, it is not claimed as done.
- This file does not change the slice: MT-03..MT-08 keep their prep
  specs in MILO_TEST_PREP.md, and MT-08 gate duty stays with Milo's
  rust-work loop — this 5-minute job runs no gate-1.
