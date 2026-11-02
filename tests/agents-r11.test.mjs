// Round 11 finish — hosted loops (254..261): real commands, pre-spawn STOP, relay results,
// restart fallback, baton continuation with no duplicate write, budget receipt.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnAgent, resolveCommand, Ledger } from "../agents/runtime.mjs";
import { createWatchman } from "../agents/watchman.mjs";
import { hostedLoops, spawnHosted, stopDrill, stopMarker } from "../agents/hosted.mjs";
import { writeBaton } from "../agents/baton.mjs";

const NODE = process.execPath;
const ROOT = path.resolve(import.meta.dirname, "..");
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agents-r11-"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

test("R11-261 every hosted entry has a real command; every placeholder is marked draft and says why", () => {
  const agents = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8")).agents;
  const hosted = hostedLoops(agents);
  assert.equal(hosted.length, 5);
  for (const a of hosted) {
    assert.equal(a.command[0], "repo:node", a.name + " uses the portable node token");
    assert.equal(a.draft, undefined, a.name + " is not draft");
    assert.ok(fs.existsSync(path.join(ROOT, a.command[1])), a.name + " names a file that exists");
  }
  const drafts = agents.filter((a) => a.draft === true);
  assert.ok(drafts.length >= 20, "the rest are in the open, not silently placeholder");
  for (const a of drafts) assert.ok(a.draftReason && a.draftReason.length > 20, a.name + " says why it is draft");
  assert.equal(resolveCommand(["repo:node", "aegis/hosted.mjs"], "/r")[0], process.execPath);
  assert.equal(resolveCommand(["repo:node", "aegis/hosted.mjs"], "/r")[1], "/r/aegis/hosted.mjs");
});

test("R11-235/254 the Aegis hosted loop runs its real command and leaves a complete ledger", async () => {
  const agents = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8")).agents;
  const aegis = agents.find((a) => a.name === "aegis");
  const r = spawnHosted(aegis, { root: ROOT });
  assert.equal(r.ok, true);
  const { code } = await r.handle.done;
  assert.equal(code, 0);
  const events = r.handle.ledger.read().map((l) => l.event);
  assert.deepEqual(events, ["spawn", "exit"]);
  assert.ok(fs.existsSync(path.join(ROOT, "os-build", "aegis", "r11", "hosted-receipt.json")));
});

test("R11-255 the Nervus hosted loop files stub records only", async () => {
  const agents = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8")).agents;
  const nervus = agents.find((a) => a.name === "nervus");
  const r = spawnHosted(nervus, { root: ROOT });
  assert.equal(r.ok, true);
  assert.equal((await r.handle.done).code, 0);
  const receipt = JSON.parse(fs.readFileSync(path.join(ROOT, "os-build", "nervus", "hosted-receipt.json"), "utf8"));
  assert.equal(receipt.stub, true);
  assert.ok(receipt.rows.every((x) => x.ok));
});

test("R11-244 the three Hands-Free entries run their real commands to exit 0", async () => {
  const agents = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8")).agents;
  for (const name of ["handsfree-intake", "handsfree-brief", "handsfree-approval"]) {
    const r = spawnHosted(agents.find((a) => a.name === name), { root: ROOT });
    assert.equal(r.ok, true, name);
    const { code } = await r.handle.done;
    assert.equal(code, 0, name + " exited " + code);
    assert.deepEqual(r.handle.ledger.read().map((l) => l.event), ["spawn", "exit"], name + " left one clean run");
  }
  assert.ok(fs.existsSync(path.join(ROOT, "os-build", "handsfree", "brief.txt")));
  assert.ok(fs.existsSync(path.join(ROOT, "os-build", "handsfree", "intake-receipt.json")));
});

test("R11-260 every hosted loop refuses a STOP filed before it starts", () => {
  const agents = JSON.parse(fs.readFileSync(path.join(ROOT, "agents", "registry.json"), "utf8")).agents;
  const dir = tmp();
  for (const a of hostedLoops(agents)) {
    const drill = stopDrill(a, { root: dir });
    assert.equal(drill.refused.ok, false, a.name + " must refuse");
    assert.equal(drill.refused.reason, "stop-filed");
    assert.ok(fs.existsSync(stopMarker(dir, a.name)));
    drill.cleared();
    assert.equal(fs.existsSync(stopMarker(dir, a.name)), false);
  }
});

test("R11-256 a job arrives on the relay board and the result goes back on the outbox, once", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", command: [NODE, "-e", "require('fs').writeFileSync('done.txt','ran')"], budget: {} }] }));
  const inbox = path.join(dir, "inbox");
  const outbox = path.join(dir, "outbox");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir: inbox, resultDir: outbox });
  fs.writeFileSync(path.join(inbox, "j1.job.json"), JSON.stringify({ id: "j1", agent: "worker", orders: "relay" }));
  const [s] = await w.pollOnce();
  await s.handle.done;
  const result = JSON.parse(fs.readFileSync(path.join(outbox, "j1.result.json"), "utf8"));
  assert.equal(result.code, 0);
  assert.ok(result.finishedAt, "the result carries a finish time for latency");
  assert.equal((await w.pollOnce()).length, 0);
  assert.equal(w.ledger.read().filter((l) => l.event === "bell").length, 1);
});

test("R11-257 a job that lands while the watchman is down runs exactly once on restart", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", command: [NODE, "-e", ""], budget: {} }] }));
  const jobsDir = path.join(dir, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  fs.writeFileSync(path.join(jobsDir, "late.job.json"), JSON.stringify({ id: "late", agent: "worker", orders: "after restart" }));

  const restarted = createWatchman({ registryFile: registry, root: dir, jobsDir });
  const first = await restarted.pollOnce();
  assert.equal(first.length, 1);
  await first[0].handle.done;
  assert.equal((await restarted.pollOnce()).length, 0);
});

test("R11-258 the baton continues across two loops and writes each artifact once", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  // Both loops work on the SAME artifact path. Each run gets its own cwd, so a relative path
  // would make this test pass by writing two different files -- the exact failure it exists to
  // catch.
  const log = JSON.stringify(path.join(dir, "log.txt"));
  const FIRST = "const fs=require('fs');fs.writeFileSync(" + log + ",'first\\n');fs.writeFileSync('baton.json',JSON.stringify({state:'one line written',artifacts:[" + log + "],nextStep:'append the second line'}))";
  const SECOND = "const fs=require('fs');const b=JSON.parse(fs.readFileSync('brief.json','utf8'));fs.appendFileSync(" + log + ",'second\\n');fs.writeFileSync('done.txt',b.orders)";
  fs.writeFileSync(registry, JSON.stringify({ agents: [
    { name: "first", command: [NODE, "-e", FIRST], budget: {} },
    { name: "second", command: [NODE, "-e", SECOND], budget: {} },
  ] }));
  const jobsDir = path.join(dir, "jobs");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });

  fs.writeFileSync(path.join(jobsDir, "a.job.json"), JSON.stringify({ id: "a", agent: "first", orders: "start" }));
  const [a] = await w.pollOnce();
  await a.handle.done;
  fs.writeFileSync(path.join(jobsDir, "b.job.json"), JSON.stringify({ id: "b", agent: "second", continuesFrom: a.handle.runId, orders: "continue" }));
  const [b] = await w.pollOnce();
  await b.handle.done;

  const lines = fs.readFileSync(path.join(dir, "log.txt"), "utf8").trim().split("\n");
  assert.deepEqual(lines, ["first", "second"], "no line was written twice");
  assert.equal(w.ledger.read().filter((l) => l.event === "baton-pass").length, 1);
  assert.match(fs.readFileSync(path.join(b.handle.runDir, "done.txt"), "utf8"), /one line written/);
});

test("R11-259 a budget kill writes its receipt before the stop", async () => {
  const dir = tmp();
  const agent = { name: "capped", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: { maxWallMs: 250 } };
  const h = spawnAgent(agent, { root: dir });
  await h.done;
  const receipt = JSON.parse(fs.readFileSync(path.join(h.runDir, "receipt.json"), "utf8"));
  assert.equal(receipt.reason, "budget-wall-clock");
  assert.equal(receipt.capMs, 250);
  const events = h.ledger.read().map((l) => l.event);
  assert.ok(events.includes("budget-receipt"));
  assert.ok(events.indexOf("budget-receipt") < events.indexOf("exit"));
  const exit = h.ledger.read().find((l) => l.event === "exit");
  assert.equal(exit.stopped, "budget-wall-clock");
});
