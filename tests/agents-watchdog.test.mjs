// Round 8, A3 — the heartbeat and the checker.
//
// The properties that matter: a missing or stale beat is an alarm, a fresh beat clears it, the
// alarm is raised ONCE (not on every check), and the CLI's exit code is usable from a shell.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { writeBeat, readBeat, checkBeat, alarmLine, DEFAULT_MAX_AGE_MS } from "../agents/watchdog.mjs";
import { createWatchman } from "../agents/watchman.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agents-watchdog-"));
const NODE = process.execPath;
const CLI = path.resolve("agents/watchdog.mjs");

test("A3.1 a missing heartbeat is an alarm, said once", () => {
  const dir = tmp();
  const f = path.join(dir, "beat.json");
  const first = checkBeat(f, { maxAgeMs: 1000 });
  assert.equal(first.state, "missing");
  assert.match(first.alarm, /^ALARM watchman heartbeat lost: /);
  const second = checkBeat(f, { maxAgeMs: 1000 });
  assert.equal(second.state, "still-dead");
  assert.equal(second.alarm, null, "the same death is not announced twice");
});

test("A3.2 a fresh beat is quiet, and clears a raised alarm", () => {
  const dir = tmp();
  const f = path.join(dir, "beat.json");
  assert.ok(checkBeat(f, { maxAgeMs: 1000 }).alarm);
  writeBeat(f, { now: Date.now() });
  const fresh = checkBeat(f, { maxAgeMs: 1000 });
  assert.equal(fresh.state, "fine");
  assert.equal(fresh.alarm, null);
  assert.equal(fresh.cleared, true);
  // A second outage alarms again: the marker was cleared by the healthy beat.
  const stale = checkBeat(f, { maxAgeMs: 1000, now: Date.now() + 60000 });
  assert.equal(stale.state, "dead");
  assert.match(stale.alarm, /^ALARM /);
});

test("A3.3 the age in the line is the age of the beat", () => {
  const dir = tmp();
  const f = path.join(dir, "beat.json");
  const t0 = 1_700_000_000_000;
  writeBeat(f, { now: t0 });
  const r = checkBeat(f, { maxAgeMs: 1000, now: t0 + 4200 });
  assert.equal(r.ageMs, 4200);
  assert.match(r.alarm, /last beat 4\.2s ago/);
  assert.match(r.alarm, /limit 1\.0s/);
  const line = alarmLine(4200, 1000, { iso: "2026-11-02T00:00:00.000Z" });
  assert.match(line, /last 2026-11-02T00:00:00\.000Z/);
});

test("A3.4 a beat is replaced atomically and carries pid + timestamp", () => {
  const dir = tmp();
  const f = path.join(dir, "beat.json");
  const b = writeBeat(f, { now: 1000 });
  assert.equal(b.ts, 1000);
  assert.equal(typeof b.pid, "number");
  assert.ok(!fs.existsSync(f + ".tmp"), "no half-written file is left behind");
  const r = readBeat(f, 2500);
  assert.equal(r.ageMs, 1500);
});

test("A3.5 a running watchman beats; a stopped one is caught by the CLI", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [] }));
  const beatFile = path.join(dir, "relay.beat.json");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir: path.join(dir, "jobs"), heartbeatFile: beatFile });
  assert.ok(fs.existsSync(beatFile), "a fresh watchman beats at start-up");
  const before = JSON.parse(fs.readFileSync(beatFile, "utf8")).ts;
  await new Promise((r) => setTimeout(r, 5));
  await w.pollOnce();
  const after = JSON.parse(fs.readFileSync(beatFile, "utf8")).ts;
  assert.ok(after >= before, "each poll refreshes the beat");

  // Fresh: exit 0, no output.
  const fresh = spawnSync(NODE, [CLI, "check", beatFile, "60000"], { encoding: "utf8" });
  assert.equal(fresh.status, 0);
  assert.equal(fresh.stdout, "");

  // Stopped: age the beat past the limit, then the checker must speak and exit 2.
  fs.writeFileSync(beatFile, JSON.stringify({ agent: "watchman", pid: 1, ts: Date.now() - 5000, iso: "2026-11-02T00:00:00.000Z" }));
  const dead = spawnSync(NODE, [CLI, "check", beatFile, "500"], { encoding: "utf8" });
  assert.equal(dead.status, 2);
  assert.match(dead.stdout, /^ALARM watchman heartbeat lost: /);
  const again = spawnSync(NODE, [CLI, "check", beatFile, "500"], { encoding: "utf8" });
  assert.equal(again.status, 2);
  assert.equal(again.stdout, "", "still dead, nothing new to say");
});

test("A3.6 the default limit is a real number of seconds", () => {
  assert.equal(DEFAULT_MAX_AGE_MS, 15000);
});
