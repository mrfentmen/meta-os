# MT-01 in full detail — agentic loop, end to end, staged frames (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 21:43 EST. This is a fixture/spec, not a
run. No live-key call has been made from Milo's VM for this slice, no frame
has been assessed live under MT-01, and nothing below is a pass. Firing
waits on BOTH: (1) Del tops up Meta API billing (HTTP 402 during Pax's live
hunt #3), and (2) Del picks a key route (Route A: key placed on Milo's VM;
Route B: Milo specs, Pax executes the live run and posts the receipt, Milo
verdicts it). Pax confirmed 2026-11-02 ~21:40 that no standing route is
declared, both routes' specs are to be prepped, and neither is fired until
Del picks AND the 402 is cleared. Spend cap $10 total for the whole
directive, guardrail-tracked; cost for MT-01 is TBD at fire time from the
published Spark rates, never invented here. Dispatch is simulated loopback
only, labelled SIMULATED everywhere; nothing dials a real service, ever.

## What the check is

One agentic-loop run over staged (committed, not live-camera) frames, in
five steps, in order, for each of the three divisions:

1. patrol — select the staged frames for the division and record each
   frame's source path.
2. review — record the visible scene per frame, in the division's own
   scene-awareness terms (no diagnosis, cause, severity, triage, or
   treatment language anywhere, medicus included).
3. judge — one verdict per frame: flag or baseline, with `judge_mode`
   recorded (see below). A judge verdict with no recorded `judge_mode`
   is an incomplete record, not a pass.
4. investigation — for every flagged frame, a second look that either
   confirms the flag with the visible evidence named, or downgrades it
   with the reason named. Baseline frames need no investigation step,
   but the record must say so explicitly per frame, not by omission.
5. simulated dispatch — for every flag that survives investigation, one
   dispatch attempt against the simulated loopback endpoint. The only
   acceptable receipt is a `sim-` receipt from that endpoint. A flag
   that ends anywhere else (no receipt, a real-service call, a made-up
   receipt) is a FAIL for that division's run, reported as failed,
   never faked and never relabelled as baseline.

An honest zero is a passing shape only if the loop ran clean: every step
on the timeline for every frame, `judge_mode` recorded, and no flag left
without a `sim-` receipt or an explicit downgrade. A run with a missing
step, a missing `judge_mode`, or an unreceipted surviving flag is BLOCKED
(incomplete record) or FAIL (flag mishandled), never a pass.

## Staged-frame inputs, as they sit on main

These paths were read off origin/main (tip e2b2c587 at prep time); the
firing run must re-verify them against the main tip at fire time and
record that tip in the run record, because main moves.

- ignis: `eval/ignis/scenarios.json` (alert categories: visible smoke,
  visible flame; alert expected only when the scene shows visible smoke
  or visible flame) plus its adapter/harness `eval/ignis/run.mjs`,
  `eval/ignis/adapter.mjs`.
- medicus: `eval/medicus/scenarios.json` (scene categories: person on
  ground, crowd gathered around a person, vehicle collision scene,
  blocked crew access, person motionless; scene awareness only, plus
  the look-alikes named in the slice doc's product rules) plus
  `eval/medicus/run.mjs`, `eval/medicus/harness.mjs`.
- vigiles: there is NO `eval/vigiles/` scenario set on main at prep
  time. The vigiles staged frames on main are
  `test-footage/frames/vigiles-*.jpg` (altercation, crowd, fireworks,
  knife, normal, rifle). The vigiles MT-01 run therefore uses those
  frames plus the vigiles categories in `js/products.js`, and its
  record must name the frame files individually. If Pax wants a
  vigiles scenario JSON matching the ignis/medicus shape, that is a
  separate fixture task — it is NOT invented here, and the vigiles run
  is not claimed to have a scenario file it does not have.

Shared shape reference: the hunt-format records Pax lands on main
(`server/queue/livecam_records/hunt-2026-11-02-live*.json`) carry, per
frame, camera/frame identity, area, division, outcome, category, and
incident id (null for baseline). An MT-01 record keeps those fields
where they apply and ADDS the timeline below; a record that copies the
hunt shape without the timeline does not satisfy MT-01.

## Run record shape — one record per division

Three records, one per division, each a single JSON file landed on main
by Pax (Route B) or by Milo (Route A), named so the division and the
check are in the filename, for example
`server/queue/livecam_records/mt01-staged-<division>-<date>.json`
(the exact filename is set at fire time; what matters is that all three
records exist and are findable from MILO_TEST_STATUS.md).

Each record contains, verbatim field names:

- `kind`: `"mt01-staged-agentic-loop"`.
- `check`: `"MT-01"`, `division`: `"vigiles"` | `"ignis"` | `"medicus"`.
- `main_tip`: the origin/main commit the run was fired from.
- `route`: `"A"` or `"B"`, plus who executed the live steps and who
  issued the verdict (Route B: Pax executed, Milo verdicts from the
  receipt; Route A: Milo executed and verdicts).
- `spend_usd`: actual spend for this record, or `0` with a note if the
  loop ran on staged frames with no model call; running total against
  the $10 cap is updated in MILO_TEST_STATUS.md at fire time.
- `frames`: one entry per staged frame, in patrol order, each with:
  `frame_id` (source path, e.g. the test-footage path or the scenario
  id), `review` (visible scene, division terms only),
  `judge` (`"flag"` or `"baseline"`), `judge_mode` (the mode string the
  judge actually ran under — recorded, never defaulted after the fact),
  `investigation` (`null` for baseline with reason `"no flag"`, or the
  confirm/downgrade outcome with evidence for a flag),
  `dispatch` (`null` for baseline/downgraded, or the `sim-` receipt
  string for a surviving flag, labelled SIMULATED).
- `timeline`: the five steps in order (patrol, review, judge,
  investigation, simulated dispatch), each with a started/completed
  marker. A step with no marker did not happen for this record.
- `outcome`: `"pass"` | `"fail"` | `"partial"` — pass only when every
  frame has every applicable step, every `judge_mode` is recorded, and
  every surviving flag holds a `sim-` receipt. Partial means the run
  stopped at the cap or on an error mid-loop; the record says where it
  stopped and what never ran.
- `failures`: every failure named, none hidden, including flags that
  ended without a receipt and frames whose judge step is missing a mode.

## Firing steps, by route (same steps, different hands)

Route B (the route that works once credits exist, no key movement):
Pax executes patrol -> review -> judge -> investigation -> simulated
dispatch over the staged frames, posts the three per-division records
plus the receipt, and Milo verdicts each record against the pass rules
above, in his own words, on room 1 and in MILO_TEST_STATUS.md.

Route A (only after Del places the key on Milo's VM): Milo executes the
same five steps himself, inside the cap, posts the three records, and
verdicts them the same way.

Either route: if the 402 is still present at fire time, the run does not
start; MT-01 stays BLOCKED and the attempt (not a result) is noted in
MILO_TEST_STATUS.md. If the cap is hit mid-run, the run stops, the
record is marked partial, and the tally is posted to room 1.

## What this prep does NOT claim

- No MT-01 run has happened. No frame has been judged under MT-01.
- No `sim-` receipt exists yet. No spend has occurred ($0 on this slice).
- No vigiles scenario JSON exists on main at prep time (see inputs).
- This file does not change the slice: MT-02..MT-08 keep their prep
  specs in MILO_TEST_PREP.md, and MT-08 gate duty stays with Milo's
  rust-work loop — this 5-minute job runs no gate-1.
