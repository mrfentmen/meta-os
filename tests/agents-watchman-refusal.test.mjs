// A job the layer refuses must not look like a job that ran. This drives the
// real watchman against a real jobs directory and a real over-cap memory.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { spawnSync } from "node:child_process";
import url from "node:url";

import { createWatchman } from "../agents/watchman.mjs";
import { memoryDir, writeRecord } from "../agents/memory.mjs";

const REPO = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-watchman-"));
}

function board(agent, job) {
  const root = tmp();
  const jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({ agents: [agent] }));
  fs.writeFileSync(path.join(jobs, job.id + ".job.json"), JSON.stringify(job));
  return {
    root,
    jobs,
    watchman: createWatchman({ registryFile, root, jobsDir: jobs }),
  };
}

test("an over-cap spawn is refused, not written as a bell and a done", async () => {
  const agent = {
    name: "rowan",
    lane: "test",
    command: ["true"],
    budget: {},
    memory: { maxBytes: 5 },
  };
  const { root, jobs, watchman } = board(agent, { id: "j1", agent: "rowan", orders: "go" });
  writeRecord(memoryDir(root, "rowan"), "baton.json", "eight-by", { maxBytes: 100 });

  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 0, "a refused spawn is not a spawn");

  const events = watchman.ledger.read().map((entry) => entry.event);
  assert.ok(events.includes("job-refused"), "the refusal is named");
  assert.ok(!events.includes("bell"), "no bell for a process that never started");
  assert.ok(!events.includes("job-done"), "no done for work nobody did");

  const refusal = watchman.ledger.read().find((entry) => entry.event === "job-refused");
  assert.equal(refusal.reason, "memory-cap");

  const result = JSON.parse(fs.readFileSync(path.join(jobs, "j1.result.json"), "utf8"));
  await new Promise((resolve) => setTimeout(resolve, 60));
  const notices = fs.readFileSync(path.join(root, "notices.jsonl"), "utf8")
    .trim().split("\n").map((line) => JSON.parse(line));
  const alarm = notices.find((notice) => notice.key === "job:j1:refused");
  assert.ok(alarm, "a refused job raises a notice");
  assert.equal(alarm.severity, "alarm");
  assert.equal(result.refused, "memory-cap");
  assert.equal(result.code, undefined);
});

test("the refused job is not retried on every poll", async () => {
  const agent = {
    name: "rowan",
    lane: "test",
    command: ["true"],
    budget: {},
    memory: { maxBytes: 5 },
  };
  const { root, watchman } = board(agent, { id: "j2", agent: "rowan", orders: "go" });
  writeRecord(memoryDir(root, "rowan"), "baton.json", "eight-by", { maxBytes: 100 });

  await watchman.pollOnce();
  await watchman.pollOnce();
  const refusals = watchman.ledger
    .read()
    .filter((entry) => entry.event === "job-refused" && entry.id === "j2");
  assert.equal(refusals.length, 1);
});

test("a valid job still rings the bell and completes", async () => {
  const agent = { name: "hana", lane: "test", command: ["true"], budget: {} };
  const { jobs, watchman } = board(agent, { id: "j3", agent: "hana", orders: "go" });
  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 1);
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 20));
  const events = watchman.ledger.read();
  assert.ok(events.some((entry) => entry.event === "bell"));
  assert.ok(events.some((entry) => entry.event === "job-done"));
  const result = JSON.parse(fs.readFileSync(path.join(jobs, "j3.result.json"), "utf8"));
  assert.equal(result.refused, undefined);
  assert.equal(result.code, 0);
});

test("the CLI writes its state where --root points, not next to the code", () => {
  const root = tmp();
  fs.mkdirSync(path.join(root, "jobs"));
  const registry = path.join(root, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [] }));
  fs.writeFileSync(
    path.join(root, "jobs", "j9.job.json"),
    JSON.stringify({ id: "j9", agent: "nobody" })
  );
  const run = spawnSync(process.execPath, [
    path.join(REPO, "agents", "watchman.mjs"),
    "--root", root, "--registry", registry, "--once",
  ], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr);
  assert.ok(fs.existsSync(path.join(root, "watchman.heartbeat.json")));
  assert.ok(fs.existsSync(path.join(root, "watchman.jsonl")));
  assert.equal(fs.existsSync(path.join(REPO, "agents", "watchman.jsonl")), false);
});
