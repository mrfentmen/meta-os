import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Ledger, validateEntry, resolveCommand, spawnAgent } from "../agents/runtime.mjs";
import { writeBaton, handoffChain } from "../agents/baton.mjs";
import { createWatchman } from "../agents/watchman.mjs";
import { recordGymResult } from "../agents/gym.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "cb100-"));

test("CB-001 ledger rejects a record with no run, naming the field", () => {
  const l = new Ledger(path.join(tmp(), "l.jsonl"));
  assert.throws(() => l.add("", "spawn"), /missing required field run/);
  assert.throws(() => l.add("r1", ""), /missing required field event/);
});

test("CB-002 torn final line is skipped, whole records survive", () => {
  const f = path.join(tmp(), "l.jsonl");
  fs.writeFileSync(f, '{"run":"a","event":"spawn"}\n{"run":"b","eve');
  const rows = new Ledger(f).read();
  assert.equal(rows.length, 1);
  assert.equal(rows[0].event, "spawn");
});

test("CB-003 torn job is logged, not fatal", async () => {
  const root = tmp(), jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const reg = path.join(root, "registry.json");
  fs.writeFileSync(reg, JSON.stringify({ agents: [{ name: "a", lane: "l", command: ["true"], budget: {} }] }));
  fs.writeFileSync(path.join(jobs, "j1.job.json"), '{"agent":"a","id":"j1"');
  const w = createWatchman({ registryFile: reg, root, jobsDir: jobs });
  await w.pollOnce();
  assert.ok(w.ledger.read().some((r) => r.event === "job-unreadable"));
});

test("CB-004 claims persist across a watchman restart", async () => {
  const root = tmp(), jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const reg = path.join(root, "registry.json");
  fs.writeFileSync(reg, JSON.stringify({ agents: [{ name: "a", lane: "l", command: ["true"], budget: {} }] }));
  fs.writeFileSync(path.join(jobs, "j1.job.json"), JSON.stringify({ id: "j1", agent: "nobody" }));
  const w1 = createWatchman({ registryFile: reg, root, jobsDir: jobs });
  await w1.pollOnce();
  assert.ok(w1.state().claimed.includes("j1"));
  // The claim is on disk, so a reload sees the same id.
  const persisted = JSON.parse(fs.readFileSync(path.join(root, "watchman-state.json"), "utf8"));
  assert.ok(persisted.claimed.includes("j1"));
  // A restart keeps the same claimed id and retries the unspawned claim once.
  const w2 = createWatchman({ registryFile: reg, root, jobsDir: jobs });
  assert.equal(w2.state().claimed.includes("j1"), true);
  assert.ok(w2.recovered.some((r) => r.id === "j1" && r.action === "retry"));
});

test("CB-004 registry validator names a missing lane", () => {
  assert.throws(() => validateEntry({ name: "x", command: ["true"], budget: {} }), /missing field lane/);
  assert.throws(() => validateEntry({ name: "x", lane: "l", command: [], budget: {} }), /missing command/);
  assert.equal(validateEntry({ name: "x", lane: "l", command: ["true"], budget: {} }), true);
});

test("CB-005 baton refuses a finished job and records the reason", () => {
  const dir = tmp();
  assert.throws(() => writeBaton(dir, { finished: true }), /job already finished/);
  const refusal = JSON.parse(fs.readFileSync(path.join(dir, "baton-refused.json"), "utf8"));
  assert.equal(refusal.reason, "job already finished");
  assert.equal(fs.existsSync(path.join(dir, "baton.json")), false);
});

test("CB-006 a three-link chain keeps one job id and three authors in order", () => {
  const chain = handoffChain([
    { jobId: "j1", author: "a" }, { jobId: "j1", author: "b" }, { jobId: "j1", author: "c" }]);
  assert.equal(chain.jobId, "j1");
  assert.deepEqual(chain.authors, ["a", "b", "c"]);
  assert.throws(() => handoffChain([{ jobId: "j1", author: "a" }, { jobId: "j2", author: "b" }]), /job id changed/);
});

test("CB-008 command arguments are never shell-joined", () => {
  const cmd = resolveCommand(["echo", "a; touch pwned"], "/repo");
  assert.equal(cmd[1], "a; touch pwned");
  assert.equal(fs.existsSync("pwned"), false);
});

test("CB-010 a failed gym task leaves a named record", () => {
  const root = tmp();
  const reg = path.join(root, "registry.json");
  fs.writeFileSync(reg, JSON.stringify({ agents: [{ name: "a", lane: "l", command: ["true"], budget: {} }] }, null, 1));
  const ledger = path.join(root, "gym.jsonl");
  recordGymResult({ registryFile: reg, gymLedgerFile: ledger, result: {
    agent: "a", drill: "d", at: "now", total: 0, max: 1,
    tasks: [{ id: "spawn-clean-exit", score: 0, max: 1 }] } });
  const fail = new Ledger(ledger).read().find((r) => r.event === "gym-fail");
  assert.equal(fail.task, "spawn-clean-exit");
});

test("CB-009 budget receipt is written before the kill", async () => {
  const root = tmp();
  const agent = { name: "sleeper", lane: "test", command: [process.execPath, "-e", "setTimeout(()=>{},5000)"], budget: { maxWallMs: 80 } };
  const h = spawnAgent(agent, { root });
  await h.done;
  const events = h.ledger.read().map((r) => r.event);
  assert.ok(events.includes("budget-receipt"));
  assert.ok(fs.existsSync(path.join(h.runDir, "receipt.json")));
});
