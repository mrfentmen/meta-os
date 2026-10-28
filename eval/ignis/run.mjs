// Meta Ignis eval runner (Rowan's lane).
// Usage: node eval/ignis/run.mjs [--out <path>] [--baseline]
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

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const source = useBaseline
  ? "baseline always-no-hazard (fixture)"
  : "server model adapter (held while Spark stays off)";
const records = await runIgnisEval(scenarios, useBaseline ? assessBaseline : assessViaModelAdapter);
const metrics = computeMetrics(records);
console.log(formatIgnisReport({ source, records, metrics }));
console.log("");
if (useBaseline) {
  console.log(
    "Baseline note: a do-nothing source that predicts no hazard for " +
      "every scene and never fires an alert. These are fixture numbers, " +
      "not model performance. A future real source must beat this " +
      "baseline on recall and category accuracy to claim value; beating " +
      "it on precision alone proves nothing, since it never fires a " +
      "false alarm by construction.",
  );
} else {
  console.log(
    "Held-state note: every scenario above records the server adapter's " +
      "refusal as its error. These numbers describe source availability " +
      "(no assessment available while live calls are held), not model " +
      "performance. No assessment was fabricated to fill the gap.",
  );
}

if (outPath) {
  writeFileSync(
    outPath,
    JSON.stringify(
      { source, records, metrics, generated: useBaseline ? "fixture run, no live model" : "held-state run, no live model" },
      null,
      2,
    ) + "\n",
  );
  console.log(`Wrote ${outPath}`);
}
