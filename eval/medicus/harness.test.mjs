// Tests for the Meta Medicus evaluation harness (Agent 3).
// Run: node --test eval/medicus/harness.test.mjs
// (also wired into `npm test`). No network, no model calls.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  ALERT_CATEGORIES,
  validateScenarios,
  runEval,
  computeMetrics,
} from "./harness.mjs";
import { assessStub } from "./stub.mjs";
import { assessBaseline } from "./baseline.mjs";
import { validateAssessment } from "../../js/schema.js";
import { PRODUCT_BY_ID } from "../../js/products.js";

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

function fakeAssessment(category) {
  return {
    product: "medicus",
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [
      { category, description: "test observation", evidence: "test frame", confidence: null },
    ],
    assessment: {
      category,
      summary: "test summary",
      uncertainty: [],
      requires_human_review: false,
    },
    processing: { model: "test", latency_ms: null },
  };
}

function oneScenario(overrides = {}) {
  return {
    scenario_id: "MED-T1",
    expected_observable_condition: "test condition",
    ground_truth_label: "person on ground",
    alert_expected: true,
    ...overrides,
  };
}

// ---------- label loading ----------

test("labels: scenario set loads, ids unique, labels are medicus categories", () => {
  assert.equal(validateScenarios(scenarios).length, 0);
  const ids = scenarios.map((s) => s.scenario_id);
  assert.equal(new Set(ids).size, ids.length, "duplicate scenario ids");
  for (const s of scenarios) {
    assert.ok(
      PRODUCT_BY_ID.medicus.categories.includes(s.ground_truth_label),
      `${s.scenario_id} label ${s.ground_truth_label} not a medicus category`,
    );
    assert.equal(typeof s.alert_expected, "boolean", `${s.scenario_id} alert_expected`);
  }
  assert.ok(scenarios.length >= 20, "scenario set should cover the directive cases with depth");
  const labels = new Set(scenarios.map((s) => s.ground_truth_label));
  for (const needed of [
    "person on ground",
    "crowd gathered around a person",
    "vehicle collision scene",
    "blocked crew access",
    "person motionless",
    "normal activity",
    "indeterminate",
  ]) {
    assert.ok(labels.has(needed), `missing ground-truth label ${needed}`);
  }
});

test("labels: alert categories match the directive action set", () => {
  assert.deepEqual([...ALERT_CATEGORIES].sort(), [
    "blocked crew access",
    "crowd gathered around a person",
    "person motionless",
    "person on ground",
    "vehicle collision scene",
  ]);
});

test("labels: invalid sets are rejected, not run", () => {
  assert.ok(validateScenarios([{ ...oneScenario(), scenario_id: "X" }, { ...oneScenario(), scenario_id: "X" }]).length > 0);
  assert.ok(validateScenarios([{ ...oneScenario(), ground_truth_label: "not a category" }]).length > 0);
  assert.ok(validateScenarios([]).length > 0);
});

// ---------- metric math ----------

test("metrics: hand-computed confusion gives exact precision/recall/FPR/FNR", () => {
  const records = [
    { alert_fired: true, alert_expected: true, category_correct: true, latency_ms: 10, error: null },
    { alert_fired: true, alert_expected: true, category_correct: false, latency_ms: 20, error: null },
    { alert_fired: true, alert_expected: false, category_correct: false, latency_ms: 30, error: null },
    { alert_fired: false, alert_expected: false, category_correct: true, latency_ms: 40, error: null },
    { alert_fired: false, alert_expected: true, category_correct: false, latency_ms: 50, error: null },
  ];
  const m = computeMetrics(records);
  assert.equal(m.true_positives, 2);
  assert.equal(m.false_positives, 1);
  assert.equal(m.true_negatives, 1);
  assert.equal(m.false_negatives, 1);
  assert.equal(m.precision, 2 / 3);
  assert.equal(m.recall, 2 / 3);
  assert.equal(m.false_positive_rate, 1 / 2);
  assert.equal(m.false_negative_rate, 1 / 3);
  assert.equal(m.category_accuracy, 2 / 5);
  assert.equal(m.latency_ms.mean, 30);
  assert.equal(m.latency_ms.median, 30);
  assert.equal(m.latency_ms.max, 50);
});

test("metrics: zero denominators give null, not zero or NaN", () => {
  const m = computeMetrics([
    { alert_fired: false, alert_expected: false, category_correct: true, latency_ms: 5, error: null },
  ]);
  assert.equal(m.precision, null);
  assert.equal(m.recall, null);
  assert.equal(m.false_negative_rate, null);
  assert.equal(m.false_positive_rate, 0);
});

// ---------- alert-correctness logic ----------

test("alert logic: TP, FP, TN, FN and indeterminate all scored correctly", async () => {
  const cases = [
    { scenario: oneScenario({ ground_truth_label: "person on ground", alert_expected: true }), assess: () => fakeAssessment("person on ground"), want: { fired: true, correct: true, cat: true } },
    { scenario: oneScenario({ ground_truth_label: "normal activity", alert_expected: false }), assess: () => fakeAssessment("vehicle collision scene"), want: { fired: true, correct: false, cat: false } },
    { scenario: oneScenario({ ground_truth_label: "normal activity", alert_expected: false }), assess: () => fakeAssessment("normal activity"), want: { fired: false, correct: true, cat: true } },
    { scenario: oneScenario({ ground_truth_label: "person on ground", alert_expected: true }), assess: () => fakeAssessment("indeterminate"), want: { fired: false, correct: false, cat: false } },
    { scenario: oneScenario({ ground_truth_label: "indeterminate", alert_expected: false }), assess: () => fakeAssessment("indeterminate"), want: { fired: false, correct: true, cat: true } },
  ];
  for (const c of cases) {
    const [r] = await runEval([c.scenario], c.assess);
    assert.equal(r.alert_fired, c.want.fired, c.scenario.ground_truth_label);
    assert.equal(r.alert_correct, c.want.correct);
    assert.equal(r.category_correct, c.want.cat);
    assert.equal(r.error, null);
  }
});

// ---------- malformed-input containment ----------

test("containment: a throwing source and an invalid shape are recorded, the run continues", async () => {
  const set = [
    oneScenario({ scenario_id: "MED-A" }),
    oneScenario({ scenario_id: "MED-B", ground_truth_label: "normal activity", alert_expected: false }),
    oneScenario({ scenario_id: "MED-C" }),
  ];
  const assess = async (s) => {
    if (s.scenario_id === "MED-A") throw new Error("source exploded");
    if (s.scenario_id === "MED-B") return { product: "medicus", nonsense: true };
    return fakeAssessment("person on ground");
  };
  const records = await runEval(set, assess);
  assert.equal(records.length, 3);
  assert.match(records[0].error, /exploded/);
  assert.equal(records[0].alert_correct, false);
  assert.match(records[1].error, /schema validation failed/);
  assert.equal(records[2].error, null);
  assert.equal(records[2].alert_correct, true);
});

test("containment: an invalid scenario set throws before any assessment runs", async () => {
  let called = 0;
  await assert.rejects(
    runEval([{ ...oneScenario(), ground_truth_label: "bogus" }], async () => {
      called += 1;
      return fakeAssessment("normal activity");
    }),
    /invalid scenario set/,
  );
  assert.equal(called, 0);
});

// ---------- fixture sources are contract-valid ----------

test("fixtures: stub and baseline answers pass v2 schema validation for every scenario", async () => {
  for (const s of scenarios) {
    for (const assess of [assessStub, assessBaseline]) {
      const out = await assess(s);
      const result = validateAssessment(out, "medicus");
      assert.equal(result.ok, true, `${s.scenario_id}: ${result.errors.join("; ")}`);
    }
  }
});

test("fixtures: runEval does not mutate the scenario objects", async () => {
  const frozen = scenarios.map((s) => Object.freeze({ ...s }));
  const before = JSON.stringify(frozen);
  await runEval(frozen, assessStub);
  assert.equal(JSON.stringify(frozen), before);
});
