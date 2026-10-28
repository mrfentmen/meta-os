# Meta Ignis baseline run report

Measured by `node eval/ignis/run.mjs --baseline` on 2026-10-28, from
`eval/ignis/scenarios.json` (20 labeled scenarios, ground truth
authored before any source ran). This is a BASELINE run: the source
is the always-no-hazard baseline (`baseline.mjs`), a local stand-in
that predicts "no hazard visible" for every scene, fires no alert,
and performs no inspection. No number here describes model
performance, and none may be quoted as such — these numbers are
the bar a real source must beat.

## Baseline source (`ignis-baseline-always-no-hazard`)

- Sample size: 20 scenarios
- Confusion (alert): TP=0 FP=0 TN=15 FN=5
- Precision: n/a (no alert ever predicted; denominator zero)
- Recall: 0.000
- False-positive rate: 0.000
- False-negative rate: 1.000
- Category accuracy: 0.150 (the 3 "no hazard visible" scenarios:
  IGN-005, IGN-006, IGN-017)
- Latency (harness wall clock): mean 0.1 ms, median 0 ms, max 1 ms
  (baseline-local only; a baseline call is not a model call)
- Errors: 0

The 5 false negatives are the 5 alert-expected scenarios
(IGN-001, IGN-002, IGN-003, IGN-004, IGN-016) — every real hazard in
the set is missed by construction. The 15 true negatives include
all 15 non-alert scenarios, but only 3 of them are also category
correct; the other 12 predicted "no hazard visible" where the truth
was steam or fog, flame-like lighting, obscured or distant hazard,
or indeterminate. Alert-correct is not category-correct: the
baseline is right about "no alert" on confusable negatives while
being wrong about what is actually in the scene.

## The bar it sets

A future real source must beat this baseline on recall and
category accuracy to claim value. Beating it on precision alone
proves nothing, since the baseline never fires a false alarm by
construction — its precision is vacuous, not perfect. A source
that merely alerts less is not better; a source that catches the
5 missed hazards without flooding the 15 negatives is.

## Baseline is not the held run

The confusion counts look identical to the held-state run's
(TP=0 FP=0 TN=15 FN=5), and that resemblance is a trap, in the
other direction from the held report's warning. The held run
predicts nothing at all (category accuracy 0.000, 20 errors) —
a receipt that no source was available. The baseline predicts
"no hazard visible" everywhere (category accuracy 0.150, 0
errors) — a floor a real source must clear. Do not substitute
one for the other: the held run proves honest refusal, the
baseline run proves what doing nothing scores.

## What this run does not prove

Live backend, live Spark, real-hardware camera, and real imagery
are all unproven, exactly as in the fixture and held-state
reports. Re-run this harness against Rowan's `/api/assess` only
after Del green-lights the test phase, and report those numbers
separately as live numbers, never as an edit to this baseline
record.
