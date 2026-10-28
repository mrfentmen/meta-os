// Meta Ignis run-report renderer (Rowan's lane).
//
// Turns a run JSON file produced by `node eval/ignis/run.mjs --out <path>`
// into the markdown report format used by the report trio
// (fixture-run-report.md, held-state-run-report.md,
// baseline-run-report.md). This file makes NO model call and reads NO
// key: it only renders numbers already measured by a run.
//
// Classification is by record evidence, not by the run's labels alone,
// because run.mjs labels predate the test phase and a stale label must
// never upgrade or downgrade a run:
//   1. every record errors with the held refusal -> "held-state"
//   2. source/generated names a fixture, baseline, or stub -> "fixture"
//   3. any record carries an actual category -> "live-model"
//   4. every record errors (some other way) -> "errored"
//   5. otherwise -> "unlabelled"
// Rule 3 is what lets a future live run render as live even if it was
// produced by an older run.mjs whose source string still says "held":
// assessments in the records beat a stale label. Rule 2 is what keeps
// a stub run a fixture even though it also carries assessments: a
// named fixture source is explicit, a stale held label is not.
//
// The renderer never rewrites the trio reports: --out to one of the
// trio filenames is refused, so a live run lands in its own file
// (live-run-report.md) and never edits a fixture/held/baseline record.
//
// Alert-level metrics hide which categories are confused: a run can
// look respectable while systematically swapping one category for
// another (the stub swaps steam/fog for smoke and flame-like lighting
// for flame). The report therefore also renders a truth-vs-predicted
// category table, and a confusable-negative breakdown counting the
// non-alert scenes (steam or fog, flame-like lighting) that were
// predicted as an alert category (visible smoke, visible flame).
// Errored records appear in the table under ERROR: they are failures,
// not confusions. Above the full table, a headline finding names the
// weakest truth category and the most-confused pair, so the single
// biggest failure mode is visible without reading the whole matrix.
// A per-category rate table backs the headline: one correct/total
// rate per truth category, so the weakest claim is checkable without
// counting the confusion matrix. The Misses section names each miss
// as truth -> predicted, so a miss is diagnosable without
// cross-referencing the per-scenario table; unassessed records show
// ERROR, matching the confusion table's convention.
// A run's numbers are only ever compared against a baseline run the
// caller supplies; the bar is recall AND category accuracy, never
// precision alone (the baseline never fires a false alarm by
// construction, so its precision is vacuous, not perfect).

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { basename, dirname } from "node:path";

export const PROTECTED_REPORT_NAMES = [
  "fixture-run-report.md",
  "held-state-run-report.md",
  "baseline-run-report.md",
];

const KIND_TITLES = {
  fixture: "fixture",
  "held-state": "held-state",
  "live-model": "live-model",
  errored: "errored",
  unlabelled: "unlabelled",
};

const KIND_INTRO = {
  fixture:
    "This is a FIXTURE run: the source is a local stand-in, not a model. " +
    "No number here describes model performance, and none may be quoted as such.",
  "held-state":
    "This is a HELD-STATE run: every scenario records the server adapter's " +
    "refusal, because live model calls are held. These numbers describe source " +
    "availability, not model performance: the run predicts nothing.",
  "live-model":
    "This is a LIVE-MODEL run: the source returned real assessments for these " +
    "scenarios. Its numbers describe this scenario set against the wired source " +
    "only — not real-hardware camera input, and not photographs, unless the run " +
    "itself was produced from real frames.",
  errored:
    "This run ERRORED on every scenario and produced no assessment. It cannot " +
    "be quoted as a model result, and its confusion counts describe the failure, " +
    "not detection.",
  unlabelled:
    "This run is UNLABELLED: it carries neither a named fixture source nor " +
    "assessments that would make it a live run. Do not quote it as a model " +
    "result until its source is identified.",
};

function isObject(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function isNumberOrNull(v) {
  return v === null || typeof v === "number";
}

export function validateRunJson(run) {
  const errors = [];
  if (!isObject(run)) return ["run is not an object"];
  if (!Array.isArray(run.records) || run.records.length === 0) {
    errors.push("records: missing or empty");
  } else {
    run.records.forEach((r, i) => {
      const prefix = `records[${i}]`;
      if (!isObject(r)) {
        errors.push(`${prefix}: not an object`);
        return;
      }
      if (typeof r.scenario_id !== "string" || r.scenario_id.length === 0) {
        errors.push(`${prefix}.scenario_id: missing or not a string`);
      }
      if (typeof r.ground_truth_label !== "string" || r.ground_truth_label.length === 0) {
        errors.push(`${prefix}.ground_truth_label: missing or not a string`);
      }
      if (typeof r.alert_expected !== "boolean") errors.push(`${prefix}.alert_expected: not a boolean`);
      if (typeof r.alert_fired !== "boolean") errors.push(`${prefix}.alert_fired: not a boolean`);
      if (typeof r.alert_correct !== "boolean") errors.push(`${prefix}.alert_correct: not a boolean`);
      if (typeof r.category_correct !== "boolean") errors.push(`${prefix}.category_correct: not a boolean`);
      if (!(typeof r.actual_category === "string" || r.actual_category === null)) {
        errors.push(`${prefix}.actual_category: neither a string nor null`);
      }
      if (!(typeof r.error === "string" || r.error === null)) {
        errors.push(`${prefix}.error: neither a string nor null`);
      }
    });
  }
  if (!isObject(run.metrics)) {
    errors.push("metrics: missing or not an object");
  } else {
    const m = run.metrics;
    for (const field of [
      "sample_size",
      "true_positives",
      "false_positives",
      "true_negatives",
      "false_negatives",
    ]) {
      if (typeof m[field] !== "number") errors.push(`metrics.${field}: missing or not a number`);
    }
    for (const field of ["recall", "false_positive_rate", "false_negative_rate", "category_accuracy"]) {
      if (!isNumberOrNull(m[field])) errors.push(`metrics.${field}: neither a number nor null`);
    }
    if (!isNumberOrNull(m.precision)) errors.push("metrics.precision: neither a number nor null");
    if (!isObject(m.latency_ms)) {
      errors.push("metrics.latency_ms: missing or not an object");
    } else {
      if (typeof m.latency_ms.n !== "number") errors.push("metrics.latency_ms.n: missing or not a number");
      for (const field of ["mean", "median", "max"]) {
        if (!isNumberOrNull(m.latency_ms[field])) errors.push(`metrics.latency_ms.${field}: neither a number nor null`);
      }
    }
    if (!isObject(m.errors) || typeof m.errors.count !== "number" || !Array.isArray(m.errors.scenario_ids)) {
      errors.push("metrics.errors: missing count or scenario_ids");
    }
    if (Array.isArray(run.records) && typeof m.sample_size === "number" && m.sample_size !== run.records.length) {
      errors.push(`metrics.sample_size ${m.sample_size} does not match ${run.records.length} records`);
    }
  }
  return errors;
}

export function classifyRunKind(run) {
  const records = Array.isArray(run.records) ? run.records : [];
  const labelText = `${run.source || ""} ${run.generated || ""}`;
  const allHeld =
    records.length > 0 &&
    records.every((r) => typeof r.error === "string" && /Live model calls are held/.test(r.error));
  if (allHeld) return "held-state";
  if (/fixture|baseline|stub/i.test(labelText)) return "fixture";
  if (records.some((r) => r.actual_category !== null)) return "live-model";
  if (records.length > 0 && records.every((r) => r.error !== null)) return "errored";
  return "unlabelled";
}

// The headline finding names the single biggest failure mode before
// the full table, so a reader need not read the whole matrix: the
// truth category with the lowest category-correct rate, and the
// most-confused truth -> predicted pair. Rates are correct / total
// for the truth category, matching category-accuracy semantics —
// errored records count as misses, not as excused. A truth category
// is only ranked when at least one of its scenarios was assessed;
// when nothing in the run was assessed at all there is no weakest
// category to name, and the headline says so instead of inventing
// one. The most-confused pair counts only real predicted categories:
// ERROR is a failure, not a confusion, so a run whose misses are all
// errors has no most-confused pair. Ties break deterministically —
// weakest by most misses then truth name, pair by truth then
// predicted name — so the headline never depends on record order.
export function computeCategoryHeadline(records) {
  const perCategory = {};
  for (const r of records) {
    perCategory[r.ground_truth_label] ??= { truth: r.ground_truth_label, total: 0, correct: 0, assessed: 0 };
    const entry = perCategory[r.ground_truth_label];
    entry.total += 1;
    if (r.actual_category !== null) entry.assessed += 1;
    if (r.actual_category === r.ground_truth_label) entry.correct += 1;
  }
  const ranked = Object.values(perCategory)
    .filter((e) => e.assessed > 0)
    .map((e) => ({ ...e, rate: e.total === 0 ? 0 : e.correct / e.total }))
    .sort((a, b) => {
      if (a.rate !== b.rate) return a.rate - b.rate;
      const missesA = a.total - a.correct;
      const missesB = b.total - b.correct;
      if (missesA !== missesB) return missesB - missesA;
      return a.truth < b.truth ? -1 : a.truth > b.truth ? 1 : 0;
    });
  const weakest = ranked.length > 0 ? ranked[0] : null;
  const pairCounts = {};
  for (const r of records) {
    if (r.actual_category === null || r.actual_category === r.ground_truth_label) continue;
    pairCounts[r.ground_truth_label] ??= {};
    pairCounts[r.ground_truth_label][r.actual_category] ??= [];
    pairCounts[r.ground_truth_label][r.actual_category].push(r.scenario_id);
  }
  const pairs = [];
  for (const truth of Object.keys(pairCounts).sort()) {
    for (const predicted of Object.keys(pairCounts[truth]).sort()) {
      pairs.push({ truth, predicted, count: pairCounts[truth][predicted].length, scenarioIds: pairCounts[truth][predicted] });
    }
  }
  pairs.sort((a, b) => {
    if (a.count !== b.count) return b.count - a.count;
    if (a.truth !== b.truth) return a.truth < b.truth ? -1 : 1;
    return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
  });
  return { weakest, mostConfused: pairs.length > 0 ? pairs[0] : null, perCategory: ranked };
}

// One rate row per truth category present in the records, sorted
// alphabetically by truth name: correct predictions over all of that
// category's scenarios. The rate uses the headline's definition —
// correct / total, with records that produced no assessment counting
// as misses, matching category-accuracy semantics — so the headline's
// weakest category is the lowest row of this table (headline ties
// break by most misses, then truth name). The assessed count is
// carried alongside so a held-state row of 0.000 reads as "nothing
// assessed", not as a measured zero.
export function computeCategoryRates(records) {
  const perCategory = {};
  for (const r of records) {
    perCategory[r.ground_truth_label] ??= { truth: r.ground_truth_label, total: 0, correct: 0, assessed: 0 };
    const entry = perCategory[r.ground_truth_label];
    entry.total += 1;
    if (r.actual_category !== null) entry.assessed += 1;
    if (r.actual_category === r.ground_truth_label) entry.correct += 1;
  }
  return Object.values(perCategory)
    .map((e) => ({ ...e, rate: e.total === 0 ? 0 : e.correct / e.total }))
    .sort((a, b) => (a.truth < b.truth ? -1 : a.truth > b.truth ? 1 : 0));
}

// Alert categories for the Ignis product (from scenarios.json and
// adapter.mjs: only visible smoke and visible flame fire an alert).
// Confusable negatives are the non-alert categories a source most
// plausibly mistakes for an alert: steam or fog for smoke, flame-like
// lighting for flame.
export const IGNIS_ALERT_CATEGORIES = ["visible smoke", "visible flame"];
export const CONFUSABLE_NEGATIVE_CATEGORIES = ["steam or fog", "flame-like lighting"];
const ERROR_PREDICTED = "ERROR";

// One entry per category miss, in record order: the scenario id with
// the truth category and the predicted category, so a miss is
// diagnosable without cross-referencing the per-scenario table.
// Records that produced no assessment show ERROR, matching the
// confusion table's convention — a failure, not a wrong category.
// The filter is category_correct, the same definition the old bare
// id list used, so the section's count does not change — only the
// detail per miss does.
export function computeMisses(records) {
  return records
    .filter((r) => !r.category_correct)
    .map((r) => ({
      scenarioId: r.scenario_id,
      truth: r.ground_truth_label,
      predicted: r.actual_category === null ? ERROR_PREDICTED : r.actual_category,
    }));
}

// Truth-vs-predicted category counts for a run's records. Only the
// two record fields the table needs are read, so hand-built record
// lists work as well as full run JSON. Truth categories sort
// alphabetically; predicted categories sort alphabetically with
// ERROR last, so a held-state run's all-ERROR column never sorts
// ahead of a real category. Errored records (actual_category null)
// count under ERROR: they produced no prediction, so they are
// failures, not confusions.
export function computeCategoryConfusion(records) {
  const counts = {};
  for (const r of records) {
    const predicted = r.actual_category === null ? ERROR_PREDICTED : r.actual_category;
    counts[r.ground_truth_label] ??= {};
    counts[r.ground_truth_label][predicted] = (counts[r.ground_truth_label][predicted] || 0) + 1;
  }
  const truthCategories = Object.keys(counts).sort();
  const predictedSet = new Set();
  for (const truth of truthCategories) {
    for (const predicted of Object.keys(counts[truth])) predictedSet.add(predicted);
  }
  const predictedCategories = [...predictedSet].sort((a, b) => {
    if (a === ERROR_PREDICTED) return 1;
    if (b === ERROR_PREDICTED) return -1;
    return a < b ? -1 : a > b ? 1 : 0;
  });
  return { truthCategories, predictedCategories, counts };
}

// For each confusable-negative truth category present in the
// records: how many of its scenarios there are, how many were
// assessed at all, and how many were predicted as an alert category
// (a confusable false alarm), grouped by the predicted alert category
// with scenario ids. A truth category with no assessed scenarios
// reports zero assessed rather than zero false alarms, so a
// held-state run never reads as "no confusable problem" — it reads
// as "nothing assessed".
export function computeConfusableNegatives(records) {
  return CONFUSABLE_NEGATIVE_CATEGORIES.map((truth) => {
    const truthRecords = records.filter((r) => r.ground_truth_label === truth);
    const assessed = truthRecords.filter((r) => r.actual_category !== null);
    const falseAlarms = {};
    for (const r of assessed) {
      if (!IGNIS_ALERT_CATEGORIES.includes(r.actual_category)) continue;
      falseAlarms[r.actual_category] ??= [];
      falseAlarms[r.actual_category].push(r.scenario_id);
    }
    const falseAlarmCount = Object.values(falseAlarms).reduce((n, ids) => n + ids.length, 0);
    return { truth, total: truthRecords.length, assessed: assessed.length, falseAlarmCount, falseAlarms };
  }).filter((entry) => entry.total > 0);
}

export function assertWritableReportPath(outPath) {
  if (PROTECTED_REPORT_NAMES.includes(basename(outPath))) {
    throw new Error(
      `refusing to overwrite protected report "${basename(outPath)}": ` +
        "the fixture/held/baseline trio are historical records — write a live run to live-run-report.md instead",
    );
  }
}

function fmt(v) {
  return v === null ? "n/a" : v.toFixed(3);
}

function fmtLatency(v) {
  return v === null ? "n/a" : v.toFixed(1);
}

export function renderRunReport(run, baselineRun = null) {
  const errors = validateRunJson(run);
  if (errors.length > 0) throw new Error(`invalid run JSON: ${errors.join("; ")}`);
  let baseline = null;
  if (baselineRun !== null) {
    const baselineErrors = validateRunJson(baselineRun);
    if (baselineErrors.length > 0) {
      throw new Error(`invalid baseline run JSON: ${baselineErrors.join("; ")}`);
    }
    baseline = baselineRun;
  }
  const kind = classifyRunKind(run);
  const m = run.metrics;
  const lines = [
    `# Meta Ignis ${KIND_TITLES[kind]} run report`,
    "",
    KIND_INTRO[kind],
    "",
  ];
  if (run.source) lines.push(`- Source: ${run.source}`);
  if (run.generated) lines.push(`- Generated: ${run.generated}`);
  lines.push(
    `- Sample size: ${m.sample_size} scenarios`,
    `- Confusion (alert): TP=${m.true_positives} FP=${m.false_positives} TN=${m.true_negatives} FN=${m.false_negatives}`,
    `- Precision: ${fmt(m.precision)}${m.precision === null ? " (no alert ever predicted; denominator zero)" : ""}`,
    `- Recall: ${fmt(m.recall)}`,
    `- False-positive rate: ${fmt(m.false_positive_rate)}`,
    `- False-negative rate: ${fmt(m.false_negative_rate)}`,
    `- Category accuracy: ${fmt(m.category_accuracy)}`,
    `- Latency (harness wall clock): mean ${fmtLatency(m.latency_ms.mean)} ms, median ${fmtLatency(m.latency_ms.median)} ms, max ${fmtLatency(m.latency_ms.max)} ms`,
    `- Errors: ${m.errors.count}${m.errors.scenario_ids.length > 0 ? ` (${m.errors.scenario_ids.join(", ")})` : ""}`,
    "",
  );
  const headline = computeCategoryHeadline(run.records);
  lines.push("## Headline finding", "");
  if (headline.weakest === null) {
    lines.push(
      "No category finding: nothing in this run was assessed, so no weakest category " +
        "or confused pair can be named. This run's numbers describe source availability, not detection.",
    );
  } else if (headline.weakest.rate === 1) {
    lines.push("No category misses: every assessed scenario matched its ground truth.");
  } else {
    const w = headline.weakest;
    lines.push(`- Weakest category: ${w.truth} — ${w.correct} of ${w.total} correct (${w.rate.toFixed(3)}).`);
    if (headline.mostConfused === null) {
      lines.push("- Most confused pair: none — every category miss in this run produced no assessment (ERROR), not a wrong category.");
    } else {
      const p = headline.mostConfused;
      lines.push(`- Most confused pair: ${p.truth} -> ${p.predicted} — ${p.count} scenario(s) (${p.scenarioIds.join(", ")}).`);
    }
  }
  const rates = computeCategoryRates(run.records);
  lines.push(
    "",
    "## Per-category rates",
    "",
    "Each row is one ground-truth category: correct predictions over all of its scenarios. " +
      "Records that produced no assessment count as misses, matching category-accuracy semantics " +
      "and the headline's definition — so the headline's weakest category is the lowest row here " +
      "(headline ties break by most misses, then truth name). The assessed column keeps a held-state " +
      "row of 0.000 honest: it means nothing was assessed, not that a source scored zero.",
    "",
    "| Truth | Correct | Total | Assessed | Rate |",
    "| --- | --- | --- | --- | --- |",
  );
  for (const row of rates) {
    lines.push(`| ${row.truth} | ${row.correct} | ${row.total} | ${row.assessed} | ${row.rate.toFixed(3)} |`);
  }
  lines.push(
    "",
    "## Per-scenario records",
    "",
    "| Scenario | Truth | Actual | Alert correct | Category correct | Error |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const r of run.records) {
    lines.push(
      `| ${r.scenario_id} | ${r.ground_truth_label} | ${r.actual_category === null ? "ERROR" : r.actual_category} | ` +
        `${r.alert_correct} | ${r.category_correct} | ${r.error === null ? "" : r.error} |`,
    );
  }
  const misses = computeMisses(run.records);
  lines.push("", `## Misses (${misses.length})`, "");
  lines.push(
    misses.length > 0
      ? misses
          .map(
            (m) =>
              `- ${m.scenarioId}: ${m.truth} -> ${m.predicted}` +
              (m.predicted === ERROR_PREDICTED ? " (no assessment)" : ""),
          )
          .join("\n")
      : "None: every scenario's predicted category matched its ground truth.",
  );
  const confusion = computeCategoryConfusion(run.records);
  lines.push("", "## Per-category confusion", "");
  lines.push(
    "Rows are ground-truth categories, columns are predicted categories. " +
      "Diagonal cells are correct predictions; off-diagonal cells are category misses. " +
      "The ERROR column counts records that produced no assessment — failures, not confusions.",
    "",
    `| Truth \ Predicted | ${confusion.predictedCategories.join(" | ")} | Total |`,
    `| --- | ${confusion.predictedCategories.map(() => "---").join(" | ")} | --- |`,
  );
  for (const truth of confusion.truthCategories) {
    const cells = confusion.predictedCategories.map((p) => confusion.counts[truth][p] || 0);
    const total = cells.reduce((n, c) => n + c, 0);
    lines.push(`| ${truth} | ${cells.join(" | ")} | ${total} |`);
  }
  const confusables = computeConfusableNegatives(run.records);
  const confusableTotal = confusables.reduce((n, e) => n + e.total, 0);
  const confusableFalseAlarms = confusables.reduce((n, e) => n + e.falseAlarmCount, 0);
  lines.push("", "## Confusable negatives", "");
  lines.push(
    "Confusable negatives are non-alert scenes a source plausibly mistakes for an alert: " +
      "steam or fog for smoke, flame-like lighting for flame. This section counts, per confusable " +
      "truth category, how many scenarios were predicted as an alert category (visible smoke, visible flame).",
    "",
  );
  if (confusables.length === 0) {
    lines.push("- No confusable-negative scenarios in this run.");
  }
  for (const entry of confusables) {
    if (entry.assessed === 0) {
      lines.push(`- ${entry.truth}: ${entry.total} scenario(s), none assessed — no confusable false alarm could occur.`);
    } else if (entry.falseAlarmCount === 0) {
      lines.push(`- ${entry.truth}: 0 of ${entry.total} predicted as an alert category.`);
    } else {
      const byPredicted = Object.entries(entry.falseAlarms)
        .map(([predicted, ids]) => `${predicted}: ${ids.length} (${ids.join(", ")})`)
        .join("; ");
      lines.push(`- ${entry.truth}: ${entry.falseAlarmCount} of ${entry.total} predicted as an alert category — ${byPredicted}.`);
    }
  }
  lines.push(
    "",
    `Total: ${confusableFalseAlarms} of ${confusableTotal} confusable-negative scenarios predicted as an alert category.`,
  );
  if (baseline !== null) {
    const b = baseline.metrics;
    const recallBeats = m.recall !== null && b.recall !== null && m.recall > b.recall;
    const accuracyBeats =
      m.category_accuracy !== null && b.category_accuracy !== null && m.category_accuracy > b.category_accuracy;
    const beats = recallBeats && accuracyBeats;
    lines.push(
      "",
      "## Comparison against the baseline",
      "",
      `Baseline (always-no-hazard): recall ${fmt(b.recall)}, category accuracy ${fmt(b.category_accuracy)}.`,
      `This run: recall ${fmt(m.recall)}, category accuracy ${fmt(m.category_accuracy)}.`,
      beats
        ? "Verdict: this run BEATS the baseline on recall and category accuracy — the bar a real source must clear."
        : "Verdict: this run does NOT beat the baseline on both recall and category accuracy. " +
          "Beating it on precision alone proves nothing, since the baseline never fires a false alarm by construction.",
    );
  } else {
    lines.push(
      "",
      "## Comparison against the baseline",
      "",
      "No baseline run supplied: pass `--baseline <baseline-run.json>` to render the " +
        "recall-and-category-accuracy verdict. A source must beat the baseline on both to claim value.",
    );
  }
  lines.push(
    "",
    "## What this run does not prove",
    "",
    kind === "live-model"
      ? "A live-model run on labeled descriptions proves the wired source scores this scenario set; " +
        "it does not prove real-hardware camera performance, real photographs, or performance on scenes outside this set."
      : "This run is not a model result, and its numbers must not be quoted as one. " +
        "A live run belongs in its own live-run-report.md file, never as an edit to the fixture, held-state, or baseline trio.",
    "",
  );
  return lines.join("\n");
}

// CLI: node eval/ignis/report.mjs <run.json> [--baseline <baseline-run.json>] [--out <report.md>]
// No model call, no key, no network: it only reads run JSON files.
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  try {
    const args = process.argv.slice(2);
    // Parse sequentially so a flag's value (e.g. --out <path>) is never
    // mistaken for the positional run JSON.
    let runPath = null;
    let baselinePath = null;
    let outPath = null;
    for (let i = 0; i < args.length; i += 1) {
      if (args[i] === "--baseline" && i + 1 < args.length) baselinePath = args[++i];
      else if (args[i] === "--out" && i + 1 < args.length) outPath = args[++i];
      else if (args[i].startsWith("--")) throw new Error(`unknown or incomplete flag "${args[i]}"`);
      else if (runPath === null) runPath = args[i];
      else throw new Error(`unexpected extra argument "${args[i]}"`);
    }
    if (runPath === null) {
      throw new Error("usage: node eval/ignis/report.mjs <run.json> [--baseline <baseline-run.json>] [--out <report.md>]");
    }
    const run = JSON.parse(readFileSync(runPath, "utf8"));
    const baselineRun = baselinePath !== null ? JSON.parse(readFileSync(baselinePath, "utf8")) : null;
    const report = renderRunReport(run, baselineRun);
    if (outPath !== null) {
      assertWritableReportPath(outPath);
      writeFileSync(outPath, report);
      console.log(`Wrote ${outPath}`);
    } else {
      console.log(report);
    }
  } catch (err) {
    console.error(`report.mjs: ${err.message}`);
    process.exitCode = 1;
  }
}
