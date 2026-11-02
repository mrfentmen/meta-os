// Round 12, Sections B/C/D — the records this lane must keep true.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const R12 = path.join(ROOT, "os-build", "layer1", "r12");
const readJson = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const readText = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");

test("R12-019 the Aegis cycle is a registry entry and its receipt names every stage", () => {
  const agents = readJson("agents/registry.json").agents;
  const cycle = agents.find((a) => a.name === "aegis-cycle");
  assert.ok(cycle, "aegis-cycle is registered");
  assert.equal(cycle.hosted, true);
  assert.deepEqual(cycle.command, ["repo:node", "aegis/cycle.mjs"]);
  assert.ok(fs.existsSync(path.join(ROOT, "aegis", "cycle.mjs")));
  assert.match(readText("os-build/layer1/r12/CHAOS_COVERAGE.md"), /`aegis-cycle`/);
  const receipt = readJson("os-build/layer1/r12/AEGIS_CYCLE.json");
  assert.equal(receipt.ok, true);
  for (const stage of ["sweep", "kev", "ledger"]) assert.equal(receipt.stages[stage].state, "ran", stage);
  assert.equal(receipt.stages.sweep.manifests, 23);
  assert.equal(receipt.stages.sweep.queried, 108);
});

test("R12-015 history scan reports counts and a range, never values", () => {
  const r = readJson("os-build/aegis/HISTORY_SCAN.json");
  assert.equal(r.commits, 1881);
  assert.equal(r.range.first.date, "2026-11-02");
  assert.equal(r.range.last.date, "2026-10-28");
  assert.ok(r.totalCategoryHits >= 0);
  assert.ok(r.categories["private-key"]);
  assert.equal(typeof r.categories["github-token"]["2026"], "number");
});

test("R12-016 zero sweep findings still write an append-only batch receipt", () => {
  const ledger = readText("os-build/aegis/findings-ledger.jsonl").trim().split("\n").map(JSON.parse);
  const batches = ledger.filter((r) => r.kind === "batch");
  assert.ok(batches.length >= 1);
  for (const b of batches) assert.equal(typeof b.sweepFindings, "number");
});

test("R12-017 no watch target is left UNVERIFIED; unreachable is not dead", () => {
  const doc = readJson("aegis/watch-targets.json");
  assert.equal(doc.targets.length, 169);
  for (const t of doc.targets) {
    assert.ok(["LIVE", "DEAD", "UNREACHABLE"].includes(t.liveness), t.id + " " + t.liveness);
    assert.ok(t.livenessCheckedAt, t.id + " checked date");
  }
  const unreachable = doc.targets.filter((t) => t.liveness === "UNREACHABLE");
  assert.equal(unreachable.length, 1);
  assert.equal(unreachable[0].ref, "clipraiders.com");
});

test("R12-018 OPSEC checklist has no silent pass for screenshots", () => {
  const md = readText("os-build/aegis/OPSEC_R12.md");
  assert.match(md, /\| checks failed \| 0 \|/);
  assert.match(md, /UNCHECKED/);
  assert.match(md, /no OCR/i);
});

test("R12-020 clean input stays clean", () => {
  const r = readJson("os-build/layer1/r12/FALSE_POSITIVE_DRILL.json");
  assert.equal(r.ok, true);
  assert.equal(r.findings, 0);
  assert.equal(r.checked, 3);
});

test("R12-021/022/025 baton proofs: one artifact course, one continuation, one alarm", () => {
  const cadence = readJson("os-build/layer1/r12/BATON_PROOF.json");
  assert.equal(cadence.ok, true);
  assert.equal(cadence.artifacts.stageOne, 1);
  assert.equal(cadence.artifacts.continuation, 1);
  assert.equal(cadence.recovery.orphanedRecords, 1);
  assert.equal(cadence.recovery.batonPassRecords, 1);
  assert.ok(cadence.recovery.restartToResultMs >= 0);
  assert.ok(cadence.recovery.alarm.line);
  const imperium = readJson("os-build/layer1/r12/IMPERIUM_BATON.json");
  assert.equal(imperium.ok, true);
  assert.equal(imperium.dispatchesInRunDir, 1);
});

test("R12-023/024 every hosted loop has a STOP outcome and the budget cap is enforced", () => {
  const r = readJson("os-build/layer1/r12/LOOPS_DRILL.json");
  assert.equal(r.ok, true);
  assert.equal(r.loops.length, 8);
  for (const loop of r.loops) {
    assert.ok(["stopped-mid-run", "finished-before-stop"].includes(loop.state), loop.agent);
    assert.equal(loop.noOrphan, true, loop.agent);
  }
  assert.equal(r.budget.ok, true);
  assert.equal(r.budget.receipt.reason, "budget-wall-clock");
  assert.equal(r.budget.receipt.capMs, 20);
  assert.equal(r.budget.registryBudgetUnchanged, 120000);
});

test("D restart is proven for the host-runnable services and the gap names the rest", () => {
  const r = readJson("os-build/layer1/r12/RESTART_PROOF.json");
  assert.equal(r.ok, true);
  const names = r.services.map((s) => s.service);
  assert.ok(names.includes("heartbeat"));
  assert.ok(names.includes("echo"));
  assert.ok(names.includes("mcp-host"));
  const gap = readText("os-build/layer1/r12/RESTART_GAP.md");
  assert.match(gap, /35/);
  assert.match(gap, /mcp-host/);
  assert.match(gap, /svc_entry/);
});
