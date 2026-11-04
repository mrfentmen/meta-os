# Meta Vigiles baseline run report

Measured by `node eval/vigiles/run.mjs --baseline` on 2026-11-03, from
`eval/vigiles/scenarios.json` (3 frame-anchored rows, ground truth
from `test-footage/MANIFEST.md` and recorded verdicts in
`os-build/demo/EVAL4.md` batch 6). This is a BASELINE run: the source
is the always-normal baseline (`baseline.mjs`), a local stand-in
that predicts "normal activity" for every scene, fires no alert,
and performs no scene review. No number here describes model
performance, and none may be quoted as such — these numbers are
the bar a real source must beat.

## Baseline source (`vigiles-baseline-always-normal`)

- Sample size: 3 scenarios
- Confusion (alert): TP=0 FP=0 TN=2 FN=1
- Precision: n/a (no alert ever predicted; denominator zero)
- Recall: 0.000
- False-positive rate: 0.000
- False-negative rate: 1.000
- Category accuracy (shared metric, all rows): 0.333 (1/3)
- Category accuracy (decided rows only): 0.500 (1/2 decided rows)
- Category-undecided rows: VIG-F03 (taxonomy call for Pax, never
  scored as a miss)
- Latency (harness wall clock): mean 0.0 ms, median 0 ms, max 0 ms
  (baseline-local only; a baseline call is not a model call)
- Errors: 0

Per-scenario: VIG-F01 predicted "normal activity" where the
products category is "crowd gathered" (alert-correct, category
wrong); VIG-F02 predicted "normal activity" where the truth is
"normal activity" (correct on both); VIG-F03 predicted "normal
activity" where an alert was expected (false negative by
construction) and its category is undecided, so it counts in
neither decided-row numerator nor denominator.

The single false negative is the single alert-expected row
(VIG-F03) — every real alert in the set is missed by
construction. The 2 true negatives include both non-alert rows,
but only 1 of them is also category-correct. Alert-correct is
not category-correct: the baseline is right about "no alert"
on the crowd row while being wrong about what is actually in
the scene.

## The bar it sets

A future real source must beat this baseline on recall and
decided-row category accuracy to claim value. Beating it on
precision alone proves nothing, since it never fires a false
alarm by construction. The stub (`run.mjs --stub`, reproducing
EVAL4 batch 6) already beats it on decided-row category
accuracy (1.000, 2/2) while matching it on recall (0.000) —
because the stub, like batch 6, names "crowd gathered" on the
altercation row without committing to the altercation class,
so the alert still does not fire. That is the gap a real
source must close: committing to the altercation class on
VIG-F03, once Pax settles its products category.
