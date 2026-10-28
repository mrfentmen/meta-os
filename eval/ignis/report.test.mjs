// Tests for the Meta Ignis run-report renderer (Rowan's lane).
// Run: node --test eval/ignis/report.test.mjs
// (also wired into `npm test`). No network, no model calls: the
// held-state case passes an empty environment so the gate state is
// deterministic, and every other case uses local fake sources or
// hand-built run JSON. The CLI test runs report.mjs in a temp dir.

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

import { runIgnisEval, computeMetrics, assessViaModelAdapter } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";
import { assessStub } from "./stub.mjs";

import {
  PROTECTED_REPORT_NAMES,
  assertWritableReportPath,
  classifyRunKind,
  computeCategoryConfusion,
  computeBaselineDeltas,
  computeCategoryHeadline,
  computeCategoryCorrect,
  computeCategoryRates,
  computeConfusableNegatives,
  computeAlertCorrect,
  computeAlertErrors,
  computeErrorBreakdown,
  computeLatencyByCategory,
  computeLatencyByAlertOutcome,
  computeLatencyByAlertCorrectness,
  computeLatencyByAlertExpectation,
  computeLatencyByAlertFired,
  computeLatencyByAssessed,
  computeLatencyByCategoryCorrectness,
  computeLatencyByOutcome,
  computeLatencyDistribution,
  computeLatencyOutliers,
  computeMissPairs,
  computeMisses,
  computeSlowestScenario,
  renderRunReport,
} from "./report.mjs";

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

async function buildRun(assess, source, generated) {
  const records = await runIgnisEval(scenarios, assess);
  return { source, records, metrics: computeMetrics(records), generated };
}

test("report: a stub run classifies as fixture and renders its measured numbers, never as live", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  assert.equal(classifyRunKind(run), "fixture");
  const report = renderRunReport(run);
  assert.match(report, /^# Meta Ignis fixture run report/m);
  assert.match(report, /TP=4 FP=3 TN=12 FN=1/);
  assert.match(report, /Category accuracy: 0\.700/);
  assert.doesNotMatch(report, /^# Meta Ignis live-model run report/m);
  assert.match(report, /not a model result|not.*model performance/);
});

test("report: a held run classifies as held-state and says its numbers describe source availability", async () => {
  const run = await buildRun((s) => assessViaModelAdapter(s, {}), "server model adapter (held while Spark stays off)", "held-state run, no live model");
  assert.equal(classifyRunKind(run), "held-state");
  const report = renderRunReport(run);
  assert.match(report, /^# Meta Ignis held-state run report/m);
  assert.match(report, /source availability, not model performance/);
  assert.match(report, /Errors: 20/);
});

test("report: assessments in the records beat a stale held label — a live-shaped run renders as live", async () => {
  // Deliberately stale labels from an older run.mjs: the records carry
  // real assessments, so evidence, not the label, decides the kind.
  const run = await buildRun(
    (s) => fakeAssessment(s.ground_truth_label),
    "server model adapter (held while Spark stays off)",
    "held-state run, no live model",
  );
  assert.equal(classifyRunKind(run), "live-model");
  const report = renderRunReport(run);
  assert.match(report, /^# Meta Ignis live-model run report/m);
  assert.match(report, /Category accuracy: 1\.000/);
});

test("report: baseline comparison — stub beats the baseline, baseline does not beat itself", async () => {
  const stubRun = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const baselineRun = await buildRun(assessBaseline, "baseline always-no-hazard (fixture)", "fixture run, no live model");
  assert.match(renderRunReport(stubRun, baselineRun), /BEATS the baseline on recall and category accuracy/);
  assert.match(renderRunReport(baselineRun, baselineRun), /does NOT beat the baseline/);
  assert.match(renderRunReport(stubRun), /No baseline run supplied/);
});

test("report: baseline comparison renders signed deltas — stub beats baseline by +0.800 recall, +0.550 accuracy", async () => {
  const stubRun = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const baselineRun = await buildRun(assessBaseline, "baseline always-no-hazard (fixture)", "fixture run, no live model");
  const deltas = computeBaselineDeltas(stubRun.metrics, baselineRun.metrics);
  assert.equal(deltas.recallDelta, 0.8);
  // 14/20 - 3/20 is 0.5499999999999999 in binary floating point, so
  // compare within epsilon; the rendered line still prints +0.550.
  assert.ok(Math.abs(deltas.categoryAccuracyDelta - 0.55) < 1e-9);
  assert.equal(deltas.beats, true);
  // Baseline against itself: zero deltas, not a beat.
  const selfDeltas = computeBaselineDeltas(baselineRun.metrics, baselineRun.metrics);
  assert.equal(selfDeltas.recallDelta, 0);
  assert.equal(selfDeltas.categoryAccuracyDelta, 0);
  assert.equal(selfDeltas.beats, false);
  // Null on either side is n/a, never zero: a held run's recall is
  // null only when its metrics say so, and a null delta must not
  // read as "no change" or count as a beat.
  const nullDeltas = computeBaselineDeltas(
    { recall: null, category_accuracy: 0.5 },
    { recall: 0, category_accuracy: 0.15 },
  );
  assert.equal(nullDeltas.recallDelta, null);
  assert.equal(nullDeltas.beats, false);
  const report = renderRunReport(stubRun, baselineRun);
  assert.match(report, /Recall delta: \+0\.800/);
  assert.match(report, /Category-accuracy delta: \+0\.550/);
  const heldReport = renderRunReport(baselineRun, baselineRun);
  assert.match(heldReport, /Recall delta: \+0\.000/);
  assert.match(heldReport, /Category-accuracy delta: \+0\.000/);
});

test("report: per-category confusion table names the stub's exact swaps", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const confusion = computeCategoryConfusion(run.records);
  assert.equal(confusion.counts["visible smoke"]["indeterminate"], 1); // IGN-003
  assert.equal(confusion.counts["steam or fog"]["visible smoke"], 1); // IGN-007
  assert.equal(confusion.counts["flame-like lighting"]["visible flame"], 2); // IGN-010, IGN-018
  assert.equal(confusion.counts["obscured or distant hazard"]["flame-like lighting"], 1); // IGN-012
  assert.equal(confusion.counts["indeterminate"]["steam or fog"], 1); // IGN-015
  assert.equal(confusion.counts["visible smoke"]["visible smoke"], 2); // IGN-001, IGN-016
  assert.equal(confusion.counts["steam or fog"]["steam or fog"], 1); // IGN-008
  assert.ok(!confusion.predictedCategories.includes("ERROR")); // the stub assesses every scenario
  const report = renderRunReport(run);
  assert.match(report, /## Per-category confusion/);
  assert.match(report, /\| steam or fog \|/);
  assert.match(report, /failures, not confusions/);
});

test("report: confusable-negative breakdown counts the stub's three false alarms", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const confusables = computeConfusableNegatives(run.records);
  const steam = confusables.find((e) => e.truth === "steam or fog");
  const flameLike = confusables.find((e) => e.truth === "flame-like lighting");
  assert.equal(steam.total, 2);
  assert.equal(steam.falseAlarmCount, 1);
  assert.deepEqual(steam.falseAlarms["visible smoke"], ["IGN-007"]);
  assert.equal(flameLike.total, 3);
  assert.equal(flameLike.falseAlarmCount, 2);
  assert.deepEqual(flameLike.falseAlarms["visible flame"], ["IGN-010", "IGN-018"]);
  const report = renderRunReport(run);
  assert.match(report, /## Confusable negatives/);
  assert.match(report, /Total: 3 of 5 confusable-negative scenarios predicted as an alert category/);
  assert.match(report, /IGN-007/);
});

test("report: headline finding names the stub's weakest category and most-confused pair, above the table", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const headline = computeCategoryHeadline(run.records);
  assert.equal(headline.weakest.truth, "flame-like lighting");
  assert.equal(headline.weakest.correct, 1);
  assert.equal(headline.weakest.total, 3);
  assert.equal(headline.mostConfused.truth, "flame-like lighting");
  assert.equal(headline.mostConfused.predicted, "visible flame");
  assert.equal(headline.mostConfused.count, 2);
  assert.deepEqual(headline.mostConfused.scenarioIds, ["IGN-010", "IGN-018"]);
  const report = renderRunReport(run);
  assert.match(report, /## Headline finding/);
  assert.match(report, /Weakest category: flame-like lighting — 1 of 3 correct \(0\.333\)/);
  assert.match(report, /Most confused pair: flame-like lighting -> visible flame — 2 scenario\(s\) \(IGN-010, IGN-018\)/);
  assert.ok(report.indexOf("## Headline finding") < report.indexOf("## Per-category confusion"));
});

test("report: headline names the slowest scenario — max latency, missing latency ignored, ties alphabetical", async () => {
  // Hand-built: the max wins, a record with no latency is ignored
  // (never a zero), and an exact tie breaks by scenario id.
  assert.deepEqual(
    computeSlowestScenario([
      { scenario_id: "T2", ground_truth_label: "beta", latency_ms: 12.5 },
      { scenario_id: "T1", ground_truth_label: "alpha" },
      { scenario_id: "T3", ground_truth_label: "gamma", latency_ms: 12.5 },
      { scenario_id: "T4", ground_truth_label: "delta", latency_ms: 3.0 },
    ]),
    { scenarioId: "T2", truth: "beta", latencyMs: 12.5 },
  );
  assert.equal(computeSlowestScenario([{ scenario_id: "T1", ground_truth_label: "alpha" }]), null);
  // Rendered: a stub run's headline carries a slowest line (wall-clock
  // values vary run to run, so match the shape, not a number), and a
  // hand-built run with no latency says none recorded, not zero.
  const stubRun = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const stubReport = renderRunReport(stubRun);
  assert.match(stubReport, /- Slowest scenario: IGN-\d+ \(.+\) — \d+\.\d ms \(harness wall clock\)\./);
  assert.ok(stubReport.indexOf("## Headline finding") < stubReport.indexOf("Slowest scenario:"));
  assert.ok(stubReport.indexOf("Slowest scenario:") < stubReport.indexOf("## Per-category rates"));
  const handRun = {
    source: "test source",
    generated: "test run",
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: true, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 1, true_positives: 1, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 1, mean: 0, median: 0, max: 0 }, errors: { count: 0, scenario_ids: [] } },
  };
  assert.match(renderRunReport(handRun), /- Slowest scenario: none recorded — no record in this run carries a latency measurement\./);
});

test("report: per-category rate table backs the headline — stub rates, alphabetical order, errors as misses", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  const rates = computeCategoryRates(run.records);
  assert.deepEqual(
    rates.map((r) => r.truth),
    ["flame-like lighting", "indeterminate", "no hazard visible", "obscured or distant hazard", "steam or fog", "visible flame", "visible smoke"],
  );
  const flameLike = rates.find((r) => r.truth === "flame-like lighting");
  assert.equal(flameLike.correct, 1);
  assert.equal(flameLike.total, 3);
  assert.equal(flameLike.assessed, 3);
  assert.equal(flameLike.rate, 1 / 3);
  const smoke = rates.find((r) => r.truth === "visible smoke");
  assert.equal(smoke.correct, 2);
  assert.equal(smoke.total, 3);
  const report = renderRunReport(run);
  assert.match(report, /## Per-category rates/);
  assert.match(report, /\| flame-like lighting \| 1 \| 3 \| 3 \| 0\.333 \|/);
  assert.match(report, /\| visible smoke \| 2 \| 3 \| 3 \| 0\.667 \|/);
  assert.ok(report.indexOf("## Headline finding") < report.indexOf("## Per-category rates"));
  assert.ok(report.indexOf("## Per-category rates") < report.indexOf("## Per-scenario records"));
  // The headline's weakest row is the table's lowest rate.
  assert.equal(computeCategoryHeadline(run.records).weakest.truth, "flame-like lighting");
});

test("report: per-category rates count unassessed records as misses and show assessed separately", () => {
  const rates = computeCategoryRates([
    { scenario_id: "T1", ground_truth_label: "alpha", actual_category: "alpha" },
    { scenario_id: "T2", ground_truth_label: "alpha", actual_category: null },
    { scenario_id: "T3", ground_truth_label: "beta", actual_category: null },
  ]);
  assert.deepEqual(rates, [
    { truth: "alpha", total: 2, correct: 1, assessed: 1, rate: 0.5 },
    { truth: "beta", total: 1, correct: 0, assessed: 0, rate: 0 },
  ]);
});

test("report: misses section names truth -> predicted per miss, ERROR for unassessed records", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  assert.deepEqual(
    computeMisses(run.records).map((m) => `${m.scenarioId}: ${m.truth} -> ${m.predicted}`),
    [
      "IGN-003: visible smoke -> indeterminate",
      "IGN-007: steam or fog -> visible smoke",
      "IGN-010: flame-like lighting -> visible flame",
      "IGN-012: obscured or distant hazard -> flame-like lighting",
      "IGN-015: indeterminate -> steam or fog",
      "IGN-018: flame-like lighting -> visible flame",
    ],
  );
  const report = renderRunReport(run);
  assert.match(report, /## Misses \(6\)/);
  assert.match(report, /- IGN-003: visible smoke -> indeterminate/);
  assert.match(report, /- IGN-007: steam or fog -> visible smoke/);
  assert.match(report, /- IGN-018: flame-like lighting -> visible flame/);
  assert.doesNotMatch(report, /predicted category did not match ground truth/);
  // Hand-built: an unassessed record is a miss that shows ERROR, not a category,
  // and a correct record is not a miss.
  assert.deepEqual(
    computeMisses([
      { scenario_id: "T1", ground_truth_label: "visible smoke", actual_category: null, category_correct: false },
      { scenario_id: "T2", ground_truth_label: "visible smoke", actual_category: "visible smoke", category_correct: true },
    ]),
    [{ scenarioId: "T1", truth: "visible smoke", predicted: "ERROR" }],
  );
  const heldRun = await buildRun((s) => assessViaModelAdapter(s, {}), "server model adapter (held while Spark stays off)", "held-state run, no live model");
  assert.match(renderRunReport(heldRun), /- IGN-001: visible smoke -> ERROR \(no assessment\)/);
});

test("report: miss-pair counts aggregate the misses — stub's dominant swap first, held run all ERROR", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  assert.deepEqual(
    computeMissPairs(run.records).map((p) => `${p.truth} -> ${p.predicted}: ${p.count}`),
    [
      "flame-like lighting -> visible flame: 2",
      "indeterminate -> steam or fog: 1",
      "obscured or distant hazard -> flame-like lighting: 1",
      "steam or fog -> visible smoke: 1",
      "visible smoke -> indeterminate: 1",
    ],
  );
  assert.deepEqual(computeMissPairs(run.records)[0].scenarioIds, ["IGN-010", "IGN-018"]);
  const report = renderRunReport(run);
  assert.match(report, /## Miss-pair counts/);
  assert.match(report, /\| flame-like lighting \| visible flame \| 2 \| IGN-010, IGN-018 \|/);
  assert.ok(report.indexOf("## Misses (6)") < report.indexOf("## Miss-pair counts"));
  assert.ok(report.indexOf("## Miss-pair counts") < report.indexOf("## Per-category confusion"));
  // Hand-built: ERROR sorts last among same-truth, same-count pairs, and
  // counts group across records; a correct record contributes no pair.
  assert.deepEqual(
    computeMissPairs([
      { scenario_id: "T1", ground_truth_label: "alpha", actual_category: null, category_correct: false },
      { scenario_id: "T2", ground_truth_label: "alpha", actual_category: "beta", category_correct: false },
      { scenario_id: "T3", ground_truth_label: "alpha", actual_category: "beta", category_correct: false },
      { scenario_id: "T4", ground_truth_label: "alpha", actual_category: "alpha", category_correct: true },
    ]).map((p) => `${p.truth} -> ${p.predicted}: ${p.count}`),
    ["alpha -> beta: 2", "alpha -> ERROR: 1"],
  );
  const heldRun = await buildRun((s) => assessViaModelAdapter(s, {}), "server model adapter (held while Spark stays off)", "held-state run, no live model");
  const heldPairs = computeMissPairs(heldRun.records);
  assert.equal(heldPairs.length, 7);
  assert.ok(heldPairs.every((p) => p.predicted === "ERROR"));
  assert.equal(heldPairs.find((p) => p.truth === "visible smoke").count, 3);
  assert.match(renderRunReport(heldRun), /\| visible smoke \| ERROR \| 3 \| IGN-001, IGN-003, IGN-016 \|/);
  const perfectRun = await buildRun(
    (s) => fakeAssessment(s.ground_truth_label),
    "server model adapter (held while Spark stays off)",
    "held-state run, no live model",
  );
  assert.deepEqual(computeMissPairs(perfectRun.records), []);
  assert.match(renderRunReport(perfectRun), /## Miss-pair counts/);
});

test("report: category correct lists the scenarios behind category accuracy, completing the category set", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  // The complement of the six stub misses: 14 of 20, category
  // accuracy 0.700. Sorted by scenario id, so the list never
  // depends on record order.
  assert.deepEqual(
    computeCategoryCorrect(run.records).map((e) => e.scenarioId),
    ["IGN-001", "IGN-002", "IGN-004", "IGN-005", "IGN-006", "IGN-008", "IGN-009", "IGN-011", "IGN-013", "IGN-014", "IGN-016", "IGN-017", "IGN-019", "IGN-020"],
  );
  assert.deepEqual(computeCategoryCorrect(run.records)[0], {
    scenarioId: "IGN-001",
    truth: "visible smoke",
    predicted: "visible smoke",
  });
  // Correct + misses account for every record, with no overlap.
  assert.equal(computeCategoryCorrect(run.records).length + computeMisses(run.records).length, run.records.length);
  // Hand-built: a wrong-category record and an unassessed record
  // are excluded; the list sorts by id regardless of input order.
  assert.deepEqual(
    computeCategoryCorrect([
      { scenario_id: "T3", ground_truth_label: "beta", actual_category: "beta", category_correct: true },
      { scenario_id: "T1", ground_truth_label: "alpha", actual_category: "gamma", category_correct: false },
      { scenario_id: "T2", ground_truth_label: "alpha", actual_category: null, category_correct: false },
      { scenario_id: "T4", ground_truth_label: "gamma", actual_category: "gamma", category_correct: true },
    ]).map((e) => e.scenarioId),
    ["T3", "T4"],
  );
  const report = renderRunReport(run);
  assert.match(report, /## Category correct/);
  assert.match(report, /14 correct of 20/);
  assert.match(report, /- IGN-001: visible smoke -> visible smoke/);
  assert.match(report, /- IGN-020: indeterminate -> indeterminate/);
  assert.ok(report.indexOf("## Miss-pair counts") < report.indexOf("## Category correct"));
  assert.ok(report.indexOf("## Category correct") < report.indexOf("## Per-category confusion"));
  // A held run predicts nothing, so its category-correct list is empty.
  const heldRun = await buildRun((s) => assessViaModelAdapter(s, {}), "server model adapter (held while Spark stays off)", "held-state run, no live model");
  assert.deepEqual(computeCategoryCorrect(heldRun.records), []);
  assert.match(renderRunReport(heldRun), /None: no scenario's predicted category matched its ground truth\./);
});

test("report: headline finding names nothing assessable on a held run, and no misses on a perfect run", async () => {
  const heldRun = await buildRun((s) => assessViaModelAdapter(s, {}), "server model adapter (held while Spark stays off)", "held-state run, no live model");
  const heldHeadline = computeCategoryHeadline(heldRun.records);
  assert.equal(heldHeadline.weakest, null);
  assert.equal(heldHeadline.mostConfused, null);
  assert.match(renderRunReport(heldRun), /No category finding: nothing in this run was assessed/);
  const perfectRun = await buildRun(
    (s) => fakeAssessment(s.ground_truth_label),
    "server model adapter (held while Spark stays off)",
    "held-state run, no live model",
  );
  assert.equal(computeCategoryHeadline(perfectRun.records).mostConfused, null);
  assert.match(renderRunReport(perfectRun), /No category misses: every assessed scenario matched its ground truth/);
});

test("report: headline tie-breaks are deterministic — most misses wins the weakest tie, names win the pair tie", () => {
  const headline = computeCategoryHeadline([
    { scenario_id: "T1", ground_truth_label: "alpha", actual_category: "alpha" },
    { scenario_id: "T2", ground_truth_label: "alpha", actual_category: "beta" },
    { scenario_id: "T3", ground_truth_label: "beta", actual_category: "beta" },
    { scenario_id: "T4", ground_truth_label: "beta", actual_category: "alpha" },
    { scenario_id: "T5", ground_truth_label: "beta", actual_category: "beta" },
    { scenario_id: "T6", ground_truth_label: "beta", actual_category: "gamma" },
  ]);
  // Both truth categories sit at 0.500, but beta has 2 misses to alpha's 1.
  assert.equal(headline.weakest.truth, "beta");
  // All three confused pairs have count 1; alpha -> beta wins alphabetically.
  assert.equal(headline.mostConfused.truth, "alpha");
  assert.equal(headline.mostConfused.predicted, "beta");
});

test("report: a held run's confusion is all ERROR and its confusables are unassessed, not clean", async () => {
  const run = await buildRun((s) => assessViaModelAdapter(s, {}), "server model adapter (held while Spark stays off)", "held-state run, no live model");
  const confusion = computeCategoryConfusion(run.records);
  assert.deepEqual(confusion.predictedCategories, ["ERROR"]);
  assert.equal(confusion.counts["visible smoke"]["ERROR"], 3); // IGN-001, IGN-003, IGN-016
  const confusables = computeConfusableNegatives(run.records);
  assert.ok(confusables.every((e) => e.assessed === 0 && e.falseAlarmCount === 0));
  const report = renderRunReport(run);
  assert.match(report, /## Per-category confusion/);
  assert.match(report, /none assessed/);
});

test("report: confusion ordering puts ERROR last and truth categories alphabetically", () => {
  const confusion = computeCategoryConfusion([
    { ground_truth_label: "visible smoke", actual_category: null },
    { ground_truth_label: "steam or fog", actual_category: "visible smoke" },
    { ground_truth_label: "steam or fog", actual_category: "steam or fog" },
  ]);
  assert.deepEqual(confusion.truthCategories, ["steam or fog", "visible smoke"]);
  assert.deepEqual(confusion.predictedCategories, ["steam or fog", "visible smoke", "ERROR"]);
});

test("report: invalid run JSON is rejected, not rendered", () => {
  assert.throws(() => renderRunReport({}), /invalid run JSON/);
  assert.throws(() => renderRunReport({ records: [], metrics: {} }), /invalid run JSON/);
  assert.throws(
    () =>
      renderRunReport({
        records: [{ scenario_id: "IGN-X", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: null }],
        metrics: { sample_size: 2, true_positives: 0, false_positives: 0, true_negatives: 0, false_negatives: 1, precision: null, recall: 0, false_positive_rate: 0, false_negative_rate: 1, category_accuracy: 0, latency_ms: { n: 1, mean: 0, median: 0, max: 0 }, errors: { count: 0, scenario_ids: [] } },
      }),
    /does not match/,
  );
});

test("report: the trio filenames are protected, a live filename is writable", () => {
  for (const name of PROTECTED_REPORT_NAMES) {
    assert.throws(() => assertWritableReportPath(join("/tmp", name)), /refusing to overwrite protected report/);
  }
  assert.doesNotThrow(() => assertWritableReportPath(join("/tmp", "live-run-report.md")));
});

test("report: per-scenario records carry a latency column — measured values, n/a when the record has none", async () => {
  const run = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  assert.ok(run.records.every((r) => typeof r.latency_ms === "number"));
  const report = renderRunReport(run);
  assert.match(report, /\| Scenario \| Truth \| Actual \| Alert correct \| Category correct \| Latency \(ms\) \| Outlier \| Error \|/);
  // Harness wall clock per scenario: a number with one decimal, never a fabricated zero.
  assert.match(report, /\| IGN-001 \| visible smoke \| visible smoke \| true \| true \| \d+\.\d \|/);
  // Hand-built: a record carrying no latency renders n/a, and a record
  // carrying a non-number latency is rejected, not rendered.
  const handRun = {
    source: "test source",
    generated: "test run",
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: true, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 1, true_positives: 1, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 1, mean: 0, median: 0, max: 0 }, errors: { count: 0, scenario_ids: [] } },
  };
  assert.match(renderRunReport(handRun), /\| IGN-T1 \| visible smoke \| visible smoke \| true \| true \| n\/a \|/);
  assert.throws(
    () => renderRunReport({ ...handRun, records: [{ ...handRun.records[0], latency_ms: "fast" }] }),
    /latency_ms: present but not a number/,
  );
});

test("report: latency outliers flag only latencies strictly above twice the median", async () => {
  const rec = (id, latencyMs) => ({
    scenario_id: id,
    ground_truth_label: "visible smoke",
    ...(latencyMs === undefined ? {} : { latency_ms: latencyMs }),
  });
  // Median of [10, 11, 12, 100] is 11.5, threshold 23: only the 100 flags.
  // A record with no latency is ignored, never a zero.
  assert.deepEqual(
    computeLatencyOutliers([rec("T1", 10), rec("T2", 11), rec("T3", 12), rec("T4", 100), rec("T5")]).map(
      (o) => o.scenarioId,
    ),
    ["T4"],
  );
  assert.deepEqual(
    computeLatencyOutliers([rec("T1", 10), rec("T2", 11), rec("T3", 12), rec("T4", 100), rec("T5")])[0],
    { scenarioId: "T4", truth: "visible smoke", latencyMs: 100, medianMs: 11.5, thresholdMs: 23 },
  );
  // Strict threshold: exactly twice the median (median 20, latency 40) does not flag;
  // one unit above it does.
  assert.deepEqual(computeLatencyOutliers([rec("T1", 10), rec("T2", 20), rec("T3", 40)]), []);
  assert.deepEqual(
    computeLatencyOutliers([rec("T1", 10), rec("T2", 20), rec("T3", 41)]).map((o) => o.scenarioId),
    ["T3"],
  );
  // No typical latency, no flag: fewer than two recorded latencies,
  // and a zero median (flagging on a zero baseline would single out
  // every positive latency, including a 5 ms one).
  assert.deepEqual(computeLatencyOutliers([rec("T1", 100)]), []);
  assert.deepEqual(computeLatencyOutliers([rec("T1")]), []);
  assert.deepEqual(computeLatencyOutliers([rec("T1", 0), rec("T2", 0), rec("T3", 5)]), []);
  // Rendered: the outlier row carries "yes" in the Outlier column, a
  // typical row carries an empty cell, and the header names the column.
  const handRun = {
    source: "test source",
    generated: "test run",
    records: [10, 11, 12, 100].map((latencyMs, i) => ({
      scenario_id: `IGN-T${i + 1}`,
      ground_truth_label: "visible smoke",
      alert_expected: true,
      alert_fired: true,
      alert_correct: true,
      category_correct: true,
      actual_category: "visible smoke",
      error: null,
      latency_ms: latencyMs,
    })),
    metrics: { sample_size: 4, true_positives: 4, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 4, mean: 33.25, median: 11.5, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const report = renderRunReport(handRun);
  assert.match(
    report,
    /\| Scenario \| Truth \| Actual \| Alert correct \| Category correct \| Latency \(ms\) \| Outlier \| Error \|/,
  );
  assert.match(report, /\| IGN-T4 \| visible smoke \| visible smoke \| true \| true \| 100\.0 \| yes \|/);
  assert.match(report, /\| IGN-T1 \| visible smoke \| visible smoke \| true \| true \| 10\.0 \|  \|/);
  // The existing latency-column test's header assertion is updated by
  // this feature: a stub render carries the new column too.
  const stubRun = await buildRun(assessStub, "stub (fixture, not a model)", "fixture run, no live model");
  assert.match(
    renderRunReport(stubRun),
    /\| Scenario \| Truth \| Actual \| Alert correct \| Category correct \| Latency \(ms\) \| Outlier \| Error \|/,
  );
});

test("report: error breakdown groups records by exact message, most frequent first", () => {
  const rec = (id, error) => ({
    scenario_id: id,
    ground_truth_label: "visible smoke",
    error,
  });
  // Count descending; ties alphabetical; null-error records excluded, never a blank group.
  assert.deepEqual(
    computeErrorBreakdown([
      rec("T1", "timeout"),
      rec("T2", "held refusal"),
      rec("T3", "timeout"),
      rec("T4", null),
      rec("T5", "held refusal"),
      rec("T6", "bad shape"),
    ]),
    [
      { message: "held refusal", count: 2, scenarioIds: ["T2", "T5"] },
      { message: "timeout", count: 2, scenarioIds: ["T1", "T3"] },
      { message: "bad shape", count: 1, scenarioIds: ["T6"] },
    ],
  );
  assert.deepEqual(computeErrorBreakdown([rec("T1", null)]), []);
  // Rendered: a mixed-error run splits the summary total into rows;
  // an error-free run says none instead of rendering an empty table.
  const mixedRun = {
    source: "test source",
    generated: "test run",
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: "timeout" },
      { scenario_id: "IGN-T2", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: "timeout" },
      { scenario_id: "IGN-T3", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: "bad shape | malformed" },
    ],
    metrics: { sample_size: 3, true_positives: 0, false_positives: 0, true_negatives: 0, false_negatives: 3, precision: null, recall: 0, false_positive_rate: 0, false_negative_rate: 1, category_accuracy: 0, latency_ms: { n: 0, mean: null, median: null, max: null }, errors: { count: 3, scenario_ids: ["IGN-T1", "IGN-T2", "IGN-T3"] } },
  };
  const mixed = renderRunReport(mixedRun);
  assert.match(mixed, /## Error breakdown/);
  assert.match(mixed, /\| timeout \| 2 \| IGN-T1, IGN-T2 \|/);
  // A pipe inside a message is escaped so it cannot break the table.
  assert.match(mixed, /\| bad shape \\\| malformed \| 1 \| IGN-T3 \|/);
  const cleanRun = {
    ...mixedRun,
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: true, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 1, true_positives: 1, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 0, mean: null, median: null, max: null }, errors: { count: 0, scenario_ids: [] } },
  };
  assert.match(renderRunReport(cleanRun), /None: no record in this run carries an error message\./);
});

test("report: latency distribution expands mean/median/max into quartiles and p90", () => {
  const rec = (id, latencyMs) => ({
    scenario_id: id,
    ground_truth_label: "visible smoke",
    ...(latencyMs === undefined ? {} : { latency_ms: latencyMs }),
  });
  // Linear interpolation on sorted latencies; the p50 is the
  // averaged-middle median, matching the summary line and the
  // outlier threshold. Compared within epsilon: interpolated
  // quantiles need not be exactly representable in binary.
  const approx = (dist, expected) => {
    assert.equal(dist.count, expected.count);
    for (const field of ["minMs", "p25Ms", "medianMs", "p75Ms", "p90Ms", "maxMs"]) {
      assert.ok(Math.abs(dist[field] - expected[field]) < 1e-9, `${field}: ${dist[field]} != ${expected[field]}`);
    }
  };
  approx(computeLatencyDistribution([rec("T1", 10), rec("T2", 20), rec("T3", 30), rec("T4", 40)]), {
    count: 4, minMs: 10, p25Ms: 17.5, medianMs: 25, p75Ms: 32.5, p90Ms: 37, maxMs: 40,
  });
  // A single recorded latency: every quantile is that value.
  // Records with no latency are ignored, never treated as zero.
  approx(computeLatencyDistribution([rec("T1", 50), rec("T2")]), {
    count: 1, minMs: 50, p25Ms: 50, medianMs: 50, p75Ms: 50, p90Ms: 50, maxMs: 50,
  });
  assert.equal(computeLatencyDistribution([rec("T1")]), null);
  // Rendered: values on a recorded run; a no-latency run says so, not zero.
  const base = {
    source: "test source",
    generated: "test run",
    records: [10, 20, 30, 40].map((latency_ms, i) => ({
      scenario_id: `IGN-T${i + 1}`, ground_truth_label: "visible smoke", alert_expected: true,
      alert_fired: true, alert_correct: true, category_correct: true,
      actual_category: "visible smoke", error: null, latency_ms,
    })),
    metrics: { sample_size: 4, true_positives: 4, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 4, mean: 25, median: 25, max: 40 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(base);
  assert.match(rendered, /## Latency distribution/);
  assert.match(rendered, /- Recorded latencies: 4 of 4 scenario\(s\)\./);
  assert.match(rendered, /- 25th percentile: 17\.5 ms\./);
  assert.match(rendered, /- Median: 25\.0 ms\./);
  assert.match(rendered, /- 90th percentile: 37\.0 ms\./);
  const noLatencyRun = {
    ...base,
    records: base.records.map(({ latency_ms, ...r }) => r),
    metrics: { ...base.metrics, latency_ms: { n: 0, mean: null, median: null, max: null } },
  };
  assert.match(renderRunReport(noLatencyRun), /No latency distribution: no record in this run carries a latency measurement\./);
});

test("report: latency outliers section names the flagged scenarios, with median and threshold", () => {
  const base = {
    source: "test source",
    generated: "test run",
    records: [10, 20, 30, 40, 100].map((latency_ms, i) => ({
      scenario_id: `IGN-T${i + 1}`, ground_truth_label: "visible smoke", alert_expected: true,
      alert_fired: true, alert_correct: true, category_correct: true,
      actual_category: "visible smoke", error: null, latency_ms,
    })),
    metrics: { sample_size: 5, true_positives: 5, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 5, mean: 40, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(base);
  assert.match(rendered, /## Latency outliers/);
  // The section sits after the distribution and before the Misses,
  // so the latency story reads in one place. Median 30, threshold
  // 60: only the 100 ms scenario is an outlier.
  assert.ok(rendered.indexOf("## Latency outliers") > rendered.indexOf("## Latency distribution"));
  assert.ok(rendered.indexOf("## Latency outliers") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| IGN-T5 \| visible smoke \| 100\.0 \| 30\.0 \| 60\.0 \|/);
  assert.ok(!rendered.includes("| IGN-T1 | visible smoke | 10.0"));
  // No-outlier run: latencies 10-40, median 25, threshold 50, nothing flagged.
  const clean = {
    ...base,
    records: base.records.slice(0, 4),
    metrics: { ...base.metrics, sample_size: 4, true_positives: 4, latency_ms: { n: 4, mean: 25, median: 25, max: 40 } },
  };
  assert.match(renderRunReport(clean), /None: no scenario's latency is more than twice the run's median recorded latency\./);
  // No-latency run: nothing recorded, so no outlier can be named.
  const noLatency = {
    ...base,
    records: base.records.map(({ latency_ms, ...r }) => r),
    metrics: { ...base.metrics, latency_ms: { n: 0, mean: null, median: null, max: null } },
  };
  assert.match(renderRunReport(noLatency), /None recorded: no record in this run carries a latency measurement, so no outlier can be named\./);
});

test("report: latency by category breaks recorded latencies down by truth category", () => {
  const rec = (id, truth, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    alert_expected: false,
    alert_fired: false,
    alert_correct: true,
    category_correct: true,
    actual_category: truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Smoke: 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // Steam: 100 + one unmeasured -> mean/median/max 100, recorded 1 of 2.
  // No hazard: nothing recorded -> null statistics, never zero.
  assert.deepEqual(
    computeLatencyByCategory([
      rec("IGN-T2", "visible smoke", 30),
      rec("IGN-T1", "visible smoke", 10),
      rec("IGN-T3", "steam or fog", 100),
      rec("IGN-T4", "steam or fog"),
      rec("IGN-T5", "no hazard visible"),
    ]),
    [
      { truth: "no hazard visible", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
      { truth: "steam or fog", total: 2, recorded: 1, meanMs: 100, medianMs: 100, maxMs: 100 },
      { truth: "visible smoke", total: 2, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
    ],
  );
  // Rendered: section after Latency outliers, before Misses, rows
  // sorted alphabetically by truth, n/a for the unmeasured category.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", 10),
      rec("IGN-T2", "visible smoke", 30),
      rec("IGN-T3", "steam or fog", 100),
      rec("IGN-T4", "steam or fog"),
      rec("IGN-T5", "no hazard visible"),
    ],
    metrics: { sample_size: 5, true_positives: 0, false_positives: 0, true_negatives: 5, false_negatives: 0, precision: null, recall: null, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by category/);
  assert.ok(rendered.indexOf("## Latency by category") > rendered.indexOf("## Latency outliers"));
  assert.ok(rendered.indexOf("## Latency by category") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| visible smoke \| 2 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| steam or fog \| 2 \| 1 \| 100\.0 \| 100\.0 \| 100\.0 \|/);
  assert.match(rendered, /\| no hazard visible \| 1 \| 0 \| n\/a \| n\/a \| n\/a \|/);
});

test("report: latency by outcome breaks recorded latencies down by correct/miss/unassessed", () => {
  const rec = (id, truth, actual, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: false,
    alert_fired: false,
    alert_correct: true,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Correct: 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // Miss: 100 + one unmeasured -> mean/median/max 100, recorded 1 of 2.
  // Unassessed: nothing recorded -> null statistics, never zero.
  // All three rows always render, in fixed correct/miss/unassessed
  // order, so the totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByOutcome([
      rec("IGN-T2", "visible smoke", "visible smoke", 30),
      rec("IGN-T1", "visible smoke", "visible smoke", 10),
      rec("IGN-T3", "steam or fog", "visible smoke", 100),
      rec("IGN-T4", "steam or fog", "visible smoke"),
      rec("IGN-T5", "no hazard visible", null),
    ]),
    [
      { outcome: "correct", total: 2, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
      { outcome: "miss", total: 2, recorded: 1, meanMs: 100, medianMs: 100, maxMs: 100 },
      { outcome: "unassessed", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
    ],
  );
  // Rendered: section after Latency by category, before Misses, rows
  // in fixed order, n/a for the unmeasured group.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", 10),
      rec("IGN-T2", "visible smoke", "visible smoke", 30),
      rec("IGN-T3", "steam or fog", "visible smoke", 100),
      rec("IGN-T4", "steam or fog", "visible smoke"),
      rec("IGN-T5", "no hazard visible", null),
    ],
    metrics: { sample_size: 5, true_positives: 0, false_positives: 0, true_negatives: 5, false_negatives: 0, precision: null, recall: null, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by outcome/);
  assert.ok(rendered.indexOf("## Latency by outcome") > rendered.indexOf("## Latency by category"));
  assert.ok(rendered.indexOf("## Latency by outcome") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| correct \| 2 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| miss \| 2 \| 1 \| 100\.0 \| 100\.0 \| 100\.0 \|/);
  assert.match(rendered, /\| unassessed \| 1 \| 0 \| n\/a \| n\/a \| n\/a \|/);
});

test("report: latency by alert outcome breaks recorded latencies down by TP/TN/FP/FN", () => {
  const rec = (id, truth, actual, expected, fired, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
    alert_correct: expected === fired,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // True positive: 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // True negative: 40 + one unmeasured -> mean/median/max 40, recorded 1 of 2.
  // False positive: nothing recorded -> null statistics, never zero.
  // False negative: 200 -> mean/median/max 200, recorded 1 of 1.
  // All four rows always render, in fixed TP/TN/FP/FN order, so the
  // totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByAlertOutcome([
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T3", "steam or fog", "steam or fog", false, false, 40),
      rec("IGN-T4", "no hazard visible", "no hazard visible", false, false),
      rec("IGN-T5", "steam or fog", "visible flame", false, true),
      rec("IGN-T6", "visible flame", null, true, false, 200),
    ]),
    [
      { outcome: "true positive", total: 2, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
      { outcome: "true negative", total: 2, recorded: 1, meanMs: 40, medianMs: 40, maxMs: 40 },
      { outcome: "false positive", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
      { outcome: "false negative", total: 1, recorded: 1, meanMs: 200, medianMs: 200, maxMs: 200 },
    ],
  );
  // Rendered: section after Latency by outcome, before Misses, rows
  // in fixed order, n/a for the unmeasured group.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T3", "steam or fog", "steam or fog", false, false, 40),
      rec("IGN-T4", "no hazard visible", "no hazard visible", false, false),
      rec("IGN-T5", "steam or fog", "visible flame", false, true),
      rec("IGN-T6", "visible flame", null, true, false, 200),
    ],
    metrics: { sample_size: 6, true_positives: 2, false_positives: 1, true_negatives: 2, false_negatives: 1, precision: 0.6667, recall: 0.6667, false_positive_rate: 0.3333, false_negative_rate: 0.3333, category_accuracy: 0.6667, latency_ms: { n: 4, mean: 70, median: 35, max: 200 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by alert outcome/);
  assert.ok(rendered.indexOf("## Latency by alert outcome") > rendered.indexOf("## Latency by outcome"));
  assert.ok(rendered.indexOf("## Latency by alert outcome") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| true positive \| 2 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| true negative \| 2 \| 1 \| 40\.0 \| 40\.0 \| 40\.0 \|/);
  assert.match(rendered, /\| false positive \| 1 \| 0 \| n\/a \| n\/a \| n\/a \|/);
  assert.match(rendered, /\| false negative \| 1 \| 1 \| 200\.0 \| 200\.0 \| 200\.0 \|/);
});

test("report: latency by alert correctness collapses TP/TN vs FP/FN into two rows", () => {
  const rec = (id, truth, actual, expected, fired, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
    alert_correct: expected === fired,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Alert correct: 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // Alert error: 100 + one unmeasured -> mean/median/max 100, recorded 1 of 2.
  // Both rows always render, in fixed alert-correct/alert-error order,
  // so the totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByAlertCorrectness([
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T3", "steam or fog", "visible smoke", false, true, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ]),
    [
      { outcome: "alert correct", total: 2, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
      { outcome: "alert error", total: 2, recorded: 1, meanMs: 100, medianMs: 100, maxMs: 100 },
    ],
  );
  // A group with no recorded latency shows null statistics, never zero.
  assert.deepEqual(
    computeLatencyByAlertCorrectness([
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "steam or fog", "visible smoke", false, true),
    ]),
    [
      { outcome: "alert correct", total: 1, recorded: 1, meanMs: 10, medianMs: 10, maxMs: 10 },
      { outcome: "alert error", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
    ],
  );
  // Rendered: section after Latency by alert outcome, before Misses,
  // rows in fixed order, n/a for the unmeasured group in the second run.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T3", "steam or fog", "visible smoke", false, true, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ],
    metrics: { sample_size: 4, true_positives: 2, false_positives: 1, true_negatives: 0, false_negatives: 1, precision: 0.6667, recall: 0.6667, false_positive_rate: 1, false_negative_rate: 0.3333, category_accuracy: 0.5, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by alert correctness/);
  assert.ok(rendered.indexOf("## Latency by alert correctness") > rendered.indexOf("## Latency by alert outcome"));
  assert.ok(rendered.indexOf("## Latency by alert correctness") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| alert correct \| 2 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| alert error \| 2 \| 1 \| 100\.0 \| 100\.0 \| 100\.0 \|/);
});

test("report: latency by alert expectation splits TP/FN vs TN/FP into two rows", () => {
  const rec = (id, truth, actual, expected, fired, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
    alert_correct: expected === fired,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Alert expected: 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // Alert not expected: 100 + one unmeasured -> mean/median/max 100, recorded 1 of 2.
  // Both rows always render, in fixed alert-expected/alert-not-expected
  // order, so the totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByAlertExpectation([
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T3", "steam or fog", "visible smoke", false, true, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ]),
    [
      { outcome: "alert expected", total: 3, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
      { outcome: "alert not expected", total: 1, recorded: 1, meanMs: 100, medianMs: 100, maxMs: 100 },
    ],
  );
  // A group with no recorded latency shows null statistics, never zero.
  assert.deepEqual(
    computeLatencyByAlertExpectation([
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "steam or fog", "steam or fog", false, false),
    ]),
    [
      { outcome: "alert expected", total: 1, recorded: 1, meanMs: 10, medianMs: 10, maxMs: 10 },
      { outcome: "alert not expected", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
    ],
  );
  // Rendered: section after Latency by alert correctness, before Misses,
  // rows in fixed order, n/a for the unmeasured group in the second run.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T3", "steam or fog", "visible smoke", false, true, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ],
    metrics: { sample_size: 4, true_positives: 2, false_positives: 1, true_negatives: 0, false_negatives: 1, precision: 0.6667, recall: 0.6667, false_positive_rate: 1, false_negative_rate: 0.3333, category_accuracy: 0.5, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by alert expectation/);
  assert.ok(rendered.indexOf("## Latency by alert expectation") > rendered.indexOf("## Latency by alert correctness"));
  assert.ok(rendered.indexOf("## Latency by alert expectation") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| alert expected \| 3 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| alert not expected \| 1 \| 1 \| 100\.0 \| 100\.0 \| 100\.0 \|/);
});

test("report: latency by alert fired splits TP+FP from TN+FN", () => {
  const rec = (id, truth, actual, expected, fired, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
    alert_correct: expected === fired,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Alert fired: 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // Alert not fired: 100 + one unmeasured -> mean/median/max 100, recorded 1 of 2.
  // Both rows always render, in fixed alert-fired/alert-not-fired
  // order, so the totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByAlertFired([
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T3", "steam or fog", "steam or fog", false, false, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ]),
    [
      { outcome: "alert fired", total: 2, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
      { outcome: "alert not fired", total: 2, recorded: 1, meanMs: 100, medianMs: 100, maxMs: 100 },
    ],
  );
  // A group with no recorded latency shows null statistics, never zero.
  assert.deepEqual(
    computeLatencyByAlertFired([
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "steam or fog", "steam or fog", false, false),
    ]),
    [
      { outcome: "alert fired", total: 1, recorded: 1, meanMs: 10, medianMs: 10, maxMs: 10 },
      { outcome: "alert not fired", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
    ],
  );
  // Rendered: section after Latency by alert expectation, before Misses,
  // rows in fixed order, n/a for the unmeasured group in the second run.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "visible smoke", "visible smoke", true, true, 30),
      rec("IGN-T3", "steam or fog", "steam or fog", false, false, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ],
    metrics: { sample_size: 4, true_positives: 2, false_positives: 0, true_negatives: 1, false_negatives: 1, precision: 1, recall: 0.6667, false_positive_rate: 0, false_negative_rate: 0.3333, category_accuracy: 0.75, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by alert fired/);
  assert.ok(rendered.indexOf("## Latency by alert fired") > rendered.indexOf("## Latency by alert expectation"));
  assert.ok(rendered.indexOf("## Latency by alert fired") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| alert fired \| 2 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| alert not fired \| 2 \| 1 \| 100\.0 \| 100\.0 \| 100\.0 \|/);
});

test("report: latency by assessed splits assessed from unassessed", () => {
  const rec = (id, truth, actual, expected, fired, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
    alert_correct: expected === fired,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Assessed (correct + miss): 10, 30 -> mean 20, median 20, max 30, recorded 2 of 2.
  // Unassessed: 100 + one unmeasured -> mean/median/max 100, recorded 1 of 2.
  // Both rows always render, in fixed assessed/unassessed
  // order, so the totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByAssessed([
      rec("IGN-T2", "visible smoke", "visible flame", true, true, 30),
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T3", "steam or fog", null, false, false, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ]),
    [
      { outcome: "assessed", total: 2, recorded: 2, meanMs: 20, medianMs: 20, maxMs: 30 },
      { outcome: "unassessed", total: 2, recorded: 1, meanMs: 100, medianMs: 100, maxMs: 100 },
    ],
  );
  // A group with no recorded latency shows null statistics, never zero.
  assert.deepEqual(
    computeLatencyByAssessed([
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "steam or fog", null, false, false),
    ]),
    [
      { outcome: "assessed", total: 1, recorded: 1, meanMs: 10, medianMs: 10, maxMs: 10 },
      { outcome: "unassessed", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
    ],
  );
  // Rendered: section after Latency by alert fired, before Misses,
  // rows in fixed order, n/a for the unmeasured group in the second run.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "visible smoke", "visible flame", true, true, 30),
      rec("IGN-T3", "steam or fog", null, false, false, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ],
    metrics: { sample_size: 4, true_positives: 1, false_positives: 0, true_negatives: 1, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 0.25, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by assessed/);
  assert.ok(rendered.indexOf("## Latency by assessed") > rendered.indexOf("## Latency by alert fired"));
  assert.ok(rendered.indexOf("## Latency by assessed") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| assessed \| 2 \| 2 \| 20\.0 \| 20\.0 \| 30\.0 \|/);
  assert.match(rendered, /\| unassessed \| 2 \| 1 \| 100\.0 \| 100\.0 \| 100\.0 \|/);
});

test("report: latency by category correctness splits correct from incorrect", () => {
  const rec = (id, truth, actual, expected, fired, latency_ms) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
    alert_correct: expected === fired,
    category_correct: actual === truth,
    error: null,
    ...(latency_ms === undefined ? {} : { latency_ms }),
  });
  // Category correct: 10 -> mean/median/max 10, recorded 1 of 1.
  // Category incorrect (miss + unassessed): 30, 100 + one unmeasured
  // -> mean 65, median 65, max 100, recorded 2 of 3.
  // Both rows always render, in fixed correct/incorrect order, so
  // the totals sum to the sample size.
  assert.deepEqual(
    computeLatencyByCategoryCorrectness([
      rec("IGN-T2", "visible smoke", "visible flame", true, true, 30),
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T3", "steam or fog", null, false, false, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ]),
    [
      { outcome: "category correct", total: 1, recorded: 1, meanMs: 10, medianMs: 10, maxMs: 10 },
      { outcome: "category incorrect", total: 3, recorded: 2, meanMs: 65, medianMs: 65, maxMs: 100 },
    ],
  );
  // A group with no recorded latency shows null statistics, never zero.
  assert.deepEqual(
    computeLatencyByCategoryCorrectness([
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "steam or fog", null, false, false),
    ]),
    [
      { outcome: "category correct", total: 1, recorded: 1, meanMs: 10, medianMs: 10, maxMs: 10 },
      { outcome: "category incorrect", total: 1, recorded: 0, meanMs: null, medianMs: null, maxMs: null },
    ],
  );
  // Rendered: section after Latency by assessed, before Misses,
  // rows in fixed order, n/a for the unmeasured group in the second run.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      rec("IGN-T1", "visible smoke", "visible smoke", true, true, 10),
      rec("IGN-T2", "visible smoke", "visible flame", true, true, 30),
      rec("IGN-T3", "steam or fog", null, false, false, 100),
      rec("IGN-T4", "visible flame", null, true, false),
    ],
    metrics: { sample_size: 4, true_positives: 1, false_positives: 0, true_negatives: 1, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 0.25, latency_ms: { n: 3, mean: 46.666, median: 30, max: 100 }, errors: { count: 0, scenario_ids: [] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Latency by category correctness/);
  assert.ok(rendered.indexOf("## Latency by category correctness") > rendered.indexOf("## Latency by assessed"));
  assert.ok(rendered.indexOf("## Latency by category correctness") < rendered.indexOf("## Misses"));
  assert.match(rendered, /\| category correct \| 1 \| 1 \| 10\.0 \| 10\.0 \| 10\.0 \|/);
  assert.match(rendered, /\| category incorrect \| 3 \| 2 \| 65\.0 \| 65\.0 \| 100\.0 \|/);
});

test("report: alert errors split FP/FN scenarios from category misses", () => {
  const rec = (id, truth, actual, expected, fired) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
  });
  // FP: fired where none expected. FN: expected but never fired.
  // Alert-correct records appear in neither list, even when the
  // category is wrong (right alert, wrong category is a category
  // miss, not an alert error). Lists sort by scenario id, so the
  // section never depends on record order.
  assert.deepEqual(
    computeAlertErrors([
      rec("T3", "steam or fog", "visible smoke", false, true),
      rec("T1", "visible smoke", null, true, false),
      rec("T2", "visible smoke", "visible flame", true, true),
      rec("T4", "no hazard visible", "no hazard visible", false, false),
      rec("T5", "visible flame", "visible flame", true, true),
    ]),
    {
      falsePositives: [{ scenarioId: "T3", truth: "steam or fog", predicted: "visible smoke" }],
      falseNegatives: [{ scenarioId: "T1", truth: "visible smoke", predicted: "ERROR" }],
    },
  );
  assert.deepEqual(computeAlertErrors([rec("T1", "visible smoke", "visible smoke", true, true)]), {
    falsePositives: [],
    falseNegatives: [],
  });
  // Rendered: both lists with truth -> predicted; a clean run says none.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: "held" },
      { scenario_id: "IGN-T2", ground_truth_label: "steam or fog", alert_expected: false, alert_fired: true, alert_correct: false, category_correct: false, actual_category: "visible smoke", error: null },
      { scenario_id: "IGN-T3", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: true, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 3, true_positives: 1, false_positives: 1, true_negatives: 0, false_negatives: 1, precision: 0.5, recall: 0.5, false_positive_rate: 1, false_negative_rate: 0.5, category_accuracy: 1 / 3, latency_ms: { n: 0, mean: null, median: null, max: null }, errors: { count: 1, scenario_ids: ["IGN-T1"] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Alert errors/);
  assert.match(rendered, /- False positives \(1\):\n  - IGN-T2: steam or fog -> visible smoke/);
  assert.match(rendered, /- False negatives \(1\):\n  - IGN-T1: visible smoke -> ERROR \(no assessment\)/);
  const cleanRun = {
    ...run,
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: true, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 1, true_positives: 1, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 0, mean: null, median: null, max: null }, errors: { count: 0, scenario_ids: [] } },
  };
  assert.match(renderRunReport(cleanRun), /None: every scenario's alert outcome matched its expectation\./);
});

test("report: alert correct splits TP/TN scenarios from alert errors", () => {
  const rec = (id, truth, actual, expected, fired) => ({
    scenario_id: id,
    ground_truth_label: truth,
    actual_category: actual,
    alert_expected: expected,
    alert_fired: fired,
  });
  // TP: expected alert fired. TN: no alert expected, none fired.
  // Alert-error records appear in neither list, and the lists sort
  // by scenario id, so the section never depends on record order.
  // A right-alert, wrong-category record is a TP (an alert success,
  // a category miss), and an unassessed non-alert record is a TN
  // by the fired/expected definition, reading as ERROR.
  assert.deepEqual(
    computeAlertCorrect([
      rec("T3", "steam or fog", "visible smoke", false, true),
      rec("T1", "visible smoke", "visible flame", true, true),
      rec("T4", "no hazard visible", "no hazard visible", false, false),
      rec("T2", "visible smoke", null, true, false),
      rec("T5", "visible flame", "visible flame", true, true),
      rec("T6", "steam or fog", null, false, false),
    ]),
    {
      truePositives: [
        { scenarioId: "T1", truth: "visible smoke", predicted: "visible flame" },
        { scenarioId: "T5", truth: "visible flame", predicted: "visible flame" },
      ],
      trueNegatives: [
        { scenarioId: "T4", truth: "no hazard visible", predicted: "no hazard visible" },
        { scenarioId: "T6", truth: "steam or fog", predicted: "ERROR" },
      ],
    },
  );
  assert.deepEqual(computeAlertCorrect([rec("T1", "visible smoke", null, true, false)]), {
    truePositives: [],
    trueNegatives: [],
  });
  // Rendered: both lists with truth -> predicted; a run with no
  // alert-correct scenario says none.
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: false, actual_category: "visible flame", error: null },
      { scenario_id: "IGN-T2", ground_truth_label: "no hazard visible", alert_expected: false, alert_fired: false, alert_correct: true, category_correct: true, actual_category: "no hazard visible", error: null },
      { scenario_id: "IGN-T3", ground_truth_label: "steam or fog", alert_expected: false, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: "held" },
    ],
    metrics: { sample_size: 3, true_positives: 1, false_positives: 0, true_negatives: 2, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1 / 3, latency_ms: { n: 0, mean: null, median: null, max: null }, errors: { count: 1, scenario_ids: ["IGN-T3"] } },
  };
  const rendered = renderRunReport(run);
  assert.match(rendered, /## Alert correct/);
  assert.match(rendered, /- True positives \(1\):\n  - IGN-T1: visible smoke -> visible flame/);
  assert.match(rendered, /- True negatives \(2\):\n  - IGN-T2: no hazard visible -> no hazard visible\n  - IGN-T3: steam or fog -> ERROR \(no assessment\)/);
  const allErrorRun = {
    ...run,
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: false, alert_correct: false, category_correct: false, actual_category: null, error: "held" },
      { scenario_id: "IGN-T2", ground_truth_label: "steam or fog", alert_expected: false, alert_fired: true, alert_correct: false, category_correct: false, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 2, true_positives: 0, false_positives: 1, true_negatives: 0, false_negatives: 1, precision: 0, recall: 0, false_positive_rate: 1, false_negative_rate: 1, category_accuracy: 0, latency_ms: { n: 0, mean: null, median: null, max: null }, errors: { count: 1, scenario_ids: ["IGN-T1"] } },
  };
  assert.match(renderRunReport(allErrorRun), /None: no scenario's alert outcome matched its expectation\./);
});

test("report: CLI renders a run JSON to a file and refuses a trio target", () => {
  const dir = mkdtempSync(join(tmpdir(), "ignis-report-"));
  const runPath = join(dir, "run.json");
  const outPath = join(dir, "live-run-report.md");
  const run = {
    source: "test source",
    generated: "test run",
    records: [
      { scenario_id: "IGN-T1", ground_truth_label: "visible smoke", alert_expected: true, alert_fired: true, alert_correct: true, category_correct: true, actual_category: "visible smoke", error: null },
    ],
    metrics: { sample_size: 1, true_positives: 1, false_positives: 0, true_negatives: 0, false_negatives: 0, precision: 1, recall: 1, false_positive_rate: 0, false_negative_rate: 0, category_accuracy: 1, latency_ms: { n: 1, mean: 0, median: 0, max: 0 }, errors: { count: 0, scenario_ids: [] } },
  };
  writeFileSync(runPath, JSON.stringify(run));
  execFileSync(process.execPath, [join(here, "report.mjs"), runPath, "--out", outPath], { encoding: "utf8" });
  assert.match(readFileSync(outPath, "utf8"), /^# Meta Ignis live-model run report/m);
  assert.throws(
    () => execFileSync(process.execPath, [join(here, "report.mjs"), runPath, "--out", join(dir, "baseline-run-report.md")], { encoding: "utf8" }),
    /refusing to overwrite protected report/,
  );
});
