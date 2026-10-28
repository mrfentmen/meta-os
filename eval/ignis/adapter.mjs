// Meta Ignis evaluation adapter (Rowan's lane).
//
// Mirrors the shape of Milo's Meta Sanitas harness (eval/sanitas/
// harness.mjs) for the Ignis product, without touching Milo's files:
// the same per-scenario record shape, the same metric math (imported
// from the Sanitas harness, which is product-agnostic), the same
// malformed-input containment (a source that throws or returns an
// invalid shape is recorded as an error for that scenario only; the
// run continues).
//
// Assessment source contract: an async function assess(scenario) that
// returns one Meta Trio v2 assessment object (js/schema.js) for the
// scenario, or throws. Every returned object is validated against the
// frozen v2 contract with product "ignis".
//
// Alert definition (fixed, from the scenario labels): an assessment
// "fires an alert" when its assessment.category is "visible smoke" or
// "visible flame". "obscured or distant hazard" never fires an alert
// on its own: a distant or partially hidden hazard warrants human
// review, recorded separately, not an automatic alert — the same logic
// the Sanitas set applies to "ambiguous object". "steam or fog" and
// "flame-like lighting" are confusable negatives and never fire an
// alert; "no hazard visible" and "indeterminate" never fire either.
//
// The wired source, assessViaModelAdapter, delegates to the real
// server model adapter (server/model.mjs). While Del's Spark rule
// holds, that adapter throws the held refusal, so every scenario in a
// run records that refusal as its error — no assessment is fabricated,
// and the report describes source availability, not model performance.
// When the test phase lands the Spark transport, this same function
// returns real assessments with no adapter change, and the same
// harness scores them. No live model call happens from this file
// itself: it only calls the server adapter, which enforces the gate.

import { validateAssessment } from "../../js/schema.js";
import { PRODUCT_BY_ID } from "../../js/products.js";
import { assessWithModel } from "../../server/model.mjs";
import { computeMetrics } from "../sanitas/harness.mjs";

export { computeMetrics };

export const IGNIS_ALERT_CATEGORIES = ["visible smoke", "visible flame"];

const IGNIS_CATEGORIES = PRODUCT_BY_ID.ignis.categories;

export function validateIgnisScenarios(scenarios) {
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
    if (!IGNIS_CATEGORIES.includes(s.ground_truth_label)) {
      errors.push(
        `${prefix}.ground_truth_label: "${s.ground_truth_label}" is not an ignis category ` +
          `(${IGNIS_CATEGORIES.join(", ")})`,
      );
    }
    if (typeof s.alert_expected !== "boolean") {
      errors.push(`${prefix}.alert_expected: missing or not a boolean`);
    } else if (
      IGNIS_CATEGORIES.includes(s.ground_truth_label) &&
      s.alert_expected !== IGNIS_ALERT_CATEGORIES.includes(s.ground_truth_label)
    ) {
      errors.push(
        `${prefix}.alert_expected: ${s.alert_expected} contradicts the alert definition ` +
          `(alert only for ${IGNIS_ALERT_CATEGORIES.join(", ")})`,
      );
    }
  });
  return errors;
}

export async function runIgnisEval(scenarios, assess) {
  const labelErrors = validateIgnisScenarios(scenarios);
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
      const result = validateAssessment(assessment, "ignis");
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
        alert_expected: scenario.alert_expected,
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
    const alertFired = IGNIS_ALERT_CATEGORIES.includes(actualCategory);
    const firstEvidence =
      Array.isArray(assessment.observations) && assessment.observations.length > 0
        ? assessment.observations[0].evidence
        : null;
    records.push({
      scenario_id: scenario.scenario_id,
      expected_condition: scenario.expected_observable_condition,
      ground_truth_label: scenario.ground_truth_label,
      alert_expected: scenario.alert_expected,
      actual_category: actualCategory,
      actual_summary: assessment.assessment.summary,
      alert_fired: alertFired,
      alert_correct: alertFired === scenario.alert_expected,
      category_correct: actualCategory === scenario.ground_truth_label,
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
// same caveat as the Sanitas harness, which runs descriptions against
// fixtures). The adapter itself enforces the Spark gate, so in every
// current gate state this throws a typed refusal (held /
// not_configured / transport_not_wired) and the harness records it as
// that scenario's error. env is injectable for tests; production
// passes the server environment through unchanged.
export async function assessViaModelAdapter(scenario, env = process.env) {
  void scenario;
  return assessWithModel({ product: "ignis" }, env);
}

export function formatIgnisReport({ source, records, metrics }) {
  const fmt = (v) => (v === null ? "n/a (denominator zero)" : v.toFixed(3));
  const lines = [
    `Meta Ignis eval report — source: ${source}`,
    `Sample size: ${metrics.sample_size} scenarios`,
    `Confusion (alert): TP=${metrics.true_positives} FP=${metrics.false_positives} ` +
      `TN=${metrics.true_negatives} FN=${metrics.false_negatives}`,
    `Precision: ${fmt(metrics.precision)}`,
    `Recall: ${fmt(metrics.recall)}`,
    `False-positive rate: ${fmt(metrics.false_positive_rate)}`,
    `False-negative rate: ${fmt(metrics.false_negative_rate)}`,
    `Category accuracy: ${fmt(metrics.category_accuracy)}`,
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
    lines.push(
      `  ${r.scenario_id}: truth=${r.ground_truth_label} ` +
        `actual=${r.actual_category === null ? "ERROR" : r.actual_category} ` +
        `alert_expected=${r.alert_expected} alert_fired=${r.alert_fired} ` +
        `alert_correct=${r.alert_correct} category_correct=${r.category_correct}` +
        (r.error !== null ? ` error=${r.error}` : ""),
    );
  }
  return lines.join("\n");
}
