// Meta Hands-Free eval runner (first slice).
// Usage: node eval/handsfree/run.mjs [--out <path>] [--baseline]
// Runs the Hands-Free scenario set against the real modules (default)
// or against the empty-outcome baseline fixture (--baseline).
// The real run exits 1 on any fail; the baseline run always exits 0
// because its table is the fixture bar, not a failure to investigate.
// Neither run touches os-build/handsfree/: file-writing checks run in
// fresh tmp dirs, and the hosted entry point is never executed.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessHandsfree, runHandsfreeEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = dirname(dirname(here));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : (s) => assessHandsfree(s, root);
const source = useBaseline
  ? "baseline empty-outcome reader (fixture)"
  : "real Hands-Free modules (tmp dirs only, hosted entry never run)";
const records = runHandsfreeEval(scenarios, assess, root);
const passed = records.filter((r) => r.pass).length;

console.log("Hands-Free eval (" + source + "): " + passed + "/" + records.length);
for (const r of records) {
  console.log((r.pass ? "PASS " : "FAIL ") + r.id + " " + r.title + " — " + r.evidence);
}
console.log("");
if (useBaseline) {
  console.log(
    "Baseline note: a fixture that predicts nothing happened for every " +
    "scenario. These are fixture numbers, not voice performance. A real " +
    "run must beat this baseline by running the modules, not by " +
    "predicting the empty outcome; beating it on the two empty rows " +
    "alone proves nothing, since those rows are empty by construction.",
  );
} else {
  console.log(
    "Real-run note: every scenario above ran the real Hands-Free modules " +
    "on committed inputs in fresh tmp dirs. These numbers describe the " +
    "text path's own rules (intake, brief, approval, refusals, latency, " +
    "voice lines, session replay, registry wiring) — not spoken audio, " +
    "which this path does not produce, and not any dispatched order, " +
    "which this harness never performs.",
  );
}

if (outPath) {
  writeFileSync(
    outPath,
    JSON.stringify(
      { source, records, passed, total: records.length, generated: useBaseline ? "fixture run, no live model" : "real-module run, tmp dirs only" },
      null,
      2,
    ) + "\n",
  );
  console.log(`Wrote ${outPath}`);
}

if (!useBaseline && passed !== records.length) process.exit(1);
