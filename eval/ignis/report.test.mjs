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
  computeCategoryRates,
  computeConfusableNegatives,
  computeErrorBreakdown,
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
