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
  computeCategoryHeadline,
  computeConfusableNegatives,
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
