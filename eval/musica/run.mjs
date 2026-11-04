// Meta Musica eval runner (first slice).
// Usage: node eval/musica/run.mjs [--baseline] [--out <path>]
// Default: replay the scenario set through the real Musica records,
// offline. With --baseline: score the always-reject fixture instead,
// which sets the bar a real run must beat; baseline mode always
// exits 0 because its failures are the point. Real mode exits 1 if
// any scenario fails to replay.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { assessReal, formatMusicaReport, runMusicaEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const outIndex = process.argv.indexOf("--out");
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
const useBaseline = process.argv.includes("--baseline");

const assess = useBaseline ? assessBaseline : assessReal;
const source = useBaseline ? "baseline always-reject (fixture)" : "real Musica records (offline replay)";
const records = await runMusicaEval(scenarios, assess, { root });
const report = formatMusicaReport(records, source);
console.log(report);
if (useBaseline) {
  console.log("");
  console.log("Baseline note: a do-nothing source that rejects every take and catalogues nothing. These are fixture numbers, not model performance. A real run must beat this baseline's 1/10 to claim it replays the records; beating it on the single reject row alone proves nothing.");
} else {
  console.log("");
  console.log("Replay note: a passing replay means the code still reads its own records the same way. It does not rate live composition, and it does not claim any take beyond the committed sessions (hn029, hn038 x3, overnight-001).");
}
if (outPath) writeFileSync(outPath, report + "\n");
if (!useBaseline && records.some((r) => !r.pass)) process.exit(1);
