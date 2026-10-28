# Meta Sanitas evaluation (Agent 3: Milo)

Scenario sets, ground truth, and eval harness for Meta Sanitas
(Department of Sanitation-oriented visual inspection), under the frozen
Meta Trio v2 contract (`../js/schema.js`, `FIRST_RESPONSE.md` section 4).

## Files

- `scenarios.json` — 20 labeled scenarios with ground truth. Labels
  were authored in this file before any assessment source ran against
  them; the harness reads it read-only and never mutates it. Covers all
  seven directive scenario groups (overflowing bin, sidewalk waste,
  blocked path, clean sidewalk, normal collection area, look-alike
  objects, poor visibility / ambiguous conditions) plus confusable
  negatives: fallen leaves, tied collection bags, a lone box, a lone
  chair, a cart with belongings, stains and shadows.
- `harness.mjs` — `runEval` / `computeMetrics` / `formatReport` /
  `validateScenarios`. No dependencies, no network.
- `stub.mjs` — deterministic fixture assessment source. NOT a model.
  Its intentional errors are documented in its header; its numbers are
  fixture numbers, not model performance.
- `baseline.mjs` — always-clean baseline. Predicts "clean area" for
  every scene and fires no alert, so any real source must beat its
  recall (0) and category accuracy (0.150 on this set) to claim value.
- `run.mjs` — fixture runner. Prints the stub report, the baseline
  report, and the comparison.
- `harness.test.mjs` — harness tests: label loading, metric math,
  alert-correctness logic, malformed-input containment.
- `fixture-run-report.md` — the measured output of the last fixture
  run, labeled as a fixture run.

## The contract the harness reads

One v2 assessment object per scenario, product `"sanitas"`:

```json
{
  "product": "sanitas",
  "timestamp": "ISO-8601",
  "observations": [{ "category": "...", "description": "...", "evidence": "...", "confidence": null }],
  "assessment": { "category": "...", "summary": "...", "uncertainty": ["..."], "requires_human_review": true },
  "processing": { "model": "...", "latency_ms": null }
}
```

An assessment "fires an alert" when `assessment.category` is one of
`overflowing bin`, `waste accumulation`, `blocked pedestrian path`.
`ambiguous object` and `indeterminate` never fire an alert; they
warrant human review, recorded separately. Per-scenario records carry:
scenario ID, expected condition, ground-truth label, actual output,
alert fired, alert correct, evidence reference, latency (harness wall
clock, never a reported field), and any error.

## Run it

```sh
node eval/sanitas/run.mjs
node eval/sanitas/run.mjs --out eval/sanitas/last-run.json
npm test   # runs tests/ui.test.mjs and eval/sanitas/harness.test.mjs
```

## Plugging in Rowan's /api/assess later

When the server endpoint exists and Del green-lights the test phase,
replace the assess function passed to `runEval` with an adapter around
`assessFrame` from `js/client.js` (POST `{product, timestamp, image}`).
Until then, Spark stays OFF: no live model calls, no API key, no
network model access anywhere in this directory.

## What is unproven (do not claim otherwise)

- Live backend: `/api/assess` does not exist yet in this repo.
- Live Spark: no live model call has been made by this lane; Spark
  runs only after Del green-lights the test phase.
- Real-hardware camera: scenarios here are labeled descriptions run
  against fixtures, not camera frames.
- Real imagery: no photographs are bundled; the scenario set describes
  scenes to be photographed or sourced before a live evaluation run.

## Contract notes

- The harness follows the doc over the tree where they differ. The
  frozen v2 shape in `FIRST_RESPONSE.md` section 4 and `js/schema.js`
  agree, and the harness reads exactly that shape with product
  `"sanitas"`.
- Input-mode wording differs and is NOT a contract shape: the first
  response describes Sanitas input as still images, and the top README
  documents still-image input as the Sanitas demo input, while
  `js/products.js` inputGuidance still says live camera. The harness
  is input-agnostic (it scores assessments for labeled scenarios), so
  this does not affect any result; the wording should be reconciled
  by Agent 4, not by this lane.
- Scope note: the first response assigns Agent 3 all three products,
  but this directory is Sanitas only, per the trio lock (Milo owns
  Meta Sanitas). Vigiles and Ignis sets live with their own lanes.
