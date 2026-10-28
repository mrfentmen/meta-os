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
  const misses = run.records.filter((r) => !r.category_correct).map((r) => r.scenario_id);
  lines.push("", `## Misses (${misses.length})`, "");
  lines.push(
    misses.length > 0
      ? misses.map((id) => `- ${id}: predicted category did not match ground truth`).join("\n")
      : "None: every scenario's predicted category matched its ground truth.",
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
