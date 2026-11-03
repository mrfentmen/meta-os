// Section N — a dead watchman now has a recovery, not only an alarm (R13-374).
//
// The drills found detection without repair: every restart was a hand respawn. These cases
// hold the recovery: one restart per outage, a budget, a record for every attempt.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { writeBeat, recoverOnce, restartBudget } from "../agents/watchdog.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "wd-rec-"));

function recorder() {
  const calls = [];
  const spawn = (cmd, args, opts) => {
    calls.push({ cmd, args, opts });
    return { pid: 4242, unref() {}, on() {} };
  };
  return { calls, spawn };
}

test("N.1 a dead heartbeat is restarted once, and the attempt is on disk", () => {
  const dir = tmp();
  const beat = path.join(dir, "watchman.heartbeat.json");
  const log = path.join(dir, "restarts.jsonl");
  writeBeat(beat, { now: Date.now() - 60_000 });
  const { calls, spawn } = recorder();
  const r = recoverOnce({
    heartbeatFile: beat, maxAgeMs: 500, logFile: log,
    command: ["node", "watchman.mjs"], spawn,
  });
  assert.equal(r.restarted, true);
  assert.equal(r.pid, 4242);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].args, ["watchman.mjs"]);
  const rec = JSON.parse(fs.readFileSync(log, "utf8").trim());
  assert.equal(rec.ok, true);
  assert.equal(rec.cause, "dead");
});

test("N.2 a live watchman is left alone", () => {
  const dir = tmp();
  const beat = path.join(dir, "h.json");
  writeBeat(beat, { now: Date.now() });
  const { calls, spawn } = recorder();
  const r = recoverOnce({
    heartbeatFile: beat, maxAgeMs: 15_000, logFile: path.join(dir, "r.jsonl"),
    command: ["node", "x"], spawn,
  });
  assert.equal(r.restarted, false);
  assert.equal(r.reason, "alive");
  assert.equal(calls.length, 0);
});

test("N.3 one outage gets one restart: a raised alarm is not restarted again", () => {
  const dir = tmp();
  const beat = path.join(dir, "h.json");
  const log = path.join(dir, "r.jsonl");
  writeBeat(beat, { now: Date.now() - 60_000 });
  const { calls, spawn } = recorder();
  const first = recoverOnce({ heartbeatFile: beat, maxAgeMs: 500, logFile: log, command: ["node", "x"], spawn });
  const second = recoverOnce({ heartbeatFile: beat, maxAgeMs: 500, logFile: log, command: ["node", "x"], spawn });
  assert.equal(first.restarted, true);
  assert.equal(second.restarted, false);
  assert.equal(second.reason, "already-alarmed");
  assert.equal(calls.length, 1);
});

test("N.4 the budget stops a flapping watchman and names it", () => {
  const dir = tmp();
  const beat = path.join(dir, "h.json");
  const log = path.join(dir, "r.jsonl");
  const now = Date.now();
  writeBeat(beat, { now: now - 60_000 });
  for (let i = 0; i < 3; i += 1) {
    fs.appendFileSync(log, JSON.stringify({ ts: now, ok: true, pid: 1 }) + "\n");
  }
  const { calls, spawn } = recorder();
  const r = recoverOnce({
    heartbeatFile: beat, maxAgeMs: 500, now, logFile: log,
    command: ["node", "x"], spawn, maxRestarts: 3, windowMs: 100_000,
  });
  assert.equal(r.restarted, false);
  assert.equal(r.reason, "budget-spent");
  assert.equal(calls.length, 0);
  assert.equal(restartBudget(log, { now, windowMs: 100_000, maxRestarts: 3 }).left, 0);
});

test("N.5 a failed spawn is recorded instead of thrown out of the loop", () => {
  const dir = tmp();
  const beat = path.join(dir, "h.json");
  const log = path.join(dir, "r.jsonl");
  writeBeat(beat, { now: Date.now() - 60_000 });
  const spawn = () => { throw new Error("ENOENT spawn node"); };
  const r = recoverOnce({ heartbeatFile: beat, maxAgeMs: 500, logFile: log, command: ["node", "x"], spawn });
  assert.equal(r.restarted, false);
  assert.equal(r.reason, "spawn-failed");
  const rec = JSON.parse(fs.readFileSync(log, "utf8").trim());
  assert.equal(rec.ok, false);
  assert.match(rec.error, /ENOENT/);
});
