// Tests for the Meta Ignis evaluation adapter (Rowan's lane).
// Run: node --test eval/ignis/adapter.test.mjs
// (also wired into `npm test`). No network, no model calls: the
// held-state test passes an empty environment so the gate state is
// deterministic, and every other test uses local fake sources.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  IGNIS_ALERT_CATEGORIES,
  validateIgnisScenarios,
  runIgnisEval,
  computeMetrics,
  assessViaModelAdapter,
} from "./adapter.mjs";
import { PRODUCT_BY_ID } from "../../js/products.js";

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

function fakeAssessment(category) {
  return {
    product: "ignis",
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
    scenario_id: "IGN-T1",
    expected_observable_condition: "test condition",
    ground_truth_label: "visible smoke",
    alert_expected: true,
    ...overrides,
  };
}

// ---------- label loading ----------

test("labels: scenario set loads, ids unique, labels are ignis categories, alert flags match the definition", () => {
  assert.equal(validateIgnisScenarios(scenarios).length, 0);
  const ids = scenarios.map((s) => s.scenario_id);
  assert.equal(new Set(ids).size, ids.length, "duplicate scenario ids");
  for (const s of scenarios) {
    assert.ok(
      PRODUCT_BY_ID.ignis.categories.includes(s.ground_truth_label),
      `${s.scenario_id} label ${s.ground_truth_label} not an ignis category`,
    );
    assert.equal(
      s.alert_expected,
      IGNIS_ALERT_CATEGORIES.includes(s.ground_truth_label),
      `${s.scenario_id} alert_expected contradicts the alert definition`,
    );
  }
  assert.ok(scenarios.length >= 20, "scenario set should cover the directive cases with depth");
  const labels = new Set(scenarios.map((s) => s.ground_truth_label));
  for (const needed of [
    "visible smoke",
    "visible flame",
    "steam or fog",
    "flame-like lighting",
    "obscured or distant hazard",
    "no hazard visible",
    "indeterminate",
  ]) {
    assert.ok(labels.has(needed), `missing ground-truth label ${needed}`);
  }
});

test("labels: alert categories are exactly visible smoke and visible flame", () => {
  assert.deepEqual([...IGNIS_ALERT_CATEGORIES].sort(), ["visible flame", "visible smoke"]);
});

test("labels: invalid sets are rejected, not run", () => {
  assert.ok(validateIgnisScenarios([{ ...oneScenario(), scenario_id: "X" }, { ...oneScenario(), scenario_id: "X" }]).length > 0);
  assert.ok(validateIgnisScenarios([{ ...oneScenario(), ground_truth_label: "not a category" }]).length > 0);
  assert.ok(validateIgnisScenarios([{ ...oneScenario(), alert_expected: false }]).length > 0);
  assert.ok(validateIgnisScenarios([{ ...oneScenario(), ground_truth_label: "steam or fog", alert_expected: true }]).length > 0);
  assert.ok(validateIgnisScenarios([]).length > 0);
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

// ---------- alert-correctness logic ----------

test("alert logic: TP, FP, TN, FN, obscured hazard, and indeterminate all scored correctly", async () => {
  const cases = [
    { scenario: oneScenario({ ground_truth_label: "visible smoke", alert_expected: true }), assess: () => fakeAssessment("visible smoke"), want: { fired: true, correct: true, cat: true } },
    { scenario: oneScenario({ ground_truth_label: "no hazard visible", alert_expected: false }), assess: () => fakeAssessment("visible flame"), want: { fired: true, correct: false, cat: false } },
    { scenario: oneScenario({ ground_truth_label: "steam or fog", alert_expected: false }), assess: () => fakeAssessment("steam or fog"), want: { fired: false, correct: true, cat: true } },
    { scenario: oneScenario({ ground_truth_label: "obscured or distant hazard", alert_expected: false }), assess: () => fakeAssessment("obscured or distant hazard"), want: { fired: false, correct: true, cat: true } },
    { scenario: oneScenario({ ground_truth_label: "visible flame", alert_expected: true }), assess: () => fakeAssessment("indeterminate"), want: { fired: false, correct: false, cat: false } },
    { scenario: oneScenario({ ground_truth_label: "indeterminate", alert_expected: false }), assess: () => fakeAssessment("indeterminate"), want: { fired: false, correct: true, cat: true } },
  ];
  for (const c of cases) {
    const [r] = await runIgnisEval([c.scenario], c.assess);
    assert.equal(r.alert_fired, c.want.fired, c.scenario.ground_truth_label);
    assert.equal(r.alert_correct, c.want.correct);
    assert.equal(r.category_correct, c.want.cat);
    assert.equal(r.error, null);
  }
});

// ---------- malformed-input containment ----------

test("containment: a throwing source and an invalid shape are recorded, the run continues", async () => {
  const set = [
    oneScenario({ scenario_id: "IGN-A" }),
    oneScenario({ scenario_id: "IGN-B", ground_truth_label: "no hazard visible", alert_expected: false }),
    oneScenario({ scenario_id: "IGN-C" }),
  ];
  const assess = async (s) => {
    if (s.scenario_id === "IGN-A") throw new Error("source exploded");
    if (s.scenario_id === "IGN-B") return { product: "ignis", nonsense: true };
    return fakeAssessment("visible smoke");
  };
  const records = await runIgnisEval(set, assess);
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
    runIgnisEval([{ ...oneScenario(), ground_truth_label: "bogus" }], async () => {
      called += 1;
      return fakeAssessment("no hazard visible");
    }),
    /invalid scenario set/,
  );
  assert.equal(called, 0);
});

test("containment: runIgnisEval does not mutate the scenario objects", async () => {
  const frozen = scenarios.map((s) => Object.freeze({ ...s }));
  const before = JSON.stringify(frozen);
  await runIgnisEval(frozen, () => fakeAssessment("visible smoke"));
  assert.equal(JSON.stringify(frozen), before);
});

// ---------- held state: the wired source refuses, honestly ----------

test("held state: the wired source throws the held refusal under an empty environment", async () => {
  await assert.rejects(
    assessViaModelAdapter(oneScenario(), {}),
    /Live model calls are held/,
  );
});

test("held state: a full held run records the refusal for every scenario and fabricates nothing", async () => {
  const records = await runIgnisEval(scenarios, (s) => assessViaModelAdapter(s, {}));
  assert.equal(records.length, scenarios.length);
  for (const r of records) {
    assert.match(r.error, /Live model calls are held/);
    assert.equal(r.actual_category, null);
    assert.equal(r.alert_fired, false);
    assert.equal(r.category_correct, false);
  }
  const metrics = computeMetrics(records);
  assert.equal(metrics.errors.count, scenarios.length);
  assert.equal(metrics.category_accuracy, 0);
});
