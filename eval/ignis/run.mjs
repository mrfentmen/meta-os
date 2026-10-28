// Meta Ignis eval runner (Rowan's lane).
// Usage: node eval/ignis/run.mjs [--out <path>]
// Runs the Ignis scenario set against the wired assessment source:
// the real server model adapter (server/model.mjs). While Del's Spark
// rule holds, every scenario records the held refusal as its error;
// the printed report says so, and its numbers describe source
// availability, not model performance. No assessment is fabricated,
// no live model call is made, no API key is read from anywhere but
// the server environment (which the adapter itself gates).
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

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;

const source = "server model adapter (held while Spark stays off)";
const records = await runIgnisEval(scenarios, assessViaModelAdapter);
const metrics = computeMetrics(records);
console.log(formatIgnisReport({ source, records, metrics }));
console.log("");
console.log(
  "Held-state note: every scenario above records the server adapter's " +
    "refusal as its error. These numbers describe source availability " +
    "(no assessment available while live calls are held), not model " +
    "performance. No assessment was fabricated to fill the gap.",
);

if (outPath) {
  writeFileSync(
    outPath,
    JSON.stringify({ source, records, metrics, generated: "held-state run, no live model" }, null, 2) + "\n",
  );
  console.log(`Wrote ${outPath}`);
}
