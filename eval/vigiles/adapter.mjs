// Meta Vigiles evaluation adapter (Hana's lane, applications drive).
//
// eval/vigiles/ shipped with only scenarios.json: a frame-anchored
// fixture set (3 vigiles frames, ground truth from
// test-footage/MANIFEST.md and recorded verdicts in
// os-build/demo/EVAL4.md batch 6) and no runner, adapter, baseline,
// or report — unlike eval/ignis and eval/medicus, which each have a
// full harness. This file closes that gap, mirroring the ignis
// adapter's shape (same per-scenario record shape, same metric math
// from eval/shared/metrics.mjs, same malformed-input containment)
// without touching any ignis or medicus file.
//
// Two fixture facts shape the validation, and both are deliberate:
//
// 1. ground_truth_label is NOT required to be a js/products.js
//    vigiles category. VIG-F01's label is "crowd gathered in a
//    public space" while its products category is "crowd gathered";
//    VIG-F03's label is "public disturbance / altercation" and its
//    products category is null — the fixture itself says the mapping
//    is NOT decided here, it is a taxonomy call for Pax. Requiring
//    label membership would fail the fixture by design.
// 2. Category correctness is therefore decided per row: when
//    category_in_products_js is a string, category_correct is
//    (actual === that string); when it is null, category_correct is
//    null ("undecided") and the row is excluded from the decided-only
//    category accuracy the report prints alongside the shared metric
//    (which counts an undecided row as not-correct, denominator all
//    rows). An undecided row is never scored as a miss.
//
// Alert definition: an assessment "fires an alert" when its
// assessment.category is one of VIGILES_ALERT_CATEGORIES — the red
// tier in js/command-loop.js (physical contact, person down,
// possible altercation). "crowd gathered" on its own does NOT fire:
// EVAL4's emergency list names no vigiles crowd, and the fixture
// marks VIG-F01 alert_expected false. "normal activity" and
// "indeterminate" never fire an alert.
//
// Assessment source contract: an async function assess(scenario)
// that returns one Meta Trio v2 assessment object (js/schema.js)
// for the scenario, or throws. Every returned object is validated
// against the frozen v2 contract with product "vigiles".
//
// The wired source, assessViaModelAdapter, delegates to the real
// server model adapter (server/model.mjs). That adapter enforces
// the Spark gate itself, so with the gate shut every scenario in a
// run records the held refusal as its error — no assessment is
// fabricated, and the report describes source availability, not
// model performance. When the test phase lands the Spark transport,
// this same function returns real assessments with no adapter
// change. No live model call happens from this file itself.

import { validateAssessment } from "../../js/schema.js";
import { PRODUCT_BY_ID } from "../../js/products.js";
import { assessWithModel } from "../../server/model.mjs";
import { computeMetrics } from "../shared/metrics.mjs";

export { computeMetrics };

export const VIGILES_ALERT_CATEGORIES = [
  "physical contact",
  "person down",
  "possible altercation",
];

const VIGILES_CATEGORIES = PRODUCT_BY_ID.vigiles.categories;

export function validateVigilesScenarios(scenarios, options = {}) {
  const alertCategories = options.alertCategories ?? VIGILES_ALERT_CATEGORIES;
  const errors = [];
  if (!Array.isArray(scenarios) || scenarios.length === 0) {
    return ["scenario set is missing or empty"];
  }
  const seen = new Set();
  scenarios.forEach((s, i) => {
    const prefix = `scenarios[${i}]`;
    if (!s || typeof s !== "object" || Array.isArray(s)) {
      errors.push(`${prefix}: not an object`);
      return;
    }
    if (typeof s.scenario_id !== "string" || s.scenario_id.length === 0) {
      errors.push(`${prefix}.scenario_id: missing or not a string`);
    } else if (seen.has(s.scenario_id)) {
      errors.push(`${prefix}.scenario_id: duplicate "${s.scenario_id}"`);
    } else {
      seen.add(s.scenario_id);
    }
    if (typeof s.expected_observable_condition !== "string" || s.expected_observable_condition.length === 0) {
      errors.push(`${prefix}.expected_observable_condition: missing or not a string`);
    }
    if (typeof s.ground_truth_label !== "string" || s.ground_truth_label.length === 0) {
      errors.push(`${prefix}.ground_truth_label: missing or not a string`);
    }
    // category_in_products_js must be present: a string in the
    // vigiles taxonomy, or null meaning "mapping undecided" (Pax's
    // taxonomy call). Absent or any other type is a fixture error.
    if (!("category_in_products_js" in s)) {
      errors.push(`${prefix}.category_in_products_js: missing (must be a vigiles category or null for undecided)`);
    } else if (s.category_in_products_js !== null && !VIGILES_CATEGORIES.includes(s.category_in_products_js)) {
      errors.push(
        `${prefix}.category_in_products_js: "${s.category_in_products_js}" is not a vigiles category ` +
          `(${VIGILES_CATEGORIES.join(", ")})`,
      );
    }
    if (typeof s.alert_expected !== "boolean") {
      errors.push(`${prefix}.alert_expected: missing or not a boolean`);
    } else if (
      typeof s.category_in_products_js === "string" &&
      s.alert_expected !== alertCategories.includes(s.category_in_products_js)
    ) {
      errors.push(
        `${prefix}.alert_expected: ${s.alert_expected} contradicts the alert definition ` +
          `(alert only for ${alertCategories.join(", ")})`,
      );
    }
    if (typeof s.review_expected !== "boolean") {
      errors.push(`${prefix}.review_expected: missing or not a boolean`);
    }
  });
  return errors;
}

export async function runVigilesEval(scenarios, assess, options = {}) {
  const alertCategories = options.alertCategories ?? VIGILES_ALERT_CATEGORIES;
  const labelErrors = validateVigilesScenarios(scenarios, { alertCategories });
  if (labelErrors.length > 0) {
    throw new Error(`invalid scenario set: ${labelErrors.join("; ")}`);
  }
  const records = [];
  for (const scenario of scenarios) {
    const started = Date.now();
    let assessment = null;
    let error = null;
    try {
      assessment = await assess(scenario);
      const result = validateAssessment(assessment, "vigiles");
      if (!result.ok) {
        error = `schema validation failed: ${result.errors.join("; ")}`;
        assessment = null;
      }
    } catch (err) {
      error = err && err.message ? err.message : String(err);
      assessment = null;
    }
    const latencyMs = Date.now() - started;
    if (error !== null) {
      records.push({
        scenario_id: scenario.scenario_id,
        expected_condition: scenario.expected_observable_condition,
        ground_truth_label: scenario.ground_truth_label,
        category_in_products_js: scenario.category_in_products_js,
        category_decided: scenario.category_in_products_js !== null,
        alert_expected: scenario.alert_expected,
        review_expected: scenario.review_expected,
        actual_category: null,
        actual_summary: null,
        alert_fired: false,
        alert_correct: false,
        category_correct: false,
        evidence_reference: null,
        requires_human_review: null,
        latency_ms: latencyMs,
        error,
      });
      continue;
    }
    const actualCategory = assessment.assessment.category;
    const alertFired = alertCategories.includes(actualCategory);
    const categoryDecided = scenario.category_in_products_js !== null;
    const firstEvidence =
      Array.isArray(assessment.observations) && assessment.observations.length > 0
        ? assessment.observations[0].evidence
        : null;
    records.push({
      scenario_id: scenario.scenario_id,
      expected_condition: scenario.expected_observable_condition,
      ground_truth_label: scenario.ground_truth_label,
      category_in_products_js: scenario.category_in_products_js,
      category_decided: categoryDecided,
      alert_expected: scenario.alert_expected,
      review_expected: scenario.review_expected,
      actual_category: actualCategory,
      actual_summary: assessment.assessment.summary,
      alert_fired: alertFired,
      alert_correct: alertFired === scenario.alert_expected,
      category_correct: categoryDecided ? actualCategory === scenario.category_in_products_js : null,
      evidence_reference: firstEvidence,
      requires_human_review: assessment.assessment.requires_human_review,
      latency_ms: latencyMs,
      error: null,
    });
  }
  return records;
}

// The wired assessment source: the real server model adapter, with no
// frame attached (scenarios are labeled descriptions, not images —
// same caveat as the ignis and medicus harnesses). The adapter itself
// enforces the Spark gate, so with the gate shut this throws the held
// refusal and the harness records it as that scenario's error; with
// the gate open it throws a typed model_call_failed for the missing
// image bytes instead of an untyped crash. env is injectable for
// tests; production passes the server environment through unchanged.
export async function assessViaModelAdapter(scenario, env = process.env) {
  void scenario;
  return assessWithModel({ product: "vigiles" }, env);
}

export function formatVigilesReport({ source, records, metrics }) {
  const fmt = (v) => (v === null ? "n/a (denominator zero)" : v.toFixed(3));
  const decided = records.filter((r) => r.category_decided && r.error === null);
  const decidedCorrect = decided.filter((r) => r.category_correct).length;
  const decidedAccuracy = decided.length > 0 ? decidedCorrect / decided.length : null;
  const undecided = records.filter((r) => !r.category_decided);
  const lines = [
    `Meta Vigiles eval report — source: ${source}`,
    `Sample size: ${metrics.sample_size} scenarios`,
    `Confusion (alert): TP=${metrics.true_positives} FP=${metrics.false_positives} ` +
      `TN=${metrics.true_negatives} FN=${metrics.false_negatives}`,
    `Precision: ${fmt(metrics.precision)}`,
    `Recall: ${fmt(metrics.recall)}`,
    `False-positive rate: ${fmt(metrics.false_positive_rate)}`,
    `False-negative rate: ${fmt(metrics.false_negative_rate)}`,
    `Category accuracy (shared metric, all rows): ${fmt(metrics.category_accuracy)}`,
    `Category accuracy (decided rows only): ${decidedAccuracy === null ? "n/a (no decided rows)" : decidedAccuracy.toFixed(3)} ` +
      `(${decidedCorrect}/${decided.length} decided rows)`,
    `Category-undecided rows (taxonomy call for Pax, never scored as misses): ` +
      (undecided.length > 0 ? undecided.map((r) => r.scenario_id).join(", ") : "none"),
    `Latency (harness wall clock, ms): n=${metrics.latency_ms.n} ` +
      `mean=${metrics.latency_ms.mean === null ? "n/a" : metrics.latency_ms.mean.toFixed(1)} ` +
      `median=${metrics.latency_ms.median === null ? "n/a" : metrics.latency_ms.median} ` +
      `max=${metrics.latency_ms.max === null ? "n/a" : metrics.latency_ms.max}`,
    `Errors: ${metrics.errors.count}` +
      (metrics.errors.scenario_ids.length > 0 ? ` (${metrics.errors.scenario_ids.join(", ")})` : ""),
    "",
    "Per-scenario records:",
  ];
  for (const r of records) {
    const categoryShown =
      r.category_correct === null ? "undecided" : String(r.category_correct);
    lines.push(
      `  ${r.scenario_id}: truth=${r.ground_truth_label} ` +
        `products_category=${r.category_in_products_js === null ? "undecided" : r.category_in_products_js} ` +
        `actual=${r.actual_category === null ? "ERROR" : r.actual_category} ` +
        `alert_expected=${r.alert_expected} alert_fired=${r.alert_fired} ` +
        `alert_correct=${r.alert_correct} category_correct=${categoryShown}` +
        (r.error !== null ? ` error=${r.error}` : ""),
    );
  }
  return lines.join("\n");
}
