// CB-071..080 — tooling scripts. Shell flags are exercised through bash;
// every Node tool is imported and tested on a temp fixture.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { spawnSync } from "node:child_process";

import { report as bootReport } from "../os-build/tools/boot_markers.mjs";
import { summarize } from "../os-build/tools/receipts_summary.mjs";
import { diffFailures } from "../os-build/tools/test_diff.mjs";
import { lintText, lintDir } from "../os-build/tools/records_lint.mjs";
import { buildManifest, verifyManifest } from "../os-build/tools/evidence_manifest.mjs";
import { sweep } from "../os-build/tools/fixture_sweep.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "metaos-tools-"));
const run = (cmd, args, opts = {}) => spawnSync(cmd, args, { encoding: "utf8", ...opts });

test("CB-071 light_gate --only runs one stage", () => {
  const r = run("bash", ["os-build/tools/light_gate.sh", "--only", "omissions"], { cwd: ROOT });
  assert.equal(r.status, 0, r.stderr || r.stdout);
  assert.match(r.stdout, /SKIP cargo/);
  assert.match(r.stdout, /--only omissions/);
  assert.doesNotMatch(r.stdout, /== clone ==/);
});

test("CB-072 a failing stage stops and names the stage", () => {
  const dir = tmp();
  try {
    const r = run("bash", ["os-build/tools/light_gate.sh", "--only", "docs"], {
      cwd: ROOT,
      env: { ...process.env, LIGHT_GATE_ROOT: dir },
    });
    assert.equal(r.status, 1, r.stdout + r.stderr);
    assert.match(r.stdout + r.stderr, /LIGHT GATE: FAIL — stage docs:/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("CB-073 parity_lane --dry-run prints the plan and compares nothing", () => {
  const r = run("bash", ["os-build/tools/parity_lane.sh", "--dry-run"], { cwd: ROOT });
  assert.equal(r.status, 0, r.stderr || r.stdout);
  assert.match(r.stdout, /DRY RUN/);
  assert.match(r.stdout, /would compare/);
  assert.match(r.stdout, /nothing compared/);
  assert.doesNotMatch(r.stdout, /^PASS/m);
});

test("CB-074 boot markers: the committed WAVE3 log is complete", () => {
  const serial = fs.readFileSync(path.join(ROOT, "os-build/logs/WAVE3-combined-serial.txt"), "utf8");
  const full = bootReport(serial);
  assert.equal(full.present, full.rows.length);
  assert.deepEqual(full.missing, []);

  const truncated = serial.split("\n").slice(0, 5).join("\n");
  const cut = bootReport(truncated);
  assert.ok(cut.missing.includes("HELLO FROM USERSPACE"));
});

test("CB-075 receipts summary totals by model and labels estimates", () => {
  const summary = summarize([
    { model: "a", usage: { total_tokens: 10 }, latency_ms: 100, est_cost_usd: null },
    { model: "a", usage: { total_tokens: 20 }, latency_ms: 300, est_cost_usd: null },
    { model: "b", usage: { total_tokens: 5 }, latency_ms: 50, est_cost_usd: 0.5 },
  ]);
  assert.equal(summary.totalReceipts, 3);
  assert.equal(summary.totalTokens, 35);
  assert.equal(summary.unpriced, 2);
  const a = summary.models.find((m) => m.model === "a");
  assert.equal(a.receipts, 2);
  assert.equal(a.avgLatencyMs, 200);
  assert.equal(a.unpriced, 2);
});

test("CB-076 branch tip reporter works in a scratch repo", () => {
  const dir = tmp();
  const env = {
    ...process.env,
    GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.com",
    GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.com",
  };
  try {
    assert.equal(run("git", ["init", "-q", "-b", "main"], { cwd: dir, env }).status, 0);
    fs.writeFileSync(path.join(dir, "a.txt"), "a\n");
    assert.equal(run("git", ["add", "."], { cwd: dir, env }).status, 0);
    assert.equal(run("git", ["commit", "-qm", "main"], { cwd: dir, env }).status, 0);
    assert.equal(run("git", ["checkout", "-qb", "feature"], { cwd: dir, env }).status, 0);
    fs.writeFileSync(path.join(dir, "b.txt"), "b\n");
    assert.equal(run("git", ["add", "."], { cwd: dir, env }).status, 0);
    assert.equal(run("git", ["commit", "-qm", "feature"], { cwd: dir, env }).status, 0);

    const r = run("bash", [path.join(ROOT, "os-build/tools/branch_tip.sh"), dir], { env });
    assert.equal(r.status, 0, r.stderr || r.stdout);
    assert.match(r.stdout, /branch: feature/);
    assert.match(r.stdout, /tip: [0-9a-f]{40}/);
    assert.match(r.stdout, /b\.txt/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("CB-077 test diff names added and removed failures", () => {
  const diff = diffFailures("not ok 1 - a\nnot ok 2 - b\n", "not ok 1 - a\nnot ok 2 - c\n");
  assert.deepEqual(diff.added, ["c"]);
  assert.deepEqual(diff.removed, ["b"]);
});

test("CB-078 records lint accepts a complete header and names a missing field", () => {
  assert.deepEqual(lintText("# Record\n\nDate: 2026-11-02\nScope: test\nbody\n"), []);
  const bad = lintText("# Record\n\nbody only\n");
  assert.ok(bad.some((e) => e.startsWith("date:")));
  assert.ok(bad.some((e) => e.startsWith("scope:")));
  const rows = lintDir(path.join(ROOT, "os-build/records"));
  assert.ok(rows.length > 0);
  const r = run(process.execPath, ["os-build/tools/records_lint.mjs"], { cwd: ROOT });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /report only/);
});

test("CB-079 manifest writes and verifies sha256, then detects a change", () => {
  const dir = tmp();
  try {
    fs.writeFileSync(path.join(dir, "a.txt"), "alpha\n");
    fs.mkdirSync(path.join(dir, "nested"));
    fs.writeFileSync(path.join(dir, "nested", "b.txt"), "beta\n");
    const manifest = buildManifest(dir);
    assert.equal(manifest.files.length, 2);
    assert.equal(verifyManifest(manifest).ok, true);
    fs.writeFileSync(path.join(dir, "a.txt"), "changed\n");
    const after = verifyManifest(manifest);
    assert.equal(after.ok, false);
    assert.deepEqual(after.changed, ["a.txt"]);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("CB-080 sweep lists unreferenced fixtures and TODO lines", () => {
  const dir = tmp();
  try {
    fs.writeFileSync(path.join(dir, "fixture.json"), "{}\n");
    fs.writeFileSync(path.join(dir, "used.test.mjs"), "// reads fixture.json\n");
    fs.writeFileSync(path.join(dir, "orphan.bin"), "x\n");
    fs.writeFileSync(path.join(dir, "todo.test.mjs"), "// TODO: remove me\n");
    const result = sweep(dir);
    assert.ok(result.orphans.includes("orphan.bin"));
    assert.ok(!result.orphans.includes("fixture.json"));
    assert.equal(result.todos.length, 1);
    assert.equal(result.todos[0].file, "todo.test.mjs");
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
