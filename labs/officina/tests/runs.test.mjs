// labs/officina/tests/runs.test.mjs — node:test, no dependencies.
// Validates runs.json against the recorded sources it claims to come from:
// job/field coverage, margin arithmetic, artifact files exist on disk,
// memory seqs match workshop-memory.jsonl, timings match the timing files.
// Run: node --test labs/officina/tests/runs.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "url";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..");
const builds = join(dir, "builds");
const runs = JSON.parse(readFileSync(join(dir, "runs.json"), "utf8"));
const memLines = readFileSync(join(dir, "workshop-memory.jsonl"), "utf8")
  .split("\n").filter(Boolean).map((l) => JSON.parse(l));
const memBySeq = Object.fromEntries(memLines.map((o) => [o.seq, o.entry]));

test("five jobs, none failed", () => {
  assert.equal(runs.job_count, 5);
  assert.equal(runs.jobs.length, 5);
  assert.equal(runs.failed_job_count, 0);
  assert.deepEqual(runs.failed_jobs, []);
});

test("required fields on every job", () => {
  for (const j of runs.jobs) {
    for (const f of ["id", "kind", "status", "agent", "started_utc", "duration_s",
      "result_r", "heldout_r", "target_r", "margin", "rounds", "params", "artifacts"]) {
      assert.ok(j[f] !== undefined && j[f] !== null, `${j.id} has ${f}`);
    }
    assert.ok(j.artifacts.length > 0, `${j.id} has artifacts`);
  }
});

test("margins equal target minus result", () => {
  for (const j of runs.jobs) {
    assert.ok(Math.abs(j.margin - (j.target_r - j.result_r)) < 1e-9, j.id);
  }
});

test("result R matches the source pack/brief on disk", () => {
  const b1 = JSON.parse(readFileSync(join(builds, "build-001/brief.json"), "utf8"));
  const b2 = JSON.parse(readFileSync(join(builds, "build-002/brief.json"), "utf8"));
  const byId = Object.fromEntries(runs.jobs.map((j) => [j.id, j]));
  assert.equal(byId["build-001"].result_r, b1.verification.fresh_r_th_c_per_w);
  assert.equal(byId["build-002"].result_r, b2.verification.fresh_r_th_c_per_w);
  assert.equal(byId["build-001"].heldout_r, b1.verification.heldout_r_th_c_per_w);
  assert.equal(byId["build-002"].heldout_r, b2.verification.heldout_r_th_c_per_w);
  for (const [id, file] of [["brief-a", "brief-a-pack.json"], ["brief-b", "brief-b-pack.json"], ["brief-c", "brief-c-pack.json"]]) {
    const p = JSON.parse(readFileSync(join(builds, file), "utf8"));
    assert.equal(byId[id].result_r, p.provenance.final_r_th_c_per_w, id);
  }
});

test("durations match the timing files within float tolerance", () => {
  const bt = JSON.parse(readFileSync(join(builds, "build-timings.json"), "utf8"));
  const gt = JSON.parse(readFileSync(join(builds, "gen-timings.json"), "utf8"));
  const byId = Object.fromEntries(runs.jobs.map((j) => [j.id, j]));
  const close = (a, b, id) => assert.ok(Math.abs(a - b) < 1e-9, `${id}: ${a} vs ${b}`);
  close(byId["build-001"].duration_s, bt["build-001"]["2a_s"] + bt["build-001"]["2b_s"] + bt["build-001"]["2c_s"], "build-001");
  close(byId["build-002"].duration_s, bt["build-002"]["2a_s"] + bt["build-002"]["2b_s"] + bt["build-002"]["2c_s"], "build-002");
  close(byId["brief-a"].duration_s, gt.a.note_s + gt.a.pack_s, "brief-a");
});

test("memory seqs match workshop-memory.jsonl entries", () => {
  const byId = Object.fromEntries(runs.jobs.map((j) => [j.id, j]));
  assert.equal(byId["build-001"].memory_seq, 4);
  assert.equal(byId["build-002"].memory_seq, 5);
  assert.equal(memBySeq[byId["build-001"].memory_seq].final_r_th_c_per_w, byId["build-001"].result_r);
  assert.equal(memBySeq[byId["build-002"].memory_seq].final_r_th_c_per_w, byId["build-002"].result_r);
});

test("every artifact path exists on disk", () => {
  for (const j of runs.jobs) {
    for (const a of j.artifacts) {
      assert.ok(existsSync(join(dir, a.path)), `${j.id}: ${a.path} exists`);
    }
  }
});

test("variant pass/fail is consistent with the bar", () => {
  for (const j of runs.jobs.filter((j) => j.variants)) {
    for (const v of j.variants) {
      if (v.r_th_c_per_w != null) {
        assert.equal(v.pass_bar, v.r_th_c_per_w <= 2.0, `${j.id} round ${v.round}`);
        assert.ok(Math.abs(v.margin_vs_bar - (2.0 - v.r_th_c_per_w)) < 1e-9, `${j.id} round ${v.round} margin`);
      }
      if (v.heldout_r != null) {
        assert.equal(v.heldout_pass, v.heldout_r <= 2.0, `${j.id} round ${v.round} held-out`);
      }
    }
    assert.ok(j.variants.some((v) => v.pass_bar === true), `${j.id} shows its pass`);
  }
  const b1 = runs.jobs.find((j) => j.id === "build-001");
  assert.ok(b1.variants.some((v) => v.pass_bar === false), "build-001 shows its design misses");
  const b2 = runs.jobs.find((j) => j.id === "build-002");
  assert.ok(b2.variants.some((v) => v.heldout_pass === false), "build-002 shows its held-out miss");
});

test("misses all carry positive measured gaps", () => {
  const measured = runs.misses.filter((m) => m.gap != null);
  assert.ok(measured.length > 0);
  for (const m of measured) assert.ok(m.gap > 0, `${m.job} ${m.where}`);
});

test("agent attribution names the registry entry running the same program", () => {
  const reg = JSON.parse(readFileSync(join(dir, "..", "..", "agents/registry.json"), "utf8"));
  const faber = reg.agents.find((a) => a.name === "officina-faber");
  assert.ok(faber, "officina-faber in registry");
  assert.ok(faber.command.join(" ").includes("design_loop.py"), "registry command is design_loop.py");
  for (const j of runs.jobs) assert.equal(j.agent, "officina-faber");
});
