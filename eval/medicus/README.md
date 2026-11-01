# Meta Medicus evaluation (Agent 3: Milo)

Scenario sets, ground truth, and eval harness for Meta Medicus
(FDNY EMS-oriented scene awareness), under the frozen
Meta Trio v2 contract (`../js/schema.js`, `FIRST_RESPONSE.md` section 4).

Default set: the current `js/products.js` taxonomy (14 categories,
12 alert categories) in `scenarios-current.json` (27 scenarios).
The frozen benchmark (`scenarios.json`, 20 scenarios, alert only for
the five original categories) still runs as legacy with
`run.mjs --legacy`.

## Files

- `scenarios-current.json` — the default set: 27 labeled scenarios
  with ground truth, covering all 14 medicus categories in
  `js/products.js` (the frozen 20 plus one scenario per EMS
  scene-type category: person down in roadway, person slumped in
  vehicle, person in or near water, person trapped or pinned,
  bystander aid in progress, multi-person incident scene, blood
  visible at scene). Labels were authored in this file before any
  assessment source ran against them; the harness reads it read-only
  and never mutates it.
- `scenarios.json` — the frozen benchmark: 20 labeled scenarios
  with ground truth. Covers all seven directive scenario groups
  (person on ground, crowd gathered around a person, vehicle
  collision scene, blocked crew access, person motionless, normal
  activity, poor visibility / ambiguous conditions) plus the
  look-alike class that must not fire an alert: sleeping on a bench,
  sunbathing, yoga or stretching, sitting on a curb resting, CPR
  training manikin. Still runnable as legacy with
  `run.mjs --legacy`.
- `harness.mjs` — `runEval` / `computeMetrics` / `formatReport` /
  `validateScenarios`. No dependencies, no network. `runEval` takes
  an optional `{ alertCategories }`: the default is the current
  taxonomy's 12 alert categories; pass
  `ALERT_CATEGORIES_LEGACY` for the frozen five-category
  definition.
- `stub.mjs` — deterministic fixture assessment source. NOT a model.
  Its intentional errors are documented in its header; its numbers are
  fixture numbers, not model performance. The current-set scenarios
  (MED-021..027) are all answered with their labeled category.
- `baseline.mjs` — always-normal baseline. Predicts "normal activity"
  for every scene and fires no alert, so any real source must beat its
  recall (0) and category accuracy (0.296 on the current 27-scenario
  set; 0.400 on the legacy 20-scenario set) to claim value.
- `run.mjs` — fixture runner. Prints the stub report, the baseline
  report, and the comparison. Default set is
  `scenarios-current.json`; with `--legacy`, runs the frozen
  `scenarios.json` set with the frozen alert definition instead.
- `harness.test.mjs` — harness tests: label loading, metric math,
  alert-correctness logic, malformed-input containment.
- `fixture-run-report.md` — the measured output of the last fixture
  run on the frozen legacy set, labeled as a fixture run.

## The contract the harness reads

One v2 assessment object per scenario, product `"medicus"`:

```json
{
  "product": "medicus",
  "timestamp": "ISO-8601",
  "observations": [{ "category": "...", "description": "...", "evidence": "...", "confidence": null }],
  "assessment": { "category": "...", "summary": "...", "uncertainty": ["..."], "requires_human_review": true },
  "processing": { "model": "...", "latency_ms": null }
}
```

An assessment "fires an alert" when `assessment.category` is one of
the current taxonomy's 12 alert categories: `person on ground`,
`crowd gathered around a person`, `vehicle collision scene`,
`blocked crew access`, `person motionless`, `person down in
roadway`, `person slumped in vehicle`, `person in or near water`,
`person trapped or pinned`, `bystander aid in progress`,
`multi-person incident scene`, `blood visible at scene`.
`normal activity` and `indeterminate` never fire an alert; they
warrant human review where confusable or unclear, recorded separately. Under the legacy frozen definition only the five original
categories fire an alert. Per-scenario records carry:
scenario ID, expected condition, ground-truth label, actual output,
alert fired, alert correct, evidence reference, latency (harness wall
clock, never a reported field), and any error.

## Run it

```sh
node eval/medicus/run.mjs
node eval/medicus/run.mjs --legacy   # frozen benchmark set
node eval/medicus/run.mjs --out eval/medicus/last-run.json
npm test   # runs tests/ui.test.mjs and eval/medicus/harness.test.mjs
```

Current-set fixture numbers (measured 2026-10-31, fixture numbers,
not model performance): stub TP=13 FP=3 TN=10 FN=1, precision 0.813,
recall 0.929, category accuracy 0.778 (21/27); baseline TP=0 FP=0
TN=13 FN=14, recall 0.000, category accuracy 0.296 (8/27). Legacy
frozen-set numbers: stub TP=6 FP=3 TN=10 FN=1, precision 0.667,
recall 0.857, category accuracy 0.700 (14/20); baseline TP=0 FP=0
TN=13 FN=7, recall 0.000, category accuracy 0.400 (8/20).

## Plugging in Rowan's /api/assess

The server endpoint exists in-repo (Rowan cd1efa9, live calls held).
When Del green-lights the test phase,
replace the assess function passed to `runEval` with an adapter around
`assessFrame` from `js/client.js` (POST `{product, timestamp, image}`).
Until then, Spark stays OFF: no live model calls, no API key, no
network model access anywhere in this directory.

## What is unproven (do not claim otherwise)

- Live backend: `/api/assess` exists in-repo (Rowan cd1efa9) with live
  calls held; no running instance has been proven live.
- Live Spark: no live model call has been made by this lane; Spark
  runs only after Del green-lights the test phase.
- Real-hardware camera: scenarios here are labeled descriptions run
  against fixtures, not camera frames.
- Real imagery: no photographs are bundled; the scenario set describes
  scenes to be sourced (public clips, corner/overhead angle, per the
  standing ruling) before a live evaluation run.
- Medicus scope: scene awareness only. No diagnosis, no cause, no
  severity or triage call, no treatment language anywhere in
  categories, prompts, UI copy, or demo material.

## Contract notes

- The harness follows the doc over the tree where they differ. The
  frozen v2 shape in `FIRST_RESPONSE.md` section 4 and `js/schema.js`
  agree, and the harness reads exactly that shape with product
  `"medicus"`.
- Input-mode wording differs and is NOT a contract shape: the first
  response describes Medicus input as still images, and the top README
  documents still-image input as the Medicus demo input, while
  `js/products.js` inputGuidance still says live camera. The harness
  is input-agnostic (it scores assessments for labeled scenarios), so
  this does not affect any result; the wording should be reconciled
  by Agent 4, not by this lane.
- Scope note: the first response assigns Agent 3 all three products,
  but this directory is Medicus only, per the trio lock (Milo owns
  Meta Medicus). Vigiles and Ignis sets live with their own lanes.
