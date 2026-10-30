# Meta Medicus fixture run report

Measured by `node eval/medicus/run.mjs` on 2026-10-30, from
`eval/medicus/scenarios.json` (20 labeled scenarios, ground truth
authored before any source ran). This is a FIXTURE run: both sources
are local stand-ins, not models. No number here describes live model
performance, and none may be quoted as such.

## Stub source (`medicus-stub-fixture`)

- Sample size: 20 scenarios
- Confusion (alert): TP=6 FP=3 TN=10 FN=1
- Precision: 0.667
- Recall: 0.857
- False-positive rate: 0.231
- False-negative rate: 0.143
- Category accuracy: 0.700
- Latency (harness wall clock): mean 0.1 ms, median 0 ms, max 1 ms
  (stub-local only; a stub call is not a model call)
- Errors: 0

Known stub misses (documented in `stub.mjs` before the run):
MED-002 predicted indeterminate (miss); MED-010, MED-012, MED-013
predicted person on ground (false alarms on confusable negatives);
MED-016 and MED-019 predicted normal activity (wrong category, no alert).

## Baseline source (`medicus-baseline-always-normal`)

- Sample size: 20 scenarios
- Confusion (alert): TP=0 FP=0 TN=13 FN=7
- Precision: n/a (no alert ever predicted; denominator zero)
- Recall: 0.000
- False-positive rate: 0.000
- False-negative rate: 1.000
- Category accuracy: 0.400
- Latency (harness wall clock): mean 0.0 ms, median 0 ms, max 0 ms
- Errors: 0

## Comparison

On the same ground truth and harness, the stub beats the baseline on
recall (0.857 vs 0.000) and category accuracy (0.700 vs 0.400), while
the baseline's precision is vacuous (it never predicts an alert).
A future real source must beat the baseline on recall and category
accuracy to claim value; beating it on precision alone proves
nothing, since the baseline never fires a false alarm by construction.

## What this run does not prove

Live backend, live Spark, real-hardware camera, and real imagery are
all unproven. Re-run this harness against Rowan's `/api/assess` only
after Del green-lights the test phase, and report those numbers
separately as live numbers.
