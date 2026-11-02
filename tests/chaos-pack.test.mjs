// Round 11 finish — the chaos pack (285..293). Each test is named for the failure it injects.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { validatePackage, acceptPackage } from "../agents/queue.mjs";
import { rule, RULING_INCONCLUSIVE, RULING_AGREE } from "../agents/judge.mjs";
import { runSweep } from "../aegis/sweep.mjs";
import { createWatchman } from "../agents/watchman.mjs";
import { lessons, lessonsHealth, teach } from "../agents/lessons.mjs";
import { spawnAgent, Ledger } from "../agents/runtime.mjs";
import { elapsedMs, budgetRemainingMs } from "../agents/clock.mjs";
import { writeFileLoud, DiskFullError } from "../agents/safe-write.mjs";

const NODE = process.execPath;
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "chaos-"));

test("R11-285 a package with no picture is refused by name and never queued", () => {
  const dir = tmp();
  const v = validatePackage({ id: "p1", agent: "vision" });
  assert.equal(v.ok, false);
  assert.equal(v.errors[0].reason, "missing-picture");
  assert.match(v.errors[0].detail, /carries no picture/);
  const r = acceptPackage({ id: "p1", agent: "vision" }, { queueDir: dir });
  assert.equal(r.ok, false);
  assert.deepEqual(fs.readdirSync(dir), []);

  const ok = acceptPackage({ id: "p2", agent: "vision", picture: "data:image/png;base64,AA" }, { queueDir: dir });
  assert.equal(ok.ok, true);
  assert.ok(fs.existsSync(path.join(dir, "p2.package.json")));
});

test("R11-286 two contradictory readings are ruled inconclusive, never a coin flip", () => {
  const r = rule([{ source: "camera", value: 1 }, { source: "still", value: 9 }]);
  assert.equal(r.ruling, RULING_INCONCLUSIVE);
  assert.equal(r.reason, "contradictory-readings");
  assert.equal(r.gap, 8);
  assert.equal(rule([{ source: "a", value: 1 }, { source: "b", value: 1.05 }]).ruling, RULING_AGREE);
  assert.equal(rule([{ source: "a", value: 1 }]).reason, "fewer-than-two-readings");
  assert.equal(rule([{ source: "a", value: 1 }, { source: "b", value: "n/a" }]).reason, "unreadable-reading");
});

test("R11-287 a network cut mid-sweep keeps the checked count and says CUT", async () => {
  const dir = tmp();
  // 101 versioned references: the first batch succeeds, the second throws.
  let lock = "";
  for (let i = 0; i < 101; i++) {
    lock += '[[package]]\nname = "crate' + i + '"\nversion = "1.0.0"\nsource = "registry+https://github.com/rust-lang/crates.io-index"\n\n';
  }
  fs.writeFileSync(path.join(dir, "Cargo.lock"), lock);
  let calls = 0;
  const client = {
    callTool: async () => {
      calls += 1;
      if (calls === 2) throw new Error("ECONNRESET");
      return { text: "No known vulnerabilities found across 100 package(s)." };
    },
  };
  const r = await runSweep({ root: dir, outDir: path.join(dir, "out"), client, runId: "cut-1" });
  assert.equal(r.status, "cut");
  assert.equal(r.checked, 100);
  assert.equal(r.batches, 1);
  assert.match(r.reason, /batch 2/);
  const events = new Ledger(path.join(dir, "out", "runs.jsonl")).read().map((l) => l.event);
  assert.ok(events.includes("sweep-cut"));
  assert.ok(!events.includes("sweep-done"));
});

test("R11-288 a malformed job is refused and logged, never spawned", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", command: [NODE, "-e", ""], budget: {} }] }));
  const jobsDir = path.join(dir, "jobs");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  fs.writeFileSync(path.join(jobsDir, "bad.job.json"), '{"id":"bad","agent":');
  assert.equal((await w.pollOnce()).length, 0);
  const line = w.ledger.read().find((l) => l.event === "job-unreadable");
  assert.ok(line, "the refusal is in the ledger");
  assert.equal(line.file, "bad.job.json");
});

test("R11-289 two job files with the same id are claimed once, not spawned twice", async () => {
  const dir = tmp();
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({ agents: [{ name: "worker", command: [NODE, "-e", "setTimeout(()=>{},50)"], budget: {} }] }));
  const jobsDir = path.join(dir, "jobs");
  const w = createWatchman({ registryFile: registry, root: dir, jobsDir });
  fs.writeFileSync(path.join(jobsDir, "a.job.json"), JSON.stringify({ id: "same", agent: "worker", orders: "one" }));
  fs.writeFileSync(path.join(jobsDir, "b.job.json"), JSON.stringify({ id: "same", agent: "worker", orders: "two" }));
  const spawned = await w.pollOnce();
  assert.equal(spawned.length, 1);
  await spawned[0].handle.done;
});

test("R11-290 a corrupted lessons line is quarantined; the good lessons still brief the agent", async () => {
  const dir = tmp();
  teach(dir, "rowan", "check the tree, not the branch");
  fs.appendFileSync(path.join(dir, "lessons.jsonl"), '{"agent":"broken","text":\n');
  teach(dir, "milo", "boot logs before claims");
  assert.deepEqual(lessons(dir).map((l) => l.agent), ["rowan", "milo"]);
  assert.deepEqual(lessonsHealth(dir), { good: 2, torn: 1 });

  const h = spawnAgent({ name: "reader", command: [NODE, "-e", ""], budget: {} }, { root: dir });
  await h.done;
  const brief = JSON.parse(fs.readFileSync(path.join(h.runDir, "brief.json"), "utf8"));
  assert.equal(brief.sharedLessons.length, 2);
});

test("R11-291 a backwards clock yields zero elapsed and a clamped, non-negative budget", () => {
  const back = elapsedMs(2000, 1000);
  assert.equal(back.ms, 0);
  assert.equal(back.jumped, true);
  assert.equal(back.raw, -1000);
  assert.equal(elapsedMs(1000, 1500).ms, 500);

  assert.deepEqual(budgetRemainingMs({ capMs: 100, spentMs: 150 }), { remaining: 0, capped: true, overrun: true });
  assert.equal(budgetRemainingMs({ capMs: 100, spentMs: 40 }).remaining, 60);
  assert.equal(budgetRemainingMs({ capMs: null, spentMs: 40 }).remaining, Infinity);
  assert.equal(budgetRemainingMs({ capMs: 100, spentMs: -1 }).reason, "bad-spend");
});

test("R11-292 a short write is a loud failure and leaves no partial file", () => {
  const dir = tmp();
  const file = path.join(dir, "record.json");
  const unlinked = [];
  const fake = {
    mkdirSync() {},
    openSync: () => 7,
    closeSync() {},
    unlinkSync: (f) => { unlinked.push(f); },
    writeSync: (_fd, buf) => buf.length - 1,
  };
  assert.throws(() => writeFileLoud(file, "0123456789", { fsImpl: fake }), DiskFullError);
  assert.deepEqual(unlinked, [file]);

  const enospc = { ...fake, writeSync: () => { const e = new Error("no space"); e.code = "ENOSPC"; throw e; } };
  assert.throws(() => writeFileLoud(file, "x", { fsImpl: enospc }), /disk full/);

  // The real path writes the whole file.
  writeFileLoud(path.join(dir, "real.txt"), "complete");
  assert.equal(fs.readFileSync(path.join(dir, "real.txt"), "utf8"), "complete");
});

test("R11-293 the chaos pack is one suite over the agent layer, not a drill per repo", () => {
  // The check this test makes is structural on purpose: every drill above is in THIS file and
  // runs with the agent suite. Counting them here catches a drill that was written in prose and
  // never landed as a test.
  const self = fs.readFileSync(new URL(import.meta.url), "utf8");
  const drills = self.match(/test\("R11-2\d\d/g) || [];
  assert.equal(drills.length, 9);
});
