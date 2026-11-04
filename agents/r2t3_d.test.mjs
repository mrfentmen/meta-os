// R2-T3 lane, Section D tests: patrol record, watchman alert + dedupe,
// heartbeat, eval gate, cleanup, demo idempotency.
//
// Run from the worktree root:  node --test agents/r2t3_d.test.mjs
// Offline only: loopback board, local python3 stdlib, temp dirs.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { describe, test } from "node:test";

import { alertUnitFailure } from "./unit_alert.mjs";
import { beatDaily, heartbeatFile } from "./heartbeat.mjs";
import { cleanupStaleRuns } from "./cleanup.mjs";
import { runEval, gateVerdict } from "./eval.mjs";
import { runDemo } from "./demo.mjs";
import { notify } from "./notify.mjs";

const tmp = (p) => fs.mkdtempSync(path.join(os.tmpdir(), p));
const NODE = process.execPath;

describe("patrol files a record even when it finds nothing (task 64)", () => {
  test("empty camera list yields an idle status record", async () => {
    const out = await runEval({ resultsDir: tmp("r2t3d-eval-"), only: "patrol-empty-record" });
    assert.equal(out.passed, 1, JSON.stringify(out.tasks));
    assert.equal(out.tasks[0].id, "patrol-empty-record");
  });
});

describe("watchman unit alerts (tasks 65-66)", () => {
  test("alarm names the unit and the reason", async () => {
    const root = tmp("r2t3d-alert-");
    const rec = await alertUnitFailure({ root, unit: "oc2-trio", reason: "exit 1" });
    assert.equal(rec.severity, "alarm");
    assert.match(rec.title, /oc2-trio/);
    assert.match(rec.body, /exit 1/);
    assert.equal(rec.suppressed, false);
  });

  test("one failure rings once across a 10x repeat", async () => {
    const root = tmp("r2t3d-dedupe-");
    const recs = [];
    for (let i = 0; i < 10; i++) {
      recs.push(await notify({
        root, severity: "alarm", key: "unit:oc2-trio:failed",
        title: "Unit failed: oc2-trio", body: "unit oc2-trio failed: exit 1",
      }));
    }
    assert.equal(recs.filter((r) => !r.suppressed).length, 1);
    const lines = fs.readFileSync(path.join(root, "notices.jsonl"), "utf8").split("\n").filter(Boolean);
    assert.equal(lines.length, 10); // repeats are journaled, not rung
  });
});

describe("daily heartbeat (task 67)", () => {
  test("one line per UTC day, carrying commit + scheduler", () => {
    const dir = tmp("r2t3d-beat-");
    const day1 = Date.UTC(2026, 10, 3, 12);
    assert.equal(beatDaily({ dir, now: day1, commit: "c1" }).written, true);
    assert.equal(beatDaily({ dir, now: day1 + 1000, commit: "c1" }).written, false);
    assert.equal(beatDaily({ dir, now: day1 + 86400 * 1000, commit: "c2" }).written, true);
    const lines = fs.readFileSync(heartbeatFile(dir), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
    assert.equal(lines.length, 2);
    assert.equal(lines[0].scheduler, "oc2-eval.timer");
    assert.equal(lines[0].commit, "c1");
  });
});

describe("stale-run cleanup (task 79)", () => {
  test("backdated run abandoned, fresh and finished runs untouched", () => {
    const root = tmp("r2t3d-clean-");
    const now = Date.UTC(2026, 10, 4, 12);
    const mk = (id, startMs, withExit) => {
      const d = path.join(root, "runs", id);
      fs.mkdirSync(d, { recursive: true });
      fs.writeFileSync(path.join(d, "start.json"), JSON.stringify({ startedAt: new Date(startMs).toISOString() }));
      const lines = [{ ts: new Date(startMs).toISOString(), run: id, event: "spawn" }];
      if (withExit) lines.push({ ts: new Date(startMs + 1000).toISOString(), run: id, event: "exit", code: 0 });
      fs.writeFileSync(path.join(d, "ledger.jsonl"), lines.map((l) => JSON.stringify(l)).join("\n") + "\n");
    };
    mk("run-old", now - 2 * 86400 * 1000, false);
    mk("run-fresh", now - 3600 * 1000, false);
    mk("run-done", now - 3 * 86400 * 1000, true);
    const out = cleanupStaleRuns({ root, now });
    assert.deepEqual(out.marked.map((m) => m.run), ["run-old"]);
    assert.ok(fs.existsSync(path.join(root, "runs", "run-old", "abandoned.json")));
    assert.ok(!fs.existsSync(path.join(root, "runs", "run-fresh", "abandoned.json")));
    assert.ok(!fs.existsSync(path.join(root, "runs", "run-done", "abandoned.json")));
  });
});

describe("eval gate + exit codes (tasks 72, 74, 75)", () => {
  test("gate passes with no prior, passes on match, fails below last", () => {
    const dir = tmp("r2t3d-gate-");
    assert.equal(gateVerdict(dir, 0).applies, false);
    const ts = Date.now();
    fs.writeFileSync(path.join(dir, "eval-prior.json"),
      JSON.stringify({ runId: "eval-prior", ts, iso: new Date(ts).toISOString(), score: 1, passed: 12, total: 12, commit: "x", tasks: [] }));
    assert.equal(gateVerdict(dir, 1).ok, true);
    const bad = gateVerdict(dir, 0.5);
    assert.equal(bad.ok, true === false);
    assert.match(bad.reason, /REGRESSION/);
  });

  test("harness exits non-zero on task failure", () => {
    const r = spawnSync(NODE, ["agents/eval.mjs", "--only", "no-such-task",
      "--results-dir", tmp("r2t3d-exit-")], { encoding: "utf8" });
    assert.notEqual(r.status, 0);
  });

  test("gate trip exits 2 on a replayed lowered score", () => {
    const dir = tmp("r2t3d-gate2-");
    const ts = Date.now();
    fs.writeFileSync(path.join(dir, "eval-prior.json"),
      JSON.stringify({ runId: "eval-prior", ts, iso: new Date(ts).toISOString(), score: 1, passed: 12, total: 12, commit: "x", tasks: [] }));
    const tasks = JSON.parse(fs.readFileSync("agents/eval_tasks.json", "utf8"));
    tasks.tasks.push({ id: "bogus", name: "b", area: "?", artifact: "b.json", pass: "never" });
    const tf = path.join(dir, "tasks.json");
    fs.writeFileSync(tf, JSON.stringify(tasks));
    const r = spawnSync(NODE, ["agents/eval.mjs", "--gate", "--results-dir", dir, "--tasks", tf], { encoding: "utf8" });
    assert.equal(r.status, 2, r.stdout + r.stderr);
    assert.match(r.stdout, /REGRESSION/);
  });
});

describe("demo submits 3 jobs and is safe twice (tasks 76-78)", () => {
  test("second run reuses ids, adds no files, keeps receipts", async () => {
    const dataDir = path.join(tmp("r2t3d-demo-"), "demo");
    const first = await runDemo({ dataDir });
    assert.equal(first.ok, true);
    assert.equal(first.artifacts.length, 3);
    const before = first.artifacts.map((a) => fs.readFileSync(a.result, "utf8"));
    const second = await runDemo({ dataDir });
    assert.equal(second.ok, true);
    assert.deepEqual(second.artifacts.map((a) => a.id), first.artifacts.map((a) => a.id));
    const jobs = fs.readdirSync(path.join(dataDir, "jobs")).sort();
    assert.deepEqual(jobs, [
      "demo-r2t3-1.job.json", "demo-r2t3-1.result.json",
      "demo-r2t3-2.job.json", "demo-r2t3-2.result.json",
      "demo-r2t3-3.job.json", "demo-r2t3-3.result.json",
    ]);
    const after = second.artifacts.map((a) => fs.readFileSync(a.result, "utf8"));
    assert.deepEqual(after, before);
  });
});
