import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runGymDrill, recordGymResult, TASKS } from "../agents/gym.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "gym-test-"));
const NODE = process.execPath;
const registryFor = (agents) => {
  const dir = tmp();
  const file = path.join(dir, "registry.json");
  fs.writeFileSync(file, JSON.stringify({ agents }, null, 1));
  return file;
};

test("drill has exactly three tasks", () => {
  assert.deepEqual(TASKS.map((t) => t.id), ["registry-entry", "spawn-clean-exit", "ledger-complete"]);
});

test("drill scores 3/3 on a clean agent through the real runtime", async () => {
  const file = registryFor([
    { name: "fit", command: [NODE, "-e", "console.log('trained')"], budget: { maxWallMs: 60000 } },
  ]);
  const result = await runGymDrill({ registryFile: file, agentName: "fit" });
  assert.equal(result.total, 3);
  assert.equal(result.max, 3);
  assert.deepEqual(result.tasks.map((t) => t.score), [1, 1, 1]);
  // The spawn really ran: brief + ledger + output exist in the run dir.
  assert.equal(JSON.parse(fs.readFileSync(path.join(result.runDir, "brief.json"), "utf8")).agent, "fit");
  assert.match(fs.readFileSync(path.join(result.runDir, "output.log"), "utf8"), /trained/);
});

test("a failing agent loses only the spawn task, ledger task still passes", async () => {
  const file = registryFor([
    { name: "clumsy", command: [NODE, "-e", "process.exit(3)"], budget: {} },
  ]);
  const result = await runGymDrill({ registryFile: file, agentName: "clumsy" });
  assert.deepEqual(result.tasks.map((t) => t.score), [1, 0, 1]);
  assert.equal(result.total, 2);
});

test("unknown agent throws, nothing recorded", async () => {
  const file = registryFor([{ name: "fit", command: ["true"], budget: {} }]);
  await assert.rejects(() => runGymDrill({ registryFile: file, agentName: "ghost" }), /no such agent/);
});

test("record writes the gym record onto only that entry and appends ledger scores", async () => {
  const dir = tmp();
  const file = path.join(dir, "registry.json");
  fs.writeFileSync(file, JSON.stringify({ agents: [
    { name: "fit", command: ["true"], budget: {}, lane: "test" },
    { name: "other", command: ["true"], budget: {} },
  ] }, null, 1));
  const gymLedger = path.join(dir, "gym-ledger.jsonl");
  const result = await runGymDrill({ registryFile: file, agentName: "fit" });
  const gym = recordGymResult({ registryFile: file, gymLedgerFile: gymLedger, result });
  assert.equal(gym.total, 3);
  const after = JSON.parse(fs.readFileSync(file, "utf8"));
  assert.equal(after.agents[0].gym.total, 3);
  assert.equal(after.agents[0].lane, "test");
  assert.equal(after.agents[1].gym, undefined);
  const lines = fs.readFileSync(gymLedger, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(lines.length, 4);
  assert.deepEqual(lines.map((l) => l.event), ["gym-task-score", "gym-task-score", "gym-task-score", "gym-total"]);
  assert.equal(lines[3].total, 3);
});
