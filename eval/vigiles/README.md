# Meta Vigiles evaluation (Hana's lane, applications drive)

Scenario set, eval adapter, and runner for Meta Vigiles
(NYPD-oriented visual incident awareness), under the frozen
Meta Trio v2 contract (`../../js/schema.js`, `FIRST_RESPONSE.md`
section 4).

Until this slice, `eval/vigiles/` shipped only `scenarios.json`
and no harness — unlike `eval/ignis` and `eval/medicus`, which
each have a full runner. This slice mirrors the shape of the
Ignis adapter (`../ignis/adapter.mjs`) for the Vigiles product,
without touching any Ignis or Medicus file: the same
per-scenario record shape, the same metric math (from the
shared `../shared/metrics.mjs`), the same malformed-input
containment (a source that throws or returns an invalid shape
is recorded as an error for that scenario only; the run
continues).

## Files

- `scenarios.json` — the fixture set, unchanged by this slice:
  3 frame-anchored rows (VIG-F01..F03), every row anchored to a
  committed frame in `test-footage/frames/` and to a recorded
  verdict in `os-build/demo/EVAL4.md` (batch 6, the final full
  re-run). Nothing in it is invented: a frame with no manifest
  entry and no EVAL4 verdict is NOT a ground-truth row and is
  listed under `unlabelled_frames` instead. Scene awareness
  only: labels describe what is visible, never a diagnosis,
  cause, severity, or triage decision.
- `adapter.mjs` — `validateVigilesScenarios` / `runVigilesEval` /
  `formatVigilesReport` / `assessViaModelAdapter` /
  `computeMetrics` (re-exported from `../shared/metrics.mjs`).
  No dependencies, no network beyond what the server adapter
  itself gates.
- `baseline.mjs` — always-normal baseline (`assessBaseline`).
  Predicts "normal activity" for every scene, fires no alert,
  performs no scene review. Mirrors `../medicus/baseline.mjs`.
- `stub.mjs` — deterministic fixture source (`assessStub`). NOT
  a model: a table keyed by scenario_id reproducing the recorded
  EVAL4 batch-6 verdicts (2 MATCH, 1 HELD, 0 MISS), with its
  behaviour documented in the file before any run. Mirrors
  `../ignis/stub.mjs`.
- `run.mjs` — runner: `node eval/vigiles/run.mjs [--out <path>]
  [--baseline | --stub]`. Default source is the wired server
  model adapter; `--baseline` runs the baseline; `--stub` runs
  the stub plus the baseline and prints the comparison.
- `adapter.test.mjs` — 12 tests, wired into `npm test`. No
  network, no model calls.
- `baseline-run-report.md` — the measured baseline run.

## Two fixture facts the adapter honours

1. `ground_truth_label` is NOT required to be a
   `js/products.js` vigiles category. VIG-F01's label is "crowd
   gathered in a public space" while its products category is
   "crowd gathered"; VIG-F03's label is "public disturbance /
   altercation" and its products category is null — the fixture
   itself says that mapping is NOT decided here, it is a
   taxonomy call for Pax. The validator therefore requires
   `category_in_products_js` to be present and either a vigiles
   category or null, and never requires the label itself to be
   one.
2. Category correctness is decided per row: when
   `category_in_products_js` is a string, it is
   (actual === that string); when it is null, it is null
   ("undecided") and the row is excluded from the decided-only
   category accuracy the report prints. An undecided row is
   never scored as a miss. The shared metric still counts it
   as not-correct over all rows, so the report prints both
   numbers and says which is which.

## Alert definition

An assessment "fires an alert" when its assessment.category is
one of `VIGILES_ALERT_CATEGORIES` — the red tier in
`js/command-loop.js`: physical contact, person down, possible
altercation. "crowd gathered" on its own does NOT fire (EVAL4's
emergency list names no vigiles crowd, and the fixture marks
VIG-F01 alert_expected false). "normal activity" and
"indeterminate" never fire an alert.

## The bar the baseline sets

Measured by `node eval/vigiles/run.mjs --baseline` (see
`baseline-run-report.md`): TP=0 FP=0 TN=2 FN=1, precision n/a
(no alert ever predicted), recall 0, false-positive rate 0,
false-negative rate 1, shared category accuracy 0.333,
decided-row category accuracy 0.500 (1/2). A future real
source must beat this baseline on recall and decided-row
category accuracy to claim value. Beating it on precision
alone proves nothing, since it never fires a false alarm by
construction.

## What this slice does NOT do

- It does not wire `imperium-patrol` in `agents/registry.json`:
  that entry is a DRAFT whose own reason says "Imperium lives
  outside this repo; no real command can be named here". Naming
  a command would invent one, so the draft stays a draft.
- It does not decide VIG-F03's products category: that mapping
  stays Pax's taxonomy call, and the harness scores the row as
  undecided until Pax decides it.
- It does not run a live model: the wired run records the
  server adapter's held refusal for all 3 rows (verified this
  run). When the test phase lands the Spark transport, the same
  runner scores real assessments with no adapter change.
