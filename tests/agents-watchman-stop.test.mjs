// A halt that only stops work already running is not a halt. This drives the
// real watchman with a real stop file and checks what the board says.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createWatchman } from "../agents/watchman.mjs";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-stop-"));
}

function board(job) {
  const root = tmp();
  const jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({
    agents: [{ name: "watch", lane: "iso", command: ["node", "-e", "process.exit(0)"], budget: {} }],
  }));
  fs.writeFileSync(path.join(jobs, job.id + ".job.json"), JSON.stringify(job));
  return { root, jobs, watchman: createWatchman({ registryFile, root, jobsDir: jobs }) };
}

test("a halted agent is not spawned, and the job waits instead of dying", async () => {
  const { root, jobs, watchman } = board({ id: "s1", agent: "watch", orders: "keep going" });
  fs.mkdirSync(path.join(root, "stop"));
  fs.writeFileSync(path.join(root, "stop", "watch.STOP"), "halt\n");

  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 0, "a halted agent did not start");

  const events = watchman.ledger.read();
  const held = events.find((entry) => entry.event === "job-halted");
  assert.ok(held, "the halt is on the ledger");
  assert.equal(held.reason, "stop-filed");
  assert.ok(!events.some((entry) => entry.event === "bell"), "no bell for work nobody did");

  // Paused, not judged: the job is still there and no receipt claims it ran.
  assert.ok(fs.existsSync(path.join(jobs, "s1.job.json")));
  assert.equal(fs.existsSync(path.join(jobs, "s1.result.json")), false);

  // A second poll while still halted does not repeat the line.
  await watchman.pollOnce();
  const heldLines = watchman.ledger.read().filter((entry) => entry.event === "job-halted");
  assert.equal(heldLines.length, 1);
});

test("clearing the halt resumes the very same job", async () => {
  const { root, jobs, watchman } = board({ id: "s2", agent: "watch", orders: "resume" });
  fs.mkdirSync(path.join(root, "stop"));
  const halt = path.join(root, "stop", "watch.STOP");
  fs.writeFileSync(halt, "halt\n");
  await watchman.pollOnce();

  fs.unlinkSync(halt);
  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 1, "the paused job runs once the halt is gone");
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 40));
  const events = watchman.ledger.read().map((entry) => entry.event);
  assert.ok(events.includes("job-resumed"));
  assert.ok(events.includes("bell"));
  assert.ok(events.includes("job-done"));
  assert.ok(fs.existsSync(path.join(jobs, "s2.result.json")));
});

test("a halt survives a restart without losing the work", async () => {
  const root = tmp();
  const jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({
    agents: [{ name: "watch", lane: "iso", command: ["node", "-e", "process.exit(0)"], budget: {} }],
  }));
  fs.writeFileSync(path.join(jobs, "s3.job.json"),
    JSON.stringify({ id: "s3", agent: "watch", orders: "resume after restart" }));
  fs.mkdirSync(path.join(root, "stop"));
  const halt = path.join(root, "stop", "watch.STOP");
  fs.writeFileSync(halt, "halt\n");

  await createWatchman({ registryFile, root, jobsDir: jobs }).pollOnce();
  const state = JSON.parse(fs.readFileSync(path.join(root, "watchman-state.json"), "utf8"));
  assert.deepEqual(state.halted, ["s3"], "the hold is recorded, not just remembered");

  fs.unlinkSync(halt);
  const restarted = createWatchman({ registryFile, root, jobsDir: jobs });
  const spawned = await restarted.pollOnce();
  assert.equal(spawned.length, 1, "a fresh watchman picks the job up");
  await spawned[0].handle.done;
});
