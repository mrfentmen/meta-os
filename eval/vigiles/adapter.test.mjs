// Tests for the Meta Vigiles evaluation adapter (Hana's lane).
// Run: node --test eval/vigiles/adapter.test.mjs
// (also wired into `npm test`). No network, no model calls: the
// held-state test passes an empty environment so the gate state is
// deterministic, and every other test uses local fake sources.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  VIGILES_ALERT_CATEGORIES,
  validateVigilesScenarios,
  runVigilesEval,
  computeMetrics,
  assessViaModelAdapter,
  formatVigilesReport,
} from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";
import { assessStub } from "./stub.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

function fakeAssessment(category, review = false) {
  return {
    product: "vigiles",
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [
      { category, description: "test observation", evidence: "test frame", confidence: null },
    ],
    assessment: {
      category,
      summary: "test summary",
      uncertainty: [],
      requires_human_review: review,
    },
    processing: { model: "test", latency_ms: null },
  };
}

function oneScenario(overrides = {}) {
  return {
    scenario_id: "VIG-T1",
    expected_observable_condition: "test condition",
    ground_truth_label: "crowd gathered in a public space",
    category_in_products_js: "crowd gathered",
    alert_expected: false,
    review_expected: false,
    ...overrides,
  };
}

// ---------- fixture loading ----------

test("fixture scenarios.json passes validation (3 frame-anchored rows)", () => {
  assert.equal(scenarios.length, 3);
  assert.deepEqual(
    scenarios.map((s) => s.scenario_id),
    ["VIG-F01", "VIG-F02", "VIG-F03"],
  );
  assert.deepEqual(validateVigilesScenarios(scenarios), []);
});

test("alert categories are the repo red tier, and crowd gathered does not fire", () => {
  assert.deepEqual(VIGILES_ALERT_CATEGORIES, [
    "physical contact",
    "person down",
    "possible altercation",
  ]);
  assert.equal(VIGILES_ALERT_CATEGORIES.includes("crowd gathered"), false);
  assert.equal(VIGILES_ALERT_CATEGORIES.includes("normal activity"), false);
});

// ---------- validation ----------

test("validation rejects duplicate ids, missing condition, missing label", () => {
  const dup = [oneScenario(), oneScenario()];
  assert.ok(validateVigilesScenarios(dup).some((e) => e.includes("duplicate")));
  const noCondition = [oneScenario({ expected_observable_condition: "" })];
  assert.ok(validateVigilesScenarios(noCondition).some((e) => e.includes("expected_observable_condition")));
  const noLabel = [oneScenario({ ground_truth_label: "" })];
  assert.ok(validateVigilesScenarios(noLabel).some((e) => e.includes("ground_truth_label")));
});

test("validation requires category_in_products_js present, string in taxonomy or null", () => {
  const missing = [oneScenario()];
  delete missing[0].category_in_products_js;
  assert.ok(validateVigilesScenarios(missing).some((e) => e.includes("category_in_products_js")));
  const bad = [oneScenario({ category_in_products_js: "public disturbance / altercation" })];
  assert.ok(validateVigilesScenarios(bad).some((e) => e.includes("not a vigiles category")));
  // Null is allowed: the mapping is undecided (Pax's taxonomy call),
  // and a non-category ground-truth label is allowed with it.
  const undecided = [
    oneScenario({
      ground_truth_label: "public disturbance / altercation",
      category_in_products_js: null,
      alert_expected: true,
      review_expected: true,
    }),
  ];
  assert.deepEqual(validateVigilesScenarios(undecided), []);
});

test("validation cross-checks alert_expected only for decided categories", () => {
  const contradiction = [oneScenario({ alert_expected: true })];
  assert.ok(validateVigilesScenarios(contradiction).some((e) => e.includes("alert_expected")));
  const alertRow = [
    oneScenario({
      category_in_products_js: "possible altercation",
      alert_expected: true,
    }),
  ];
  assert.deepEqual(validateVigilesScenarios(alertRow), []);
  const missingReview = [oneScenario({ review_expected: undefined })];
  assert.ok(validateVigilesScenarios(missingReview).some((e) => e.includes("review_expected")));
});

test("runVigilesEval rejects an invalid set instead of scoring it", async () => {
  await assert.rejects(
    runVigilesEval([oneScenario(), oneScenario()], async () => fakeAssessment("normal activity")),
    /invalid scenario set/,
  );
});

// ---------- scoring ----------

test("runVigilesEval scores alert and decided categories, undecided stays null", async () => {
  const rows = [
    oneScenario(),
    oneScenario({
      scenario_id: "VIG-T2",
      ground_truth_label: "normal activity",
      category_in_products_js: "normal activity",
    }),
    oneScenario({
      scenario_id: "VIG-T3",
      ground_truth_label: "public disturbance / altercation",
      category_in_products_js: null,
      alert_expected: true,
      review_expected: true,
    }),
  ];
  const byId = {
    "VIG-T1": "crowd gathered",
    "VIG-T2": "normal activity",
    "VIG-T3": "possible altercation",
  };
  const records = await runVigilesEval(rows, async (s) => fakeAssessment(byId[s.scenario_id]));
  assert.equal(records[0].alert_fired, false);
  assert.equal(records[0].alert_correct, true);
  assert.equal(records[0].category_correct, true);
  assert.equal(records[1].category_correct, true);
  // Undecided row: alert scored (possible altercation fires, expected
  // true), category explicitly null — never a miss.
  assert.equal(records[2].alert_fired, true);
  assert.equal(records[2].alert_correct, true);
  assert.equal(records[2].category_correct, null);
  assert.equal(records[2].category_decided, false);
});

test("runVigilesEval contains throwing and schema-invalid sources per row", async () => {
  const rows = [
    oneScenario(),
    oneScenario({ scenario_id: "VIG-T2" }),
    oneScenario({ scenario_id: "VIG-T3" }),
  ];
  const records = await runVigilesEval(rows, async (s) => {
    if (s.scenario_id === "VIG-T2") throw new Error("boom");
    if (s.scenario_id === "VIG-T3") return { product: "vigiles" };
    return fakeAssessment("crowd gathered");
  });
  assert.equal(records[0].error, null);
  assert.equal(records[1].error, "boom");
  assert.equal(records[1].actual_category, null);
  assert.match(records[2].error, /schema validation failed/);
});

// ---------- stub and baseline ----------

test("stub reproduces EVAL4 batch 6: 2 MATCH, 1 HELD, 0 MISS at alert level", async () => {
  const records = await runVigilesEval(scenarios, assessStub);
  const byId = Object.fromEntries(records.map((r) => [r.scenario_id, r]));
  assert.equal(byId["VIG-F01"].actual_category, "crowd gathered");
  assert.equal(byId["VIG-F01"].category_correct, true);
  assert.equal(byId["VIG-F02"].actual_category, "normal activity");
  assert.equal(byId["VIG-F02"].category_correct, true);
  assert.equal(byId["VIG-F03"].actual_category, "crowd gathered");
  assert.equal(byId["VIG-F03"].category_correct, null);
  assert.equal(byId["VIG-F03"].requires_human_review, true);
  const metrics = computeMetrics(records);
  assert.deepEqual(
    [metrics.true_positives, metrics.false_positives, metrics.true_negatives, metrics.false_negatives],
    [0, 0, 2, 1],
  );
  assert.equal(metrics.precision, null);
  assert.equal(metrics.recall, 0);
  const decided = records.filter((r) => r.category_decided);
  assert.equal(decided.filter((r) => r.category_correct).length, 2);
  assert.equal(decided.length, 2);
});

test("baseline always-normal: TN 2, FN 1, shared category accuracy 1/3", async () => {
  const records = await runVigilesEval(scenarios, assessBaseline);
  assert.ok(records.every((r) => r.actual_category === "normal activity"));
  assert.ok(records.every((r) => r.alert_fired === false));
  const metrics = computeMetrics(records);
  assert.deepEqual(
    [metrics.true_positives, metrics.false_positives, metrics.true_negatives, metrics.false_negatives],
    [0, 0, 2, 1],
  );
  assert.equal(metrics.precision, null);
  assert.equal(metrics.recall, 0);
  assert.equal(metrics.category_accuracy, 1 / 3);
});

// ---------- wired source / report ----------

test("wired source with an empty environment records the held refusal", async () => {
  await assert.rejects(
    assessViaModelAdapter(scenarios[0], {}),
    /Live model calls are held/,
  );
  const records = await runVigilesEval(scenarios, (s) => assessViaModelAdapter(s, {}));
  assert.ok(records.every((r) => typeof r.error === "string" && r.error.includes("Live model calls are held")));
  assert.ok(records.every((r) => r.actual_category === null));
});

test("report names the undecided row and shows decided-only accuracy", async () => {
  const records = await runVigilesEval(scenarios, assessStub);
  const report = formatVigilesReport({ source: "stub (fixture, not a model)", records, metrics: computeMetrics(records) });
  assert.match(report, /VIG-F03/);
  assert.match(report, /undecided/);
  assert.match(report, /decided rows only.*2\/2/);
});
