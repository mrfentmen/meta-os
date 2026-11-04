// Meta Nervus eval runner (first slice).
// Usage: node eval/nervus/run.mjs [--baseline] [--out <path>]
// Default: replay the scenario set through the real committed Nervus
// records, offline, read-only. With --baseline: score the label-only
// fixture instead, which sets the bar a real run must beat; baseline
// mode always exits 0 because its failures are the point. Real mode
// exits 1 if any scenario fails to replay.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessReal, formatNervusReport, runNervusEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessReal;
const source = useBaseline ? "baseline label-only reader (fixture)" : "real Nervus records (offline replay, read-only)";
const records = await runNervusEval(scenarios, assess, { root });
const report = formatNervusReport(records, source);
console.log(report);
if (useBaseline) {
  console.log("");
  console.log("Baseline note: a label-only reader that claims stub and reads nothing. These are fixture numbers, not model performance. A real run must beat this baseline's 2/10 to claim it reads the records; passing the two label rows alone proves nothing.");
} else {
  console.log("");
  console.log("Replay note: a passing replay means the code still reads its own stub records the same way. It does not rate a model, because no model is loaded, and it does not claim any record beyond the committed ledger, receipt, dose windows, layer curve, gap record, and registry entry.");
}
if (outPath) writeFileSync(outPath, report + "\n");
if (!useBaseline && records.some((r) => !r.pass)) process.exit(1);
