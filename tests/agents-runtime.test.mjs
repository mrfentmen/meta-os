import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadRegistry, spawnAgent, killAgent, pollWatch } from "../agents/runtime.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agents-test-"));
const NODE = process.execPath;

test("registry loads and rejects duplicates and missing commands", () => {
  const dir = tmp();
  const good = path.join(dir, "r.json");
  fs.writeFileSync(good, JSON.stringify({ agents: [{ name: "a", command: ["true"] }] }));
  assert.equal(loadRegistry(good).length, 1);
  const dup = path.join(dir, "d.json");
  fs.writeFileSync(dup, JSON.stringify({ agents: [{ name: "a", command: ["true"] }, { name: "a", command: ["true"] }] }));
  assert.throws(() => loadRegistry(dup), /duplicate/);
  const bad = path.join(dir, "b.json");
  fs.writeFileSync(bad, JSON.stringify({ agents: [{ name: "x" }] }));
  assert.throws(() => loadRegistry(bad), /missing command/);
});

test("spawn runs a real child to exit 0 and writes brief + ledger", async () => {
  const root = tmp();
  const agent = { name: "echoer", lane: "test", command: [NODE, "-e", "console.log('hi from agent')"], budget: {} };
  const h = spawnAgent(agent, { root, job: { orders: "say hi" } });
  const { code } = await h.done;
  assert.equal(code, 0);
  const brief = JSON.parse(fs.readFileSync(path.join(h.runDir, "brief.json"), "utf8"));
  assert.equal(brief.orders, "say hi");
  const events = h.ledger.read().map((l) => l.event);
  assert.deepEqual(events, ["spawn", "exit"]);
  assert.match(fs.readFileSync(path.join(h.runDir, "output.log"), "utf8"), /hi from agent/);
});

test("kill is graceful first and lands in the ledger", async () => {
  const root = tmp();
  const agent = { name: "sleeper", command: [NODE, "-e", "setTimeout(() => {}, 30000)"], budget: {} };
  const h = spawnAgent(agent, { root });
  await killAgent(h, "test-kill", 300);
  const events = h.ledger.read().map((l) => l.event);
  assert.ok(events.includes("stop-request"));
  assert.ok(events.includes("exit"));
});

test("wall-clock budget stops a runaway agent", async () => {
  const root = tmp();
  const agent = { name: "runaway", command: [NODE, "-e", "setTimeout(() => {}, 30000)"], budget: { maxWallMs: 300 } };
  const h = spawnAgent(agent, { root });
  const { signal } = await h.done;
  assert.ok(signal === "SIGTERM" || signal === "SIGKILL");
  const stop = h.ledger.read().find((l) => l.event === "stop-request");
  assert.equal(stop.reason, "budget-wall-clock");
});

test("STOP file stops the agent at a checkpoint", async () => {
  const root = tmp();
  const agent = { name: "stoppable", command: [NODE, "-e", "setTimeout(() => {}, 30000)"], budget: {} };
  const h = spawnAgent(agent, { root });
  fs.writeFileSync(path.join(h.runDir, "STOP"), "");
  await h.done;
  const stop = h.ledger.read().find((l) => l.event === "stop-request");
  assert.equal(stop.reason, "stop-file");
});

test("watch detects a file change and stays quiet when nothing moves", () => {
  const dir = tmp();
  const f = path.join(dir, "watched.txt");
  fs.writeFileSync(f, "one");
  const targets = [{ type: "file", path: f }];
  const first = pollWatch(targets, {});
  assert.equal(first.changes.length, 0);
  const quiet = pollWatch(targets, first.state);
  assert.equal(quiet.changes.length, 0);
  fs.appendFileSync(f, " two");
  const moved = pollWatch(targets, quiet.state);
  assert.equal(moved.changes.length, 1);
});
