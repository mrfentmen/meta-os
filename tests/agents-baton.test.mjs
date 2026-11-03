import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createWatchman } from "../agents/watchman.mjs";
import { writeBaton, readBaton } from "../agents/baton.mjs";

const NODE = process.execPath;
const WRITER = "const fs=require('fs');fs.writeFileSync('baton.json',JSON.stringify({state:'west wall half built',artifacts:['wall.txt'],nextStep:'finish the west wall'}))";
const READER = "const fs=require('fs');const b=JSON.parse(fs.readFileSync('brief.json','utf8'));fs.writeFileSync('done.txt',b.orders)";

test("baton record round-trips", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "baton-test-"));
  writeBaton(dir, { stepIndex: 0, state: "s", nextStep: "n" });
  const b = readBaton(dir);
  assert.equal(b.state, "s"); assert.equal(b.nextStep, "n");
  assert.equal(readBaton(path.join(dir, "nope")), null);
});

test("the pass: agent B continues from agent A's baton, briefed by the watchman", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "baton-pass-"));
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [
    { name: "first", command: [NODE, "-e", WRITER], budget: {} },
    { name: "second", command: [NODE, "-e", READER], budget: {} },
  ] }));
  const jobsDir = path.join(dir, "jobs");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  fs.writeFileSync(path.join(jobsDir, "a.job.json"), JSON.stringify({ id: "a", agent: "first", orders: "build the west wall" }));
  const [sa] = await w.pollOnce();
  await sa.handle.done;
  fs.writeFileSync(path.join(jobsDir, "b.job.json"), JSON.stringify({ id: "b", agent: "second", continuesFrom: sa.handle.runId, orders: "mind the gate" }));
  const [sb] = await w.pollOnce();
  await sb.handle.done;
  const done = fs.readFileSync(path.join(sb.handle.runDir, "done.txt"), "utf8");
  assert.match(done, /Continuation of run/);
  assert.match(done, /finish the west wall/);
  assert.match(done, /mind the gate/);
  assert.ok(w.ledger.read().some((l) => l.event === "baton-pass"));
});
