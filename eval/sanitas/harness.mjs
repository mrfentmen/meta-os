// Meta Sanitas evaluation harness (Agent 3).
// No dependencies, no network, no model calls. Runs a labeled scenario
// set against an assessment source and measures it honestly.
//
// Assessment source contract: an async function assess(scenario) that
// returns one Meta Trio v2 assessment object (js/schema.js) for the
// scenario, or throws. The harness validates every returned object
// against the frozen v2 contract with product "sanitas". A source that
// throws or returns an invalid shape is recorded as an error for that
// scenario only; the run continues (malformed-input containment).
//
// Alert definition (fixed, from the scenario labels): an assessment
// "fires an alert" when its assessment.category is one of the three
// inspection-action categories below. "ambiguous object" and
// "indeterminate" never fire an alert; they warrant human review, which
// is recorded separately and is not scored as an alert.
//
// Metrics: precision, recall, false-positive rate, false-negative rate,
// category accuracy, and end-to-end latency (wall clock of the assess
// call, measured by the harness, never taken from a reported field).
// A metric whose denominator is zero is null, not zero, and the report
// says why. Nothing here invents a result.

import { validateAssessment } from "../../js/schema.js";
import { PRODUCT_BY_ID } from "../../js/products.js";

export const ALERT_CATEGORIES = [
  "overflowing bin",
  "waste accumulation",
  "blocked pedestrian path",
];

const SANITAS_CATEGORIES = PRODUCT_BY_ID.sanitas.categories;

export function validateScenarios(scenarios) {
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
    if (!SANITAS_CATEGORIES.includes(s.ground_truth_label)) {
      errors.push(
        `${prefix}.ground_truth_label: "${s.ground_truth_label}" is not a sanitas category ` +
          `(${SANITAS_CATEGORIES.join(", ")})`,
      );
    }
    if (typeof s.alert_expected !== "boolean") {
      errors.push(`${prefix}.alert_expected: missing or not a boolean`);
    }
  });
  return errors;
}

function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export async function runEval(scenarios, assess) {
  const labelErrors = validateScenarios(scenarios);
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
      const result = validateAssessment(assessment, "sanitas");
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
    const alertFired = ALERT_CATEGORIES.includes(actualCategory);
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

export function computeMetrics(records) {
  let tp = 0;
  let fp = 0;
  let tn = 0;
  let fn = 0;
  let categoryCorrect = 0;
  const latencies = [];
  const errorIds = [];
  for (const r of records) {
    if (r.alert_fired && r.alert_expected) tp += 1;
    else if (r.alert_fired && !r.alert_expected) fp += 1;
    else if (!r.alert_fired && !r.alert_expected) tn += 1;
    else fn += 1;
    if (r.category_correct) categoryCorrect += 1;
    if (typeof r.latency_ms === "number") latencies.push(r.latency_ms);
    if (r.error !== null) errorIds.push(r.scenario_id);
  }
  const ratio = (num, den) => (den > 0 ? num / den : null);
  const mean = latencies.length > 0
    ? latencies.reduce((a, b) => a + b, 0) / latencies.length
    : null;
  return {
    sample_size: records.length,
    true_positives: tp,
    false_positives: fp,
    true_negatives: tn,
    false_negatives: fn,
    precision: ratio(tp, tp + fp),
    recall: ratio(tp, tp + fn),
    false_positive_rate: ratio(fp, fp + tn),
    false_negative_rate: ratio(fn, fn + tp),
    category_accuracy: records.length > 0 ? categoryCorrect / records.length : null,
    latency_ms: {
      n: latencies.length,
      mean,
      median: median(latencies),
      max: latencies.length > 0 ? Math.max(...latencies) : null,
    },
    errors: { count: errorIds.length, scenario_ids: errorIds },
  };
}

export function formatReport({ source, records, metrics }) {
  const fmt = (v) => (v === null ? "n/a (denominator zero)" : v.toFixed(3));
  const lines = [
    `Meta Sanitas eval report — source: ${source}`,
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
