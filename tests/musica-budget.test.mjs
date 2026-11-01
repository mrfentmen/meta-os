// Musica loop budget guard: HN-051. A cap hit must stop the
// session gracefully (logged, exit 0), not fail it; under the cap
// the loop runs normally.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-budget-test");

function today() {
  return new Date().toISOString().slice(0, 10);
}

test("cap hit stops the session gracefully, not as an error", () => {
  const config = join(staging, "budget.json");
  const ledger = join(staging, "spend.json");
  const session = join(staging, "sessions", "capped");
  execFileSync("mkdir", ["-p", staging]);
  writeFileSync(config, JSON.stringify({ daily_cap_usd: 5.0 }));
  writeFileSync(ledger, JSON.stringify(
    [{ date: today(), usd: 5.0, take_id: "take-001" }]));
  const run = spawnSync("python3", [join(runtime, "compose.py"),
    "--session-dir", session, "--brief-id", "chipsynth",
    "--takes", "3", "--seed-base", "20000", "--spark-assist", "structure",
    "--budget-config", config, "--spend-ledger", ledger],
    { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /budget stop/);
  const sessionJson = JSON.parse(readFileSync(join(session, "session.json"), "utf8"));
  assert.ok(sessionJson.budget_stop, "budget_stop missing");
  assert.equal(sessionJson.budget_stop.daily_cap_usd, 5.0);
  assert.ok(!existsSync(join(session, "take_log.jsonl"))
    || readFileSync(join(session, "take_log.jsonl"), "utf8").trim() === "");
});

test("under the cap the loop runs normally", () => {
  const config = join(staging, "budget.json");
  const ledger = join(staging, "spend.json");
  const session = join(staging, "sessions", "under-cap");
  writeFileSync(ledger, JSON.stringify(
    [{ date: today(), usd: 1.0, take_id: "take-001" }]));
  execFileSync("python3", [join(runtime, "compose.py"),
    "--session-dir", session, "--brief-id", "chipsynth",
    "--takes", "2", "--seed-base", "21000", "--spark-assist", "structure",
    "--budget-config", config, "--spend-ledger", ledger],
    { encoding: "utf8" });
  const log = readFileSync(join(session, "take_log.jsonl"), "utf8")
    .trim().split("\n");
  assert.equal(log.length, 2);
  const sessionJson = JSON.parse(readFileSync(join(session, "session.json"), "utf8"));
  assert.ok(!sessionJson.budget_stop);
});
