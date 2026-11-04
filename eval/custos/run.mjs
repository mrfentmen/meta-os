// Meta Custos eval runner (first slice).
// Usage: node eval/custos/run.mjs [--out <path>] [--baseline]
// Runs the Custos scenario set against the real patrol code (default)
// or against the empty-outcome baseline fixture (--baseline).
// The real run exits 1 on any fail; the baseline run always exits 0
// because its table is the fixture bar, not a failure to investigate.
// Neither run touches os/worlds/custos/runs/ or any watched host:
// CLI runs use fixture feeds and tmp state dirs, probe runs inject
// every signal, and the hosted patrol entry point is never executed
// against a real config.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessCustos, runCustosEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessCustos;
const source = useBaseline
  ? "baseline empty-outcome reader (fixture)"
  : "real Custos patrol code (CLI fixture feeds + injected probes, tmp dirs only)";
const records = runCustosEval(scenarios, assess);
const passed = records.filter((r) => r.pass).length;

console.log("Custos eval (" + source + "): " + passed + "/" + records.length);
for (const r of records) {
  console.log((r.pass ? "PASS " : "FAIL ") + r.id + " " + r.title + " — " + r.evidence);
}
console.log("");
if (useBaseline) {
  console.log(
    "Baseline note: a fixture that predicts nothing happened for every " +
    "scenario. These are fixture numbers, not patrol performance. A real " +
    "run must beat this baseline by running the patrol code, not by " +
    "predicting the empty outcome; beating it on the one empty row " +
    "alone proves nothing, since that row is empty by construction.",
  );
} else {
  console.log(
    "Real-run note: every scenario above ran the real Custos patrol " +
    "code on committed inputs in fresh tmp dirs. These numbers describe " +
    "the patrol's own rules (KEV matching and ageing, CT/DNS/subdomain " +
    "watches, certificate tiers, exposure, headers, TLS, dedup, " +
    "false-positive dismissal, scheduling, pack validity) — not a live " +
    "patrol, which this harness never performs, and not any escalation " +
    "to a real responder, which stage 1 never does.",
  );
}

if (outPath) {
  writeFileSync(
    outPath,
    JSON.stringify(
      { source, records, passed, total: records.length, generated: useBaseline ? "fixture run, no live patrol" : "real-code run, tmp dirs only" },
      null,
      2,
    ) + "\n",
  );
  console.log(`Wrote ${outPath}`);
}

if (!useBaseline && passed !== records.length) process.exit(1);
