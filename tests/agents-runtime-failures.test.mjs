// Failure injection and restart semantics for the agent runtime (AGENT_LAYER_TASKS B3, B4).
//
// Every case here is a way the runtime loses a run's story without losing the process:
// a kill that lands mid-write, a ledger appended by a crashed runtime, a registry entry
// that is shaped right and names something that does not exist, two stops racing for the
// same run, and a runtime that dies leaving children behind. The assertions are written
// against spec §9 (budgets), §11 (receipts) and §12 (failure model).
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadRegistry, spawnAgent, killAgent, reconcileRuns, Ledger } from "../agents/runtime.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agents-fail-"));
const NODE = process.execPath;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------------------
// B3.1 — a kill that lands while the agent is writing

test("kill lands mid-write: the output is cut, the ledger is whole, the run is marked", async () => {
  const root = tmp();
  const work = path.join(root, "work.txt");
  // One character per 5 ms so a kill at ~150 ms lands in the middle of the stream, not at a
  // convenient boundary.
  const script = `
    const fs = require("node:fs");
    let i = 0;
    const t = setInterval(() => { fs.appendFileSync(${JSON.stringify(work)}, "line" + (i++) + "\\n"); }, 5);
    setTimeout(() => { clearInterval(t); }, 5000);
  `;
  const agent = { name: "writer", command: [NODE, "-e", script], budget: {} };
  const h = spawnAgent(agent, { root });
  await sleep(150);
  await killAgent(h, "test-mid-write", 300);

  // The work file is incomplete -- that is what a kill does -- and it is NOT a corrupt file:
  // every line it does have is a whole line.
  const wrote = fs.existsSync(work) ? fs.readFileSync(work, "utf8") : "";
  if (wrote.length > 0) {
    assert.ok(wrote.endsWith("\n"), "a partly written line was left behind");
  }
  // The ledger is the receipt and it survived the kill intact.
  const events = h.ledger.read();
  const names = events.map((e) => e.event);
  assert.equal(names[0], "spawn");
  assert.ok(names.includes("stop-request"));
  assert.equal(names[names.length - 1], "exit");
  assert.equal(events.find((e) => e.event === "stop-request").reason, "test-mid-write");
  assert.equal(events.find((e) => e.event === "exit").stopped, "test-mid-write");
});

// ---------------------------------------------------------------------------
// B3.2 — a ledger a crashed runtime left behind

test("a torn last line is a crash tail: read skips it and keeps the history", () => {
  const dir = tmp();
  const file = path.join(dir, "ledger.jsonl");
  const l = new Ledger(file);
  l.add("run-1", "spawn", {});
  l.add("run-1", "action", { n: 1 });
  fs.appendFileSync(file, '{"ts":"2026-11-02T00:00:0');    // the append that was in flight
  const events = l.read();
  assert.deepEqual(events.map((e) => e.event), ["spawn", "action"]);
});

test("a torn middle line is corruption, not a crash: read refuses and names the line", () => {
  const dir = tmp();
  const file = path.join(dir, "ledger.jsonl");
  const l = new Ledger(file);
  l.add("run-1", "spawn", {});
  const good = fs.readFileSync(file, "utf8");
  fs.writeFileSync(file, good + '{"ts":\n' + good.trim() + "\n");
  assert.throws(() => l.read(), /torn line 2/);
});

// ---------------------------------------------------------------------------
// B3.3 — registry entries that are shaped right and still wrong

test("registry refuses a command with a non-string argument", () => {
  const dir = tmp();
  const f = path.join(dir, "r.json");
  fs.writeFileSync(f, JSON.stringify({ agents: [{ name: "a", command: ["node", 42] }] }));
  assert.throws(() => loadRegistry(f), /command must be strings/);
});

test("registry refuses a watch target that would throw at the cadence", () => {
  const dir = tmp();
  const f = path.join(dir, "r.json");
  // `pollWatch` throws on an unsupported type, and today it does that inside a setInterval.
  fs.writeFileSync(f, JSON.stringify({ agents: [{ name: "a", command: ["true"], watch: [{ type: "url", path: "http://x" }] }] }));
  assert.throws(() => loadRegistry(f), /bad watch target/);
  fs.writeFileSync(f, JSON.stringify({ agents: [{ name: "a", command: ["true"], watch: "nope" }] }));
  assert.throws(() => loadRegistry(f), /watch must be an array/);
});

test("a registry entry naming a command that does not exist fails its run, not the runtime", async () => {
  const root = tmp();
  const agent = { name: "ghost", command: [path.join(root, "no-such-binary")], budget: {} };
  const h = spawnAgent(agent, { root });
  const result = await h.done;                    // must settle: an unhandled 'error' is a crash
  assert.equal(result.code, null);
  assert.match(result.error, /ENOENT/);
  const events = h.ledger.read().map((e) => e.event);
  assert.deepEqual(events, ["spawn", "spawn-error"]);
  // The brief still landed before the attempt, so the run has its orders on disk.
  assert.ok(fs.existsSync(path.join(h.runDir, "brief.json")));
});

// ---------------------------------------------------------------------------
// B3.4 — two stops racing for the same run

test("two concurrent stops produce one stop-request and one exit", async () => {
  const root = tmp();
  const agent = { name: "racer", command: [NODE, "-e", "setTimeout(() => {}, 30000)"], budget: {} };
  const h = spawnAgent(agent, { root });
  await Promise.all([killAgent(h, "first", 400), killAgent(h, "second", 400)]);
  const events = h.ledger.read();
  assert.equal(events.filter((e) => e.event === "stop-request").length, 1);
  assert.equal(events.filter((e) => e.event === "exit").length, 1);
  assert.equal(events.find((e) => e.event === "stop-request").reason, "first");
});

test("a stop that arrives after the run exited adds nothing", async () => {
  const root = tmp();
  const agent = { name: "quick", command: [NODE, "-e", "process.exit(0)"], budget: {} };
  const h = spawnAgent(agent, { root });
  await h.done;
  await killAgent(h, "too-late", 50);
  const events = h.ledger.read().map((e) => e.event);
  assert.deepEqual(events, ["spawn", "exit"]);
});

// ---------------------------------------------------------------------------
// B4 — the runtime dies; the runs it started survive as records

test("a run with no terminal event is marked orphaned, and its brief is untouched", () => {
  const root = tmp();
  const runDir = path.join(root, "runs", "left-behind-1");
  fs.mkdirSync(runDir, { recursive: true });
  const brief = JSON.stringify({ agent: "buffy", orders: "keep the lane green", run: "left-behind-1" }, null, 2);
  fs.writeFileSync(path.join(runDir, "brief.json"), brief);
  const l = new Ledger(path.join(runDir, "ledger.jsonl"));
  l.add("left-behind-1", "spawn", { command: ["node"] });
  l.add("left-behind-1", "action", { n: 1 });

  const first = reconcileRuns(root);
  assert.deepEqual(first.marked, ["left-behind-1"]);
  const events = l.read();
  const last = events[events.length - 1];
  assert.equal(last.event, "orphaned");
  assert.equal(last.reason, "runtime-died");
  assert.equal(last.lastEvent, "action");
  // The orders are the agent's, not the recovery pass's.
  assert.equal(fs.readFileSync(path.join(runDir, "brief.json"), "utf8"), brief);

  // Idempotent: a second restart does not stack marks.
  const second = reconcileRuns(root);
  assert.deepEqual(second.marked, []);
  assert.deepEqual(second.quiet, ["left-behind-1"]);
  assert.equal(l.read().filter((e) => e.event === "orphaned").length, 1);
});

test("a completed run is left alone, and an unreadable one is reported not repaired", () => {
  const root = tmp();
  const done = path.join(root, "runs", "finished-1");
  fs.mkdirSync(done, { recursive: true });
  const l = new Ledger(path.join(done, "ledger.jsonl"));
  l.add("finished-1", "spawn", {});
  l.add("finished-1", "exit", { code: 0, signal: null });

  const broken = path.join(root, "runs", "broken-1");
  fs.mkdirSync(broken, { recursive: true });
  const before = '{"ts":"x","run":"broken-1","event":"spawn"}\n{"ts":\n{"ts":"y","run":"broken-1","event":"exit"}\n';
  fs.writeFileSync(path.join(broken, "ledger.jsonl"), before);

  const res = reconcileRuns(root);
  assert.deepEqual(res.marked, []);
  assert.deepEqual(res.quiet, ["finished-1"]);
  assert.equal(res.unreadable.length, 1);
  assert.equal(res.unreadable[0].run, "broken-1");
  assert.match(res.unreadable[0].reason, /torn line 2/);
  // Reported, not rewritten.
  assert.equal(fs.readFileSync(path.join(broken, "ledger.jsonl"), "utf8"), before);
});

test("an empty or missing runs directory reconciles to nothing", () => {
  const root = tmp();
  assert.deepEqual(reconcileRuns(root), { marked: [], quiet: [], unreadable: [] });
  fs.mkdirSync(path.join(root, "runs"));
  assert.deepEqual(reconcileRuns(root), { marked: [], quiet: [], unreadable: [] });
});
