# Meta Ignis evaluation (Rowan's lane)

Scenario set, eval adapter, and runner for Meta Ignis
(FDNY-oriented fire and smoke hazard awareness), under the frozen
Meta Trio v2 contract (`../js/schema.js`, `FIRST_RESPONSE.md` section 4).

This mirrors the shape of Milo's Meta Sanitas harness
(`../sanitas/harness.mjs`) for the Ignis product, without touching
Milo's files: the same per-scenario record shape, the same metric
math (imported from the Sanitas harness, which is product-agnostic),
the same malformed-input containment. Product-specific evaluation
stays separate, per the trio lock (Rowan owns Meta Ignis).

## Files

- `scenarios.json` — 20 labeled scenarios with ground truth. Labels
  were authored in this file before any assessment source ran against
  them; the adapter reads it read-only and never mutates it. Covers
  all seven ignis categories: visible smoke, visible flame, no hazard
  visible, steam or fog, flame-like lighting, obscured or distant
  hazard, and indeterminate — plus confusable negatives: steam from a
  vent, morning fog, sunset glow on windows, orange neon, vehicle
  lights in rain.
- `adapter.mjs` — `validateIgnisScenarios` / `runIgnisEval` /
  `formatIgnisReport` / `assessViaModelAdapter` / `computeMetrics`
  (re-exported from the Sanitas harness). No dependencies, no network
  beyond what the server adapter itself gates.
- `baseline.mjs` — always-no-hazard baseline (`assessBaseline`).
  Predicts "no hazard visible" for every scene, fires no alert,
  performs no inspection. Mirrors `../sanitas/baseline.mjs`.
- `stub.mjs` — deterministic fixture source (`assessStub`). NOT a
  model: a table keyed by scenario_id, deliberately imperfect, with
  its misses documented in the file before any run. Mirrors
  `../sanitas/stub.mjs`.
- `run.mjs` — held-state runner. Prints the report for the wired
  source and says plainly that its numbers describe source
  availability, not model performance. With `--baseline`, runs the
  same scenario set against the baseline instead. With `--stub`,
  runs the same scenario set against the fixture stub, then the
  baseline, and prints the stub-vs-baseline comparison. With
  `--out <path>`, writes the run JSON; its source/generated labels
  are evidence-based (all-held refusal → held-state, any returned
  assessment → live-model), so a future live run is never mislabeled
  as held by a stale runner string.
- `report.mjs` — run-report renderer. Turns a `run.mjs --out` JSON
  file into the markdown format of the report trio, classifying the
  run by record evidence (all-held refusal → held-state, named
  fixture source → fixture, any returned assessment → live-model),
  never by its labels alone — so a live run renders as live even if
  it was produced by an older run.mjs. `--baseline <baseline-run.json>`
  adds the recall-and-category-accuracy verdict against the baseline, with signed deltas
  for both bar metrics.
  `--out` to a trio filename is refused: a live run belongs in its
  own `live-run-report.md`, never as an edit to the trio. With a baseline supplied, the
  comparison section renders signed recall and category-accuracy deltas (this run minus
  baseline, n/a when either side is n/a) alongside the beat-the-baseline verdict. It also
  renders a truth-vs-predicted category table and a
  confusable-negative breakdown (steam or fog / flame-like lighting
  predicted as an alert category), so alert-level metrics cannot hide
  systematic category swaps. A headline finding above the full table
  names the weakest truth category (lowest category-correct rate)
  and the most-confused truth -> predicted pair; when nothing was
  assessed it says so instead of naming a category, and ERROR counts
  as a failure, never as a confusion. It also names the slowest
  scenario by harness wall-clock latency, or says none was recorded
  when no record carries one, so the latency tail needs no scan of
  the per-scenario table. A per-category rate table right
  below the headline backs the weakest claim: one correct/total rate
  per truth category (unassessed records count as misses, matching
  category-accuracy semantics), with an assessed column so a
  held-state row of 0.000 reads as nothing assessed, not a measured
  zero — so the headline is checkable without counting the confusion
  matrix. The Misses section names each miss as truth -> predicted
  (ERROR with a no-assessment note for unassessed records), so a miss
  is diagnosable without cross-referencing the per-scenario table.
  A miss-pair counts table right after it aggregates those misses by
  truth -> predicted pair, most frequent first, so the dominant swap
  is visible without counting the Misses list; ERROR rows there are
  failures, not confusions. The per-scenario table carries each
  record's harness wall-clock latency (n/a when the record carries
  none), so a slow scenario is visible without the summary
  statistics, and flags a latency outlier (yes) when a scenario's
  latency is more than twice the run's median recorded latency;
  runs with fewer than two recorded latencies, or a median of zero,
  flag nothing rather than singling a scenario out on a zero baseline.
- `report.test.mjs` — renderer tests: fixture/held/live-shaped
  classification (including assessments beating a stale held label),
  baseline comparison verdicts, per-category confusion and
  confusable-negative breakdowns, misses detail and miss-pair counts,
  run-JSON validation, trio protection, and the CLI end to end.
- `adapter.test.mjs` — adapter tests: label loading, alert-definition
  consistency, metric math, alert-correctness logic,
  malformed-input containment, the held-state refusal, and the
  baseline's exact full-set numbers.
- `fixture-run-report.md` — the measured output of the last fixture
  run (`run.mjs --stub`), labeled as a fixture run.
- `held-state-run-report.md` — the measured output of the last
  held-state run (`run.mjs` with no flag), labeled as a held-state
  run: every scenario records the server adapter's refusal, and its
  numbers describe source availability, not model performance.
- `baseline-run-report.md` — the measured output of the last
  baseline run (`run.mjs --baseline`), labeled as a baseline run:
  the always-no-hazard source's scores, which are the bar a real
  source must beat, not model performance. With the fixture and
  held-state reports, this completes the report trio.

## The contract the adapter reads

One v2 assessment object per scenario, product `"ignis"`:

```json
{
  "product": "ignis",
  "timestamp": "ISO-8601",
  "observations": [{ "category": "...", "description": "...", "evidence": "...", "confidence": null }],
  "assessment": { "category": "...", "summary": "...", "uncertainty": ["..."], "requires_human_review": true },
  "processing": { "model": "...", "latency_ms": null }
}
```

An assessment "fires an alert" when `assessment.category` is
`visible smoke` or `visible flame`. `obscured or distant hazard`
never fires an alert on its own — a distant or partially hidden
hazard warrants human review, recorded separately — and neither do
`steam or fog`, `flame-like lighting`, `no hazard visible`, or
`indeterminate`. The label validator enforces this: a scenario whose
`alert_expected` contradicts the alert definition is rejected, not run.
Per-scenario records carry: scenario ID, expected condition,
ground-truth label, actual output, alert fired, alert correct,
evidence reference, latency (harness wall clock, never a reported
field), and any error.

## The wired source, and the Spark rule

`assessViaModelAdapter` delegates to the real server model adapter
(`../../server/model.mjs`). Del's ruling (2026-10-28): **Spark stays
off until the build is complete and Del green-lights the test phase.
No live calls during the build.** While that holds, the adapter throws
the held refusal and every scenario in a run records it as its error.
When the test phase lands the Spark transport, this same function
returns real assessments and the same harness scores them — no adapter
change, no new wiring, and no fabricated assessment in between.

## The baseline, and the bar it sets

`node eval/ignis/run.mjs --baseline` runs the 20 labeled scenarios
against `assessBaseline` and measures, honestly, what a do-nothing
source scores. Measured 2026-10-28 (fixture numbers, not model
performance):

- Sample size: 20 scenarios
- Confusion (alert): TP=0 FP=0 TN=15 FN=5
- Precision: n/a (no alert ever predicted; denominator zero)
- Recall: 0.000, false-positive rate: 0.000, false-negative rate: 1.000
- Category accuracy: 0.150 (the 3 "no hazard visible" scenarios only)
- Errors: 0

A future real source must beat this baseline on recall and category
accuracy to claim value. Beating it on precision alone proves
nothing, since the baseline never fires a false alarm by
construction — the same bar the Sanitas set applies to its
always-clean baseline. The full measured run, including the
baseline-vs-held distinction, is documented in
`baseline-run-report.md`, completing the report trio alongside the
fixture and held-state reports.

## The stub, and the comparison it enables

`node eval/ignis/run.mjs --stub` runs the 20 labeled scenarios
against `assessStub` and then the baseline on the same set.
Measured 2026-10-28 (fixture numbers, not model performance):

- Stub: TP=4 FP=3 TN=12 FN=1, precision 0.571, recall 0.800,
  false-positive rate 0.200, false-negative rate 0.200,
  category accuracy 0.700, errors 0
- Baseline: TP=0 FP=0 TN=15 FN=5, precision n/a, recall 0.000,
  false-positive rate 0.000, false-negative rate 1.000,
  category accuracy 0.150, errors 0

Documented stub misses: IGN-003 predicted indeterminate (a missed
alert); IGN-007, IGN-010, IGN-018 predicted an alert category on a
confusable negative (false alarms); IGN-012 and IGN-015 predicted a
wrong non-alert category. The stub beats the baseline on recall
(0.800 vs 0.000) and category accuracy (0.700 vs 0.150) — the
comparison exercises the harness on a source that sometimes alerts
and sometimes misses, which the do-nothing baseline cannot do.
Neither number describes a model.

## The held-state run, and why it is not the baseline

`node eval/ignis/run.mjs` (no flag) runs the 20 labeled scenarios
against the real server model adapter. Measured 2026-10-28 (held
numbers, not model performance):

- Held: TP=0 FP=0 TN=15 FN=5, precision n/a, recall 0.000,
  false-positive rate 0.000, false-negative rate 1.000,
  category accuracy 0.000, errors 20 (every scenario, same refusal)

The confusion counts match the baseline's, but the runs are not
equivalent: the baseline predicts "no hazard visible" everywhere
(category accuracy 0.150, 0 errors), while the held run predicts
nothing (category accuracy 0.000, 20 errors). The held run proves
the default runner refuses honestly under the Spark hold instead
of fabricating assessments; it proves nothing about detection.

## Run it

```sh
node eval/ignis/run.mjs
node eval/ignis/run.mjs --baseline
node eval/ignis/run.mjs --stub
node eval/ignis/run.mjs --out eval/ignis/last-run.json
npm test   # runs the whole repo suite, including eval/ignis/adapter.test.mjs and report.test.mjs
```

## Reporting a run (the test-phase path, built now, no live call)

When Del green-lights the test phase, a live run is reported in two
steps, with no new wiring and no edit to the trio:

```sh
node eval/ignis/run.mjs --out eval/ignis/live-run.json
node eval/ignis/run.mjs --baseline --out eval/ignis/baseline-run.json
node eval/ignis/report.mjs eval/ignis/live-run.json \
  --baseline eval/ignis/baseline-run.json \
  --out eval/ignis/live-run-report.md
```

The renderer classifies by record evidence and refuses a trio
filename as `--out`, so the live numbers land in their own file
with the baseline verdict (recall and category accuracy, never
precision alone) attached. Until the test phase, the same command
on a held `--out` JSON renders a held-state report, not a live one
— the classification, not the filename, decides what a run is.

## What is unproven (do not claim otherwise)

- Live Spark: no live model call has been made by this lane; the
  held-state run records refusals, not assessments.
- Real-hardware camera: scenarios here are labeled descriptions run
  against the server adapter, not camera frames.
- Real imagery: no photographs are bundled; the scenario set describes
  scenes to be sourced as prerecorded footage or safe visual
  demonstrations before a live evaluation run. Never create a real
  fire to test this product.
