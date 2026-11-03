// Meta FDNY eval runner (first slice).
// Usage: node eval/fdny/run.mjs [--baseline] [--out <path>]
// Default: score the scenario set through the real committed FDNY pack
// declarations plus a real PAR clock smoke run, offline. With
// --baseline: score the label-only fixture instead, which sets the
// bar a real run must beat; baseline mode always exits 0 because its
// failures are the point. Real mode exits 1 if any scenario fails.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessReal, formatFdnyReport, runFdnyEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessReal;
const source = useBaseline ? "baseline label-only reader (fixture)" : "real FDNY pack declarations + PAR clock smoke (offline)";
const records = await runFdnyEval(scenarios, assess, { root });
const report = formatFdnyReport(records, source);
console.log(report);
if (useBaseline) {
  console.log("");
  console.log("Baseline note: a label-only reader that claims partial and reads nothing. These are fixture numbers, not system performance. A real run must beat this baseline's 1/11 to claim it reads the pack; passing the one label row alone proves nothing.");
} else {
  console.log("");
  console.log("Replay note: a passing replay means the pack still declares what this harness measured, including the named reciprocity gap and the PAR clock behaviour, and that the clock still escalates on its fake clock. It does not rate a real fireground, a real station, or any live feed, because the pack is status partial and only the PAR clock ships as runtime.");
}
if (outPath) writeFileSync(outPath, report + "\n");
if (!useBaseline && records.some((r) => !r.pass)) process.exit(1);
