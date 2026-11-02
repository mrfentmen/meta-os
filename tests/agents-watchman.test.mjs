import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createWatchman } from "../agents/watchman.mjs";

const NODE = process.execPath;
// The worker proves it woke BRIEFED: it copies its orders out of
// brief.json (written by the runtime before spawn) into done.txt.
const WORKER = "const fs=require('fs');const b=JSON.parse(fs.readFileSync('brief.json','utf8'));fs.writeFileSync('done.txt','orders-were: '+b.orders)";

function setup() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "watchman-test-"));
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", lane: "test", command: [NODE, "-e", WORKER], budget: {} }] }));
  const jobsDir = path.join(dir, "jobs");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  return { dir, jobsDir, w };
}

test("a job on the board wakes the named agent, briefed, and leaves a result", async () => {
  const { jobsDir, w } = setup();
  fs.writeFileSync(path.join(jobsDir, "j1.job.json"), JSON.stringify({ id: "j1", agent: "worker", orders: "sweep the board" }));
  const spawned = await w.pollOnce();
  assert.equal(spawned.length, 1);
  const { code } = await spawned[0].handle.done;
  assert.equal(code, 0);
  const done = fs.readFileSync(path.join(spawned[0].handle.runDir, "done.txt"), "utf8");
  assert.equal(done, "orders-were: sweep the board");
  const result = JSON.parse(fs.readFileSync(path.join(jobsDir, "j1.result.json"), "utf8"));
  assert.equal(result.code, 0);
  const bells = w.ledger.read().filter((l) => l.event === "bell");
  assert.equal(bells.length, 1);
});

test("a claimed job is never spawned twice", async () => {
  const { jobsDir, w } = setup();
  fs.writeFileSync(path.join(jobsDir, "j2.job.json"), JSON.stringify({ id: "j2", agent: "worker", orders: "once only" }));
  const first = await w.pollOnce();
  await first[0].handle.done;
  const second = await w.pollOnce();
  assert.equal(second.length, 0);
});

test("a job for an unknown agent is logged, not crashed", async () => {
  const { jobsDir, w } = setup();
  fs.writeFileSync(path.join(jobsDir, "j3.job.json"), JSON.stringify({ id: "j3", agent: "ghost", orders: "boo" }));
  const spawned = await w.pollOnce();
  assert.equal(spawned.length, 0);
  assert.ok(w.ledger.read().some((l) => l.event === "job-unmatched" && l.id === "j3"));
});
