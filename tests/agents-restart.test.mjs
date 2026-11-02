// Round 8, A2 — restart semantics.
//
// The state a crashed daemon leaves on disk is small and specific, and every case here builds
// exactly that state (or produces it with a real run), then starts a fresh watchman on it:
//
//   claimed, no bell        crash between claim and spawn  -> unclaim, retry
//   bell, run without exit  crash mid-run                  -> mark run-orphaned, resume from baton
//   bell, run with exit     finished, result write lost    -> leave claimed, do not re-run
//   result on disk          finished                        -> never spawn again
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createWatchman } from "../agents/watchman.mjs";
import { Ledger } from "../agents/runtime.mjs";
import { writeBaton } from "../agents/baton.mjs";

const NODE = process.execPath;
const WORKER = "const fs=require('fs');const b=JSON.parse(fs.readFileSync('brief.json','utf8'));fs.writeFileSync('done.txt',b.orders)";

function setup(extra = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agents-restart-"));
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({
    agents: [{ name: "worker", lane: "test", command: [NODE, "-e", WORKER], budget: {} }],
  }));
  const jobsDir = path.join(dir, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  const state = path.join(dir, "watchman-state.json");
  if (extra.claimed) fs.writeFileSync(state, JSON.stringify({ claimed: extra.claimed, resume: {} }));
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  return { dir, jobsDir, registry, state, w };
}

function crashedRun(dir, id, { exit = false } = {}) {
  const runDir = path.join(dir, "runs", id);
  fs.mkdirSync(runDir, { recursive: true });
  const l = new Ledger(path.join(runDir, "ledger.jsonl"));
  l.add(id, "spawn", { lane: "test" });
  if (exit) l.add(id, "exit", { code: 0 });
  writeBaton(runDir, { state: "west wall half built", artifacts: ["wall.txt"], nextStep: "finish the west wall" });
  return runDir;
}

test("A2.1 a run that died mid-flight is marked and resumed from its baton", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agents-restart-"));
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", command: [NODE, "-e", WORKER], budget: {} }] }));
  const jobsDir = path.join(dir, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  const runDir = crashedRun(dir, "r-old");
  new Ledger(path.join(dir, "watchman.jsonl")).add("watchman", "bell", { id: "j1", agent: "worker", run: "r-old" });
  fs.writeFileSync(path.join(dir, "watchman-state.json"), JSON.stringify({ claimed: ["j1"], resume: {} }));
  fs.writeFileSync(path.join(jobsDir, "j1.job.json"), JSON.stringify({ id: "j1", agent: "worker", orders: "mind the gate" }));

  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  const recovered = w.recovered;
  assert.equal(recovered.length, 1);
  assert.deepEqual(recovered[0], { id: "j1", action: "resume", from: "r-old" });
  assert.ok(new Ledger(path.join(runDir, "ledger.jsonl")).read().some((l) => l.event === "run-orphaned"),
    "the dead run is marked, so its record does not read as a clean finish");

  const spawned = await w.pollOnce();
  assert.equal(spawned.length, 1);
  const { handle } = spawned[0];
  await handle.done;
  const orders = fs.readFileSync(path.join(handle.runDir, "done.txt"), "utf8");
  assert.match(orders, /Continuation of run r-old/);
  assert.match(orders, /west wall half built/);
  assert.match(orders, /mind the gate/);
  assert.ok(w.ledger.read().some((l) => l.event === "resume-from-orphan" && l.from === "r-old"));
  assert.ok(w.ledger.read().some((l) => l.event === "baton-pass" && l.from === "r-old"));
});

test("A2.2 a claim that was never spawned is released and retried", async () => {
  const { dir, jobsDir, w } = setup({ claimed: ["j2"] });
  fs.writeFileSync(path.join(jobsDir, "j2.job.json"), JSON.stringify({ id: "j2", agent: "worker", orders: "retry me" }));
  assert.deepEqual(w.recovered, [{ id: "j2", action: "unclaimed", reason: "claimed but never spawned" }]);
  const spawned = await w.pollOnce();
  assert.equal(spawned.length, 1);
  await spawned[0].handle.done;
  assert.ok(fs.existsSync(path.join(dir, "jobs", "j2.result.json")));
});

test("A2.3 a completed job is never spawned again by a fresh watchman", async () => {
  const { dir, jobsDir, registry, w } = setup();
  fs.writeFileSync(path.join(jobsDir, "j3.job.json"), JSON.stringify({ id: "j3", agent: "worker", orders: "once" }));
  const first = await w.pollOnce();
  await first[0].handle.done;

  const w2 = createWatchman({ registryFile: registry, root: dir, jobsDir });
  assert.deepEqual(w2.recovered, []);
  assert.equal((await w2.pollOnce()).length, 0);
});

test("A2.4 a finished run whose result file was lost is not re-run", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agents-restart-"));
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", command: [NODE, "-e", WORKER], budget: {} }] }));
  const jobsDir = path.join(dir, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  crashedRun(dir, "r-done", { exit: true });
  new Ledger(path.join(dir, "watchman.jsonl")).add("watchman", "bell", { id: "j4", agent: "worker", run: "r-done" });
  fs.writeFileSync(path.join(dir, "watchman-state.json"), JSON.stringify({ claimed: ["j4"], resume: {} }));
  fs.writeFileSync(path.join(jobsDir, "j4.job.json"), JSON.stringify({ id: "j4", agent: "worker", orders: "done already" }));

  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  assert.deepEqual(w.recovered, []);
  assert.equal((await w.pollOnce()).length, 0);
});
