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
- `run.mjs` — held-state runner. Prints the report for the wired
  source and says plainly that its numbers describe source
  availability, not model performance.
- `adapter.test.mjs` — adapter tests: label loading, alert-definition
  consistency, metric math, alert-correctness logic,
  malformed-input containment, and the held-state refusal.

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

## Run it

```sh
node eval/ignis/run.mjs
node eval/ignis/run.mjs --out eval/ignis/last-run.json
npm test   # runs the whole repo suite, including eval/ignis/adapter.test.mjs
```

## What is unproven (do not claim otherwise)

- Live Spark: no live model call has been made by this lane; the
  held-state run records refusals, not assessments.
- Real-hardware camera: scenarios here are labeled descriptions run
  against the server adapter, not camera frames.
- Real imagery: no photographs are bundled; the scenario set describes
  scenes to be sourced as prerecorded footage or safe visual
  demonstrations before a live evaluation run. Never create a real
  fire to test this product.
