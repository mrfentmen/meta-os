// Meta Aegis eval runner (first slice).
// Usage: node eval/aegis/run.mjs [--baseline] [--out <path>]
// Default: replay the scenario set through the real Aegis modules, offline.
// With --baseline: score the always-no-detection fixture instead, which sets
// the bar a real run must beat; baseline mode always exits 0 because its
// failures are the point. Real mode exits 1 if any scenario fails to replay.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { runAegisEval, assessReal, formatAegisReport } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";
import { computeMetrics } from "../shared/metrics.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessReal;
const source = useBaseline ? "baseline always-no-detection (fixture)" : "real Aegis modules (offline replay)";
const records = await runAegisEval(scenarios, assess, { root });
const scored = records
  .filter((r) => r.fired !== null)
  .map((r) => ({
    alert_fired: r.fired,
    alert_expected: r.fired_expected,
    category_correct: r.category_correct,
    latency_ms: r.latency_ms,
    error: r.error,
  }));
const metrics = computeMetrics(scored);
const report = formatAegisReport(records, metrics, source);
console.log(report);
if (outPath) writeFileSync(outPath, report);
if (!useBaseline && records.some((r) => !r.pass)) process.exit(1);
