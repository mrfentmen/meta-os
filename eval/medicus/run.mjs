// Meta Medicus fixture eval runner (Agent 3).
// Usage: node eval/medicus/run.mjs [--out <path>]
// Runs the Medicus scenario set against the fixture stub and against
// the always-normal baseline, prints both reports and the comparison.
// No network, no model calls, no API key. The stub and baseline are
// fixture sources; their numbers are fixture numbers, not model
// performance, and the printed report says so.
//
// To plug in a real assessment source later (Rowan's /api/assess,
// which exists in-repo, once Del green-lights the test phase), replace the assess
// function passed to runEval with an adapter around assessFrame from
// js/client.js. Do not call any live endpoint from this runner until
// then; Spark stays OFF.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { runEval, computeMetrics, formatReport } from "./harness.mjs";
import { assessStub } from "./stub.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;

const runs = [];
for (const [source, assess] of [
  ["stub (fixture, not a model)", assessStub],
  ["baseline always-normal (fixture)", assessBaseline],
]) {
  const records = await runEval(scenarios, assess);
  const metrics = computeMetrics(records);
  console.log(formatReport({ source, records, metrics }));
  console.log("");
  runs.push({ source, records, metrics });
}

console.log(
  "Comparison (same ground truth, same harness): " +
    `stub precision=${runs[0].metrics.precision === null ? "n/a" : runs[0].metrics.precision.toFixed(3)} ` +
    `recall=${runs[0].metrics.recall.toFixed(3)} vs baseline ` +
    `precision=${runs[1].metrics.precision === null ? "n/a (no alert predicted)" : runs[1].metrics.precision.toFixed(3)} ` +
    `recall=${runs[1].metrics.recall.toFixed(3)}. ` +
    "Fixture numbers only: neither source is a model, and neither number " +
    "describes live model performance.",
);

if (outPath) {
  writeFileSync(outPath, JSON.stringify({ runs, generated: "fixture run, no live model" }, null, 2) + "\n");
  console.log(`Wrote ${outPath}`);
}
