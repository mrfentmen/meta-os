// Tests for agents/memory.mjs — real directories, real files, no mocks.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  DEFAULT_MAX_BYTES,
  MemoryError,
  memoryDir,
  capFor,
  usage,
  writeRecord,
  appendLedger,
  readLedger,
  check,
} from "../agents/memory.mjs";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-memory-"));
}

function refuses(code, fn) {
  assert.throws(fn, (error) => error instanceof MemoryError && error.code === code);
}

test("an agent gets its own directory and a bad name is refused", () => {
  const root = tmp();
  assert.equal(memoryDir(root, "rowan"), path.join(root, "memory", "rowan"));
  refuses("memory-name", () => memoryDir(root, "../etc"));
  refuses("memory-name", () => memoryDir(root, ""));
});

test("the cap comes from the registry, with a default for old entries", () => {
  assert.equal(capFor({ name: "a", memory: { maxBytes: 1024 } }), 1024);
  assert.equal(capFor({ name: "a" }), DEFAULT_MAX_BYTES);
  refuses("memory-cap", () => capFor({ name: "a", memory: { maxBytes: 0 } }));
  refuses("memory-cap", () => capFor({ name: "a", memory: { maxBytes: 1.5 } }));
});

test("a record under the cap is written and counted", () => {
  const dir = memoryDir(tmp(), "rowan");
  writeRecord(dir, "baton.json", { stepIndex: 2, state: "reading" }, { maxBytes: 4096 });
  const used = usage(dir);
  assert.equal(used.files, 1);
  assert.ok(used.bytes > 0);
});

test("a write that would cross the cap is refused and leaves nothing behind", () => {
  const root = tmp();
  const dir = memoryDir(root, "rowan");
  writeRecord(dir, "baton.json", { stepIndex: 0 }, { maxBytes: 200 });
  const before = usage(dir);
  refuses("memory-cap", () =>
    writeRecord(dir, "jobs/big.json", "x".repeat(500), { maxBytes: 200 })
  );
  assert.deepEqual(usage(dir), before);
  assert.equal(fs.existsSync(path.join(dir, "jobs", "big.json")), false);
});

test("only the three allowed records can be written", () => {
  const dir = memoryDir(tmp(), "rowan");
  refuses("memory-record", () => writeRecord(dir, "secrets.txt", "nope"));
  refuses("memory-record", () => writeRecord(dir, "jobs", "not a file"));
  writeRecord(dir, "jobs/42.job.json", { id: 42 });
  assert.equal(fs.existsSync(path.join(dir, "jobs", "42.job.json")), true);
});

test("paths cannot escape the agent directory", () => {
  const dir = memoryDir(tmp(), "rowan");
  refuses("memory-path", () => writeRecord(dir, "../rowan2/ledger.jsonl", "x"));
  refuses("memory-path", () => writeRecord(dir, "/etc/passwd", "x"));
  refuses("memory-path", () => writeRecord(dir, "jobs/../../out.json", "x"));
  assert.equal(fs.existsSync(path.join(path.dirname(dir), "rowan2")), false);
});

test("the ledger only ever grows", () => {
  const dir = memoryDir(tmp(), "rowan");
  appendLedger(dir, { event: "spawn" }, { maxBytes: 4096 });
  appendLedger(dir, { event: "exit" }, { maxBytes: 4096 });
  const lines = fs.readFileSync(path.join(dir, "ledger.jsonl"), "utf8").trim().split("\n");
  assert.equal(lines.length, 2);
  assert.deepEqual(readLedger(dir).map((l) => l.event), ["spawn", "exit"]);
});

test("a ledger append over the cap is refused whole", () => {
  const dir = memoryDir(tmp(), "rowan");
  appendLedger(dir, { event: "spawn", pad: "x".repeat(100) }, { maxBytes: 160 });
  const before = usage(dir);
  refuses("memory-cap", () =>
    appendLedger(dir, { event: "exit", pad: "x".repeat(100) }, { maxBytes: 160 })
  );
  assert.deepEqual(usage(dir), before);
  assert.equal(readLedger(dir).length, 1);
});

test("a torn ledger line does not erase the records before it", () => {
  const dir = memoryDir(tmp(), "rowan");
  appendLedger(dir, { event: "spawn" });
  fs.appendFileSync(path.join(dir, "ledger.jsonl"), '{"event":"tor');
  assert.deepEqual(readLedger(dir).map((l) => l.event), ["spawn"]);
});

test("check reports an over-cap directory without touching it", () => {
  const dir = memoryDir(tmp(), "rowan");
  writeRecord(dir, "baton.json", "x".repeat(300), { maxBytes: 4096 });
  const result = check(dir, 100);
  assert.equal(result.ok, false);
  assert.equal(result.overBy, result.bytes - 100);
  assert.equal(fs.readFileSync(path.join(dir, "baton.json"), "utf8").length, 300);
});

test("check on a directory that does not exist is a report, not a crash", () => {
  const result = check(path.join(tmp(), "memory", "ghost"), 100);
  assert.deepEqual({ files: result.files, bytes: result.bytes, ok: result.ok }, { files: 0, bytes: 0, ok: true });
});
