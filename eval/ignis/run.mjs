// Meta Ignis eval runner (Rowan's lane).
// Usage: node eval/ignis/run.mjs [--out <path>] [--baseline | --stub]
// Runs the Ignis scenario set against the wired assessment source:
// the real server model adapter (server/model.mjs). While Del's Spark
// rule holds, every scenario records the held refusal as its error;
// the printed report says so, and its numbers describe source
// availability, not model performance. No assessment is fabricated,
// no live model call is made, no API key is read from anywhere but
// the server environment (which the adapter itself gates).
// With --baseline, runs the same scenario set against the
// always-no-hazard baseline (baseline.mjs) instead: fixture numbers
// that set the bar a real source must beat (recall and category
// accuracy), not model performance.
// With --stub, runs the same scenario set against the deterministic
// fixture stub (stub.mjs) instead, then runs the baseline on the same
// set and prints the stub-vs-baseline comparison: fixture numbers
// only, neither source a model, so the comparison exercises the
// harness, it does not describe model performance.
//
// When the test phase lands the Spark transport, this same runner
// scores real assessments with no adapter change.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  runIgnisEval,
  computeMetrics,
  formatIgnisReport,
  assessViaModelAdapter,
} from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";
import { assessStub } from "./stub.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");
const useStub = process.argv.includes("--stub");

const assess = useBaseline ? assessBaseline : useStub ? assessStub : assessViaModelAdapter;
let source = useBaseline
  ? "baseline always-no-hazard (fixture)"
  : useStub
    ? "stub (fixture, not a model)"
    : "server model adapter (held while Spark stays off)";
const records = await runIgnisEval(scenarios, assess);
const metrics = computeMetrics(records);
// Evidence-based labels for the default (wired-source) run: a stale
// "held" label must never describe a run that returned assessments.
// When the test phase lands the Spark transport, this same runner
// labels a live run "live" and its --out JSON "live-model run"
// with no further change; until then the held label stays exact.
const allHeld =
  records.length > 0 &&
  records.every((r) => typeof r.error === "string" && r.error.includes("Live model calls are held"));
const anyAssessment = records.some((r) => r.actual_category !== null);
if (!useBaseline && !useStub) {
  source = allHeld
    ? "server model adapter (held while Spark stays off)"
    : anyAssessment
      ? "server model adapter (live)"
      : "server model adapter (errors, no assessments)";
}
console.log(formatIgnisReport({ source, records, metrics }));
console.log("");
if (useStub) {
  const baselineRecords = await runIgnisEval(scenarios, assessBaseline);
  const baselineMetrics = computeMetrics(baselineRecords);
  console.log(
    "Comparison (same ground truth, same harness): " +
      `stub precision=${metrics.precision === null ? "n/a" : metrics.precision.toFixed(3)} ` +
      `recall=${metrics.recall.toFixed(3)} category accuracy=${metrics.category_accuracy.toFixed(3)} ` +
      `vs baseline precision=${baselineMetrics.precision === null ? "n/a (no alert predicted)" : baselineMetrics.precision.toFixed(3)} ` +
      `recall=${baselineMetrics.recall.toFixed(3)} category accuracy=${baselineMetrics.category_accuracy.toFixed(3)}. ` +
      "Fixture numbers only: neither source is a model, and neither number " +
      "describes live model performance.",
  );
  console.log("");
}
if (useBaseline) {
  console.log(
    "Baseline note: a do-nothing source that predicts no hazard for " +
      "every scene and never fires an alert. These are fixture numbers, " +
      "not model performance. A future real source must beat this " +
      "baseline on recall and category accuracy to claim value; beating " +
      "it on precision alone proves nothing, since it never fires a " +
      "false alarm by construction.",
  );
} else if (useStub) {
  console.log(
    "Stub note: a deterministic fixture table, not a model. Its misses " +
      "are documented in stub.mjs before any run. These are fixture " +
      "numbers, not model performance.",
  );
} else if (allHeld) {
  console.log(
    "Held-state note: every scenario above records the server adapter's " +
      "refusal as its error. These numbers describe source availability " +
      "(no assessment available while live calls are held), not model " +
      "performance. No assessment was fabricated to fill the gap.",
  );
} else if (anyAssessment) {
  console.log(
    "Live-model note: the scenarios above returned real assessments. " +
      "These numbers describe this scenario set against the wired source " +
      "only — not real-hardware camera input, and not photographs, unless " +
      "the run itself was produced from real frames.",
  );
} else {
  console.log(
    "Errored note: no scenario above returned an assessment. These numbers " +
      "describe the failure, not detection, and must not be quoted as a model result.",
  );
}

if (outPath) {
  writeFileSync(
    outPath,
    JSON.stringify(
      { source, records, metrics, generated: useBaseline || useStub ? "fixture run, no live model" : allHeld ? "held-state run, no live model" : anyAssessment ? "live-model run" : "errored run, no assessments" },
      null,
      2,
    ) + "\n",
  );
  console.log(`Wrote ${outPath}`);
}
