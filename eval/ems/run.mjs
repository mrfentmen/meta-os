// Meta EMS eval runner (first slice).
// Usage: node eval/ems/run.mjs [--baseline] [--out <path>]
// Default: score the scenario set through the real committed EMS pack
// declarations, offline, read-only. With --baseline: score the
// label-only fixture instead, which sets the bar a real run must beat;
// baseline mode always exits 0 because its failures are the point.
// Real mode exits 1 if any scenario fails.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessReal, formatEmsReport, runEmsEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessReal;
const source = useBaseline ? "baseline label-only reader (fixture)" : "real EMS pack declarations (offline, read-only)";
const records = await runEmsEval(scenarios, assess, { root });
const report = formatEmsReport(records, source);
console.log(report);
if (useBaseline) {
  console.log("");
  console.log("Baseline note: a label-only reader that claims spec and reads nothing. These are fixture numbers, not system performance. A real run must beat this baseline's 1/9 to claim it reads the pack; passing the one label row alone proves nothing.");
} else {
  console.log("");
  console.log("Replay note: a passing replay means the pack still declares what this harness measured, including the named reciprocity gap. It does not rate an ambulance, a hospital, or any live feed, because the pack is status spec and no runtime ships with it.");
}
if (outPath) writeFileSync(outPath, report + "\n");
if (!useBaseline && records.some((r) => !r.pass)) process.exit(1);
