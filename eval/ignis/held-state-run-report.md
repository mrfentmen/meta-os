# Meta Ignis held-state run report

Measured by `node eval/ignis/run.mjs` (no flag) on 2026-10-28, from
`eval/ignis/scenarios.json` (20 labeled scenarios, ground truth
authored before any source ran). This is a HELD-STATE run: the wired
source is the real server model adapter (`server/model.mjs`), and
while Del's Spark ruling holds it refuses every call instead of
assessing. No number here describes model performance, and none may
be quoted as such — these numbers describe source availability.

## Held source (`server model adapter`, Spark held)

- Sample size: 20 scenarios
- Confusion (alert): TP=0 FP=0 TN=15 FN=5
- Precision: n/a (no alert ever predicted; denominator zero)
- Recall: 0.000
- False-positive rate: 0.000
- False-negative rate: 1.000
- Category accuracy: 0.000
- Latency (harness wall clock): mean 0.0 ms, median 0 ms, max 0 ms
  (refusal-return time only; a refused call is not a model call,
  and this figure varies run to run at sub-millisecond scale)
- Errors: 20 — every scenario, IGN-001 through IGN-020, with the
  identical refusal:

  > Live model calls are held: Spark stays off until the build is
  > complete and Del green-lights the test phase.

## Held is not the baseline

The confusion counts look identical to the baseline's (TP=0 FP=0
TN=15 FN=5), and that resemblance is a trap. The baseline
(`ignis-baseline-always-no-hazard`) actually predicts "no hazard
visible" for every scene: it scores category accuracy 0.150 (the 3
"no hazard visible" scenarios) with 0 errors. The held run predicts
nothing at all: category accuracy 0.000 with 20 errors. The
baseline's numbers are a bar a real source must beat; the held
run's numbers are a receipt that no source was available. Do not
substitute one for the other, and do not read the held run's
recall 0.000 or false-negative rate 1.000 as a model failing to
detect fire — no model ran.

## What this run does not prove

Live backend, live Spark, real-hardware camera, and real imagery are
all unproven, exactly as in the fixture report. This run adds one
proven fact the fixture run cannot: the default runner, pointed at
the real server adapter under the Spark hold, refuses honestly on
all 20 scenarios instead of fabricating assessments to fill the
gap. When Del green-lights the test phase and the Spark transport
lands, this same runner scores real assessments with no adapter
change — report those numbers separately as live numbers, never as
an edit to this held-state record.
