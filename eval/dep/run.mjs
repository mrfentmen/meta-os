// Meta DEP eval runner (first slice).
// Usage: node eval/dep/run.mjs [--baseline] [--out <path>]
// Default: score the scenario set through the real committed DEP
// pack declarations, offline. With --baseline: score the label-only
// fixture instead, which sets the bar a real run must beat; baseline
// mode always exits 0 because its failures are the point. Real mode
// exits 1 if any scenario fails.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessReal, formatDepReport, runDepEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessReal;
const source = useBaseline ? "baseline label-only reader (fixture)" : "real DEP pack declarations (offline)";
const records = await runDepEval(scenarios, assess, { root });
const report = formatDepReport(records, source);
console.log(report);
if (useBaseline) {
  console.log("");
  console.log("Baseline note: a label-only reader that claims spec and reads nothing. These are fixture numbers, not system performance. A real run must beat this baseline's 1/11 to claim it reads the pack; passing the one label row alone proves nothing.");
} else {
  console.log("");
  console.log("Replay note: a passing replay means the pack still declares what this harness measured, including the named cross-world gaps, and that the doc still carries its SPEC, NOT BUILT label. It does not rate a real utility system, a real pump station, or any live water service, because the pack is status spec and ships no runtime.");
}
if (outPath) writeFileSync(outPath, report + "\n");
if (!useBaseline && records.some((r) => !r.pass)) process.exit(1);
