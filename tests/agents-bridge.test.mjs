// Round 8, B2 — the bridge: order, dependency gate, and the three STOP windows.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createBridge, loadBoot } from "../agents/bridge.mjs";

const NODE = process.execPath;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function setup(boot, extraAgents = []) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agents-bridge-"));
  const registry = path.join(dir, "registry.json");
  const quick = "const fs=require('fs');fs.writeFileSync('done.txt','ok')";
  fs.writeFileSync(registry, JSON.stringify({
    agents: [
      { name: "first", command: [NODE, "-e", quick], budget: {} },
      { name: "second", command: [NODE, "-e", quick], budget: {} },
      { name: "sleeper", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: {} },
      { name: "napper", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: { maxWallMs: 300 } },
      ...extraAgents,
    ],
  }));
  const bootFile = path.join(dir, "boot.json");
  fs.writeFileSync(bootFile, JSON.stringify({ boot }));
  const b = createBridge({ root: dir, registryFile: registry, bootFile });
  return { dir, b, bootFile };
}

test("B2.1 the boot file's order is checked, not trusted", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agents-bridge-"));
  const f = path.join(dir, "b.json");
  fs.writeFileSync(f, JSON.stringify({ boot: [{ agent: "a", needs: ["b"] }, { agent: "b", needs: [] }] }));
  assert.throws(() => loadBoot(f), /does not come earlier/);
  fs.writeFileSync(f, JSON.stringify({ boot: [{ agent: "a", needs: ["ghost"] }] }));
  assert.throws(() => loadBoot(f), /unknown agent/);
  fs.writeFileSync(f, JSON.stringify({ boot: [{ agent: "a" }, { agent: "a" }] }));
  assert.throws(() => loadBoot(f), /duplicate/);
});

test("B2.2 a dependency that is not running refuses the start, and says why", () => {
  const { b } = setup([{ agent: "second", needs: ["first"] }, { agent: "first", needs: [] }].reverse());
  const r = b.start("second");
  assert.equal(r.ok, false);
  assert.equal(r.reason, "needs-not-running");
  const refusal = b.ledger.read().find((l) => l.event === "refused");
  assert.deepEqual(refusal.missing, ["first"]);
});

test("B2.3 bootAll starts in order and leaves both running", async () => {
  const { b } = setup([{ agent: "first", needs: [] }, { agent: "second", needs: ["first"] }]);
  const out = b.bootAll();
  assert.deepEqual(out.map((r) => r.ok), [true, true]);
  assert.equal(b.slots.get("second").state, "running");
  await Promise.all(out.map((r) => r.handle.done));
  await sleep(10);
  assert.equal(b.slots.get("first").state, "stopped");
  assert.equal(b.slots.get("second").state, "stopped");
});

test("B2.4 a STOP filed before the claim means nothing is spawned (window 1)", () => {
  const { dir, b } = setup([{ agent: "first", needs: [] }]);
  fs.mkdirSync(path.join(dir, "stop"), { recursive: true });
  fs.writeFileSync(path.join(dir, "stop", "first.STOP"), "stop\n");
  const r = b.start("first");
  assert.equal(r.ok, false);
  assert.equal(r.reason, "stop-filed");
  assert.equal(b.slots.get("first").runId, null, "no run was created");
  assert.ok(b.ledger.read().some((l) => l.event === "stop-pre-spawn"));
});

test("B2.5 a STOP during the run kills it and records why (window 2)", async () => {
  const { b } = setup([{ agent: "sleeper", needs: [] }]);
  const r = b.start("sleeper");
  assert.ok(r.ok);
  await sleep(20);
  await b.stop("sleeper", "drill");
  const events = b.ledger.read();
  assert.ok(events.some((l) => l.event === "stop-request" && l.reason === "drill"));
  const exit = events.find((l) => l.event === "exited");
  assert.equal(exit.state, "stopped");
  assert.equal(exit.stopped, "bridge:drill");
});

test("B2.6 an unrequested nonzero exit is a failure; a budget kill is a stop", async () => {
  const { b } = setup([{ agent: "first", needs: [] }]);
  b.start("first");
  await sleep(60);
  assert.equal(b.slots.get("first").state, "stopped");

  const crash = "process.exit(3)";
  const { b: b2 } = setup([{ agent: "crashy", needs: [] }], [{ name: "crashy", command: [NODE, "-e", crash], budget: {} }]);
  b2.start("crashy");
  await sleep(80);
  assert.equal(b2.slots.get("crashy").state, "failed");
  assert.equal(b2.ledger.read().find((l) => l.event === "exited").code, 3);

  const { b: b3 } = setup([{ agent: "napper", needs: [] }]);
  b3.start("napper");
  await sleep(500);
  const exit = b3.ledger.read().find((l) => l.event === "exited");
  assert.equal(exit.state, "stopped", "a budget kill is a requested stop, not a failure");
  assert.equal(exit.code, null);
});
