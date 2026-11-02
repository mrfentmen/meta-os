// Agent-layer edge cases: registry validation beyond the first
// duplicate, ledger recovery from a torn append, killing a handle
// that already exited, and watch transitions for a file that
// disappears. Real child processes, real files — no mocks.
// Run: node --test tests/agents-ledger-edges.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  loadRegistry,
  Ledger,
  spawnAgent,
  killAgent,
  watchState,
  pollWatch,
} from "../agents/runtime.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agents-edges-"));
const NODE = process.execPath;

function writeRegistry(dir, body) {
  const file = path.join(dir, "registry.json");
  fs.writeFileSync(file, JSON.stringify(body));
  return file;
}

test("registry rejects a non-array agents field, a missing name, and a non-positive budget", () => {
  const dir = tmp();
  assert.throws(
    () => loadRegistry(writeRegistry(dir, { agents: "nope" })),
    /'agents' must be an array/,
  );
  assert.throws(
    () => loadRegistry(writeRegistry(dir, { agents: [{ command: ["true"] }] })),
    /missing name/,
  );
  assert.throws(
    () => loadRegistry(writeRegistry(dir, { agents: [{ name: "a", command: ["true"], budget: { maxWallMs: 0 } }] })),
    /bad maxWallMs/,
  );
});

test("registry fills a missing budget with an empty object and leaves a real one alone", () => {
  const dir = tmp();
  const agents = loadRegistry(writeRegistry(dir, {
    agents: [
      { name: "plain", command: ["true"] },
      { name: "budgeted", command: ["true"], budget: { maxWallMs: 1000 } },
    ],
  }));
  assert.deepEqual(agents[0].budget, {});
  assert.equal(agents[1].budget.maxWallMs, 1000);
});

test("ledger round-trips fields and returns [] when the file does not exist", () => {
  const dir = tmp();
  const ledger = new Ledger(path.join(dir, "ledger.jsonl"));
  assert.deepEqual(ledger.read(), []);
  ledger.add("run-1", "spawn", { lane: "test" });
  ledger.add("run-1", "exit", { code: 0 });
  const rows = ledger.read();
  assert.equal(rows.length, 2);
  assert.equal(rows[0].run, "run-1");
  assert.equal(rows[0].event, "spawn");
  assert.equal(rows[0].lane, "test");
  assert.equal(rows[1].code, 0);
  assert.match(rows[0].ts, /^\d{4}-\d{2}-\d{2}T/);
});

test("ledger separates from a torn last line and keeps the records that are whole", () => {
  const dir = tmp();
  const file = path.join(dir, "ledger.jsonl");
  fs.writeFileSync(file, '{"run":"old","event":"spa'); // torn mid-append, no newline
  const ledger = new Ledger(file);
  ledger.add("run-new", "spawn");
  const rows = ledger.read();
  // The torn line is skipped; the record appended after it is kept.
  assert.equal(rows.length, 1);
  assert.equal(rows[0].run, "run-new");
  assert.equal(rows[0].event, "spawn");
});

test("a complete line with no trailing newline is still a record", () => {
  const dir = tmp();
  const file = path.join(dir, "ledger.jsonl");
  fs.writeFileSync(file, '{"run":"old","event":"spawn"}'); // complete JSON, just unterminated
  const ledger = new Ledger(file);
  ledger.add("run-new", "spawn");
  const rows = ledger.read();
  assert.deepEqual(rows.map((r) => r.run), ["old", "run-new"]);
});

test("killing an already-exited handle records the request but never a hard kill", async () => {
  const root = tmp();
  const h = spawnAgent({ name: "quick", command: [NODE, "-e", ""], budget: {} }, { root });
  await h.done;
  await killAgent(h, "late-kill", 50);
  const events = h.ledger.read().map((l) => l.event);
  assert.deepEqual(events, ["spawn", "exit", "stop-request"]);
  assert.equal(events.includes("killed-hard"), false);
});

test("a second kill is a no-op and keeps the first reason", async () => {
  const root = tmp();
  const h = spawnAgent({ name: "sleeper2", command: [NODE, "-e", "setTimeout(() => {}, 30000)"], budget: {} }, { root });
  await killAgent(h, "first-reason", 200);
  await killAgent(h, "second-reason", 200);
  const stops = h.ledger.read().filter((l) => l.event === "stop-request");
  assert.equal(stops.length, 1);
  assert.equal(stops[0].reason, "first-reason");
});

test("watchState reports a missing file and refuses an unsupported target type", () => {
  const dir = tmp();
  assert.deepEqual(watchState({ type: "file", path: path.join(dir, "absent.txt") }), { exists: false });
  assert.throws(() => watchState({ type: "socket", path: "/tmp/x" }), /unsupported target type/);
});

test("pollWatch reports a deleted file as a change and leaves other targets quiet", () => {
  const dir = tmp();
  const kept = path.join(dir, "kept.txt");
  const gone = path.join(dir, "gone.txt");
  fs.writeFileSync(kept, "still here");
  fs.writeFileSync(gone, "delete me");
  const targets = [
    { type: "file", path: kept },
    { type: "file", path: gone },
  ];
  const first = pollWatch(targets, {});
  assert.equal(first.changes.length, 0);
  fs.unlinkSync(gone);
  const next = pollWatch(targets, first.state);
  assert.equal(next.changes.length, 1);
  assert.equal(next.changes[0].key, `file:${gone}`);
  assert.deepEqual(next.changes[0].to, { exists: false });
  assert.deepEqual(next.state[`file:${kept}`], first.state[`file:${kept}`]);
});
