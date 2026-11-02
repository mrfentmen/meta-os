# EVAL BATCH 3 — the 15-frame Wikimedia pack (2026-11-02)

Ran by Pax at the boss's order ("more testing, proof with
percentage and picture with the model"). Method: the REAL pipeline
helper (spark_call.py assess) with each product's own prompt
profile, one Muse Spark 1.3 call per frame, on the 15-frame
Wikimedia Commons pack in test-footage/frames/ (manifest carries
the expected class per frame; all sources public/CC, nothing
staged). Raw model JSON kept with the run; adjudication by Pax
against the manifest, Batch-2 rules.

## Results

- MATCH 11/15 = 73%
- HELD 3/15 = 20% (unconfirmed, routed to human review — the
  system's designed safe outcome)
- MISS 1/15 = 7%
- True emergency frames caught: 5/5 = 100%
  (house fire, car fire, wildfire smoke, person on ground,
  collision scene — all named exactly)
- False emergency flags: 0/8 = 0%
  (steam, fog, dust, bench sleeper, sunbathing, yoga, curb rest,
  normal street — none declared an emergency)
- Category validity: 15/15 — every category the model used is a
  real category in that product's list.

## Per division

- Ignis 6: 5 MATCH, 1 HELD (dust plume -> indeterminate; it would
  not call dust smoke), 0 MISS.
- Medicus 6: 5 MATCH, 1 HELD (bench sleeper -> "person
  motionless": a true, weaker scene class, routed to review —
  not declared "person on ground"), 0 MISS.
- Vigiles 3: 1 MATCH, 1 HELD (altercation: saw physical contact,
  stayed indeterminate), 1 MISS.

## The miss, named

vigiles-crowd-1: a dense crowd from above. The model called it
"normal activity." Vigiles' category list has NO crowd class, so
it could never match — a taxonomy gap, not a perception failure:
it saw the scene and had no box to put it in. Fix is a category
decision for the boss (add "crowd gathered" to Vigiles), not a
model change.

## The box question (boss, 2026-11-02)

Checked in code: the model returns category + evidence TEXT,
never coordinates. There is NO tight outline box drawn around a
detected thing anywhere in the pipeline today. What exists:
(1) the full-frame evidence outline + verdict label — the demo
annotation on these pictures, drawn by the eval harness FROM the
verdict; (2) on flagged incidents the evidence lane CROPS around
a detected face for the BOLO record (a crop, not a drawn box).
A tight box is a build, not a claim: the model would have to
return a region and the surface draw it. On the ideas list as
a named item; nothing in the demo pictures fakes it.

## Cost + provenance

15 calls, est. $0.11 total (guardrail cumulative $1.204 -> $1.318,
est. not billing). Model returned: muse-spark-1.3 on every call.
Annotated pictures + contact sheet: Pax shot pack
demo-shots/imperium-eval/ (frames are the Wikimedia originals;
labels state expected vs model verdict per frame).
