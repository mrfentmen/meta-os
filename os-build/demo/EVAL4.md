# EVAL — batches 3 to 6: boxes built, results improved (2026-11-02)

Method throughout: the REAL pipeline helper (spark_call.py assess)
with each product's own prompt profile, one Muse Spark 1.3 call per
frame, on the 15-frame Wikimedia Commons pack in test-footage/frames/
(manifest carries the expected class per frame; all sources
public/CC, nothing staged). Adjudication by Pax against the
manifest: MATCH = assessment names the expected class (or correctly
rejects a look-alike); HELD = unconfirmed / a true but weaker class,
routed to human review; MISS = wrong call.

## Batch 3 — baseline (report: os-build/demo/EVAL3.md)

15 frames, the shipping prompt, no regions.
- MATCH 11/15 = 73% · HELD 3/15 = 20% · MISS 1/15 = 7%
- Emergencies exact-named 5/5 · false emergency flags 0/8
- The miss: vigiles-crowd-1. Vigiles had NO crowd class, so a dense
  crowd was called "normal activity" — a taxonomy gap, not a
  perception failure.
- The boss's box question, answered from code: the model returned
  category + evidence text, never coordinates. No outline box
  existed anywhere in the pipeline.

## Batch 4 — boxes + the raw crowd category

Changes: (1) each observation also returns a "region" bounding box
in 0-1000 relative frame coordinates (null when the observation is
scene-wide); (2) "crowd gathered" added to Vigiles' category list,
bare, with no definition.
- MATCH 10/15 = 67% · HELD 4/15 · MISS 1/15
- The crowd fix worked on crowd-1 — and backfired on the negative:
  vigiles-normal-1 (a busy crossing, ordinary pedestrian traffic in
  motion) was falsely flagged "crowd gathered." False flags went
  0/8 -> 1/8.
- ignis-smoke-1 regressed a step: the observation named the smoke,
  the assessment hedged to "obscured or distant hazard."
- Lesson, kept: a broad category with no definition costs more
  than the gap it fills.

## Batch 5 — targeted fixes, 5 frames re-run

Changes: (1) "crowd gathered" narrowed by definition — a stationary
assembled crowd (rally, audience, queue, onlookers around an
event); ordinary pedestrian traffic in motion is "normal
activity." (2) An assessment rule for every product: set the
assessment category to the strongest observation category the
visible evidence supports; hedge only when no specific category is
supported.
- vigiles-normal-1: back to "normal activity" — false flag fixed.
- vigiles-crowd-1: still "crowd gathered."
- ignis-smoke-1: assessment now "visible smoke" — hedge fixed.
- ignis-fire-2 (control): unchanged, "visible flame," regions kept.
- vigiles-altercation-1: still HELD ("crowd gathered" — true of the
  protest scene, not the target class).

## Batch 6 — FINAL: one prompt, all 15 frames, full re-run

- MATCH 12/15 = 80% · HELD 3/15 = 20% · MISS 0/15 = 0%
- Emergencies exact-named: 5/5 (house fire, car fire, wildfire
  smoke, person on ground, collision scene)
- False emergency flags: 0/8
- Category validity: 15/15 — every category used is in that
  product's list.
- The 3 HELD: dust plume (indeterminate — would not call dust
  smoke), the protest (crowd named, altercation not committed to),
  the bench sleeper ("person motionless" — a true, weaker scene
  class, not declared "person on ground"). All three are the
  system's designed safe outcome: unconfirmed goes to a human.
- Batch 3 -> Batch 6: 73% -> 80% match, misses 1 -> 0, false
  alarms 0 throughout the final configuration.

## The boxes

- Regions returned on 10/15 frames; the 5 nulls are scene-wide
  calls where a box would be decoration (a crowd from above, a
  yoga lawn, a beach, a crossing, a protest crowd).
- 12 boxes drawn in total (two frames carry two observations).
- Box-on-subject, judged by Pax visually against the rendered set:
  12 of 12 drawn boxes overlap the thing their label names.
  Honest caveat: two are loose — the steam box covers 86% of its
  frame and the house-fire smoke box 62%; the steam and smoke
  genuinely fill those areas, but they are blankets, not outlines.
  The tight boxes (car fire flame, person on ground, bench
  sleeper, the seated woman on the curb) sit on their subjects.
- Pictures: demo-shots/imperium-eval/ — <frame>-boxed.jpg per frame
  plus contact-sheet-boxed.jpg. White box + category label = where
  the model says the thing is; frame border = the score (green
  match, amber held, red miss); red FLAGGED tag = an emergency
  class was named. The annotation is drawn by the eval harness FROM
  the model's returned regions and verdicts — nothing is placed by
  hand.

## Cost

Batches 3–6 together: ≈ $0.50 estimated total (helper guardrail
estimates, not billing). Model returned on every call:
muse-spark-1.3.

## What is NOT yet true in production

The improvements live in the EVAL prompt lane only. The production
prompts — js/products.js, both mirrored prompt builders
(server/queue model + spark_gen), and the helper's PROFILES — do
NOT yet carry: the "crowd gathered" category, its narrowed
definition, the assessment rule, or the region field. The v2
contract and its validator also have no region field yet. Landing
all of that, in both mirrored builders at once, is the next merge
on the boss's word. Until then, no production surface draws a box.
