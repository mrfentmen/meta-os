// The memory cap is only real if the runtime honours it. These tests spawn
// real child processes and read the ledger the layer actually wrote.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { spawnAgent, killAgent } from "../agents/runtime.mjs";
import { memoryDir, writeRecord } from "../agents/memory.mjs";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-memory-run-"));
}

function agent(extra = {}) {
  return {
    name: "rowan",
    lane: "test",
    command: ["/bin/sh", "-c", "exit 0"],
    budget: {},
    ...extra,
  };
}

test("a spawn and its exit are written to the agent's own memory", async () => {
  const root = tmp();
  const handle = spawnAgent(agent(), { root });
  await handle.done;
  const ledger = fs
    .readFileSync(path.join(memoryDir(root, "rowan"), "ledger.jsonl"), "utf8")
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line));
  assert.deepEqual(ledger.map((l) => l.event), ["spawn", "exit"]);
  assert.equal(ledger[0].run, handle.runId);
});

test("a memory already over its cap refuses the spawn, with a receipt", async () => {
  const root = tmp();
  const dir = memoryDir(root, "rowan");
  writeRecord(dir, "baton.json", "x".repeat(200), { maxBytes: 4096 });
  const handle = spawnAgent(agent({ memory: { maxBytes: 100 } }), { root });
  assert.equal(handle.stopped, "memory-cap");
  assert.equal(handle.child, null);
  const receipt = JSON.parse(fs.readFileSync(path.join(handle.runDir, "receipt.json"), "utf8"));
  assert.equal(receipt.reason, "memory-cap");
  assert.ok(receipt.usedBytes > receipt.capBytes);
});

test("a spawn that would cross the cap never starts a process", async () => {
  const root = tmp();
  const dir = memoryDir(root, "rowan");
  writeRecord(dir, "baton.json", "x".repeat(60), { maxBytes: 4096 });
  const handle = spawnAgent(agent({ memory: { maxBytes: 70 } }), { root });
  assert.equal(handle.stopped, "memory-cap");
  assert.equal(fs.existsSync(path.join(dir, "ledger.jsonl")), false);
});

test("a stop is recorded in the agent's memory", async () => {
  const root = tmp();
  const handle = spawnAgent(
    agent({ command: ["/bin/sh", "-c", "sleep 5"] }),
    { root }
  );
  await new Promise((resolve) => setTimeout(resolve, 150));
  await killAgent(handle, "test-stop", 200);
  const ledger = fs
    .readFileSync(path.join(memoryDir(root, "rowan"), "ledger.jsonl"), "utf8")
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line));
  const stop = ledger.find((l) => l.event === "stop");
  assert.equal(stop.reason, "test-stop");
  assert.ok(ledger.some((l) => l.event === "exit"));
});

test("a run still finishes when the memory fills mid-flight", async () => {
  // Measure a real spawn line instead of guessing sizes: the cap is set to
  // exactly that line plus a little, so the exit record cannot fit.
  const probeRoot = tmp();
  const probe = spawnAgent(agent(), { root: probeRoot });
  await probe.done;
  const spawnBytes = fs.statSync(
    path.join(memoryDir(probeRoot, "rowan"), "ledger.jsonl")
  ).size;
  const cap = spawnBytes + 5;

  const root = tmp();
  writeRecord(memoryDir(root, "rowan"), "baton.json", "x".repeat(5), { maxBytes: cap });
  const handle = spawnAgent(agent({ memory: { maxBytes: cap } }), { root });
  const result = await handle.done;
  assert.equal(result.code, 0);
  const refused = handle.ledger.read().find((l) => l.event === "memory-write-failed");
  assert.ok(refused, "the refused exit record is named in the run ledger");
  assert.equal(refused.event, "memory-write-failed");
});
