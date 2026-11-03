// A relay that can task itself needs a ceiling on how fast it spends. These
// tests drive the real watchman with a real budget.json.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createWatchman } from "../agents/watchman.mjs";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-budget-"));
}

function board(jobs, budget) {
  const root = tmp();
  const dir = path.join(root, "jobs");
  fs.mkdirSync(dir);
  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({
    agents: [{
      name: "watch", lane: "iso", budget: {},
      command: ["node", "-e", "setTimeout(() => process.exit(0), 10)"],
    }],
  }));
  for (const job of jobs) {
    fs.writeFileSync(path.join(dir, job.id + ".job.json"), JSON.stringify({ agent: "watch", ...job }));
  }
  if (budget != null) {
    fs.writeFileSync(path.join(root, "budget.json"), JSON.stringify({ maxSpawnsPerHour: budget }));
  }
  return { root, jobs: dir, watchman: createWatchman({ registryFile, root, jobsDir: dir }) };
}

async function drain(spawned) {
  await Promise.all(spawned.map((entry) => entry.handle.done));
}

test("the ceiling stops the second start and keeps its job on the board", async () => {
  const { jobs, watchman } = board(
    [{ id: "b1", orders: "one" }, { id: "b2", orders: "two" }],
    1
  );
  const first = await watchman.pollOnce();
  assert.equal(first.length, 1, "one start is within the ceiling");
  await drain(first);

  const second = await watchman.pollOnce();
  assert.equal(second.length, 0, "the ceiling held");

  const events = watchman.ledger.read();
  assert.ok(events.some((entry) => entry.event === "relay-budget"), "the refusal is named");
  const bell = events.filter((entry) => entry.event === "bell");
  assert.equal(bell.length, 1, "only the first job rang");

  // Held, not judged: no receipt, and the job file is still there.
  assert.ok(fs.existsSync(path.join(jobs, "b2.job.json")));
  assert.equal(fs.existsSync(path.join(jobs, "b2.result.json")), false);
});

test("the budget line is written once an hour, not once a poll", async () => {
  const { watchman } = board([{ id: "b3", orders: "a" }, { id: "b4", orders: "b" }], 1);
  const first = await watchman.pollOnce();
  await drain(first);
  await watchman.pollOnce();
  await watchman.pollOnce();
  const lines = watchman.ledger.read().filter((entry) => entry.event === "relay-budget");
  assert.equal(lines.length, 1);
});

test("raising the ceiling on disk lets the held job run without a restart", async () => {
  const { root, jobs, watchman } = board([{ id: "b5", orders: "a" }, { id: "b6", orders: "b" }], 1);
  const first = await watchman.pollOnce();
  await drain(first);
  assert.equal((await watchman.pollOnce()).length, 0);

  fs.writeFileSync(path.join(root, "budget.json"), JSON.stringify({ maxSpawnsPerHour: 5 }));
  const after = await watchman.pollOnce();
  assert.equal(after.length, 1, "the held job runs once there is headroom");
  await drain(after);
  assert.ok(fs.existsSync(path.join(jobs, "b6.result.json")));
});

test("no budget file means no ceiling", async () => {
  const { watchman } = board([{ id: "b7", orders: "a" }, { id: "b8", orders: "b" }], null);
  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 2);
  await drain(spawned);
});
