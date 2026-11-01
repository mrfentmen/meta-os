// Musica session report: HN-050. The daily page must show takes,
// keepers, rejects, and the best prompt, all matching the log.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-report-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("session report matches the take log", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--brief-text", "report prompt", "--takes", "3", "--seed-base", "19000"]);
  py("keepers.py", [staging]);
  py("report.py", [staging]);
  const report = readFileSync(join(staging, "report.html"), "utf8");
  const log = readFileSync(join(staging, "take_log.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const keepers = log.filter((t) => t.verdict === "keeper").length;
  const rejects = log.filter((t) => t.verdict === "reject").length;
  assert.ok(report.includes(`Takes: ${log.length}`));
  assert.ok(report.includes(`Keepers: ${keepers}`));
  assert.ok(report.includes(`Rejects: ${rejects}`));
  assert.ok(report.includes("Best prompt:"));
  assert.ok(report.includes("report prompt"));
});
