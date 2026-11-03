// Tests for the Meta Custos eval adapter (first slice).
// Run: node --test eval/custos/adapter.test.mjs
// The full-eval test runs the real patrol code in tmp dirs only; the
// tmp-only guard proves os/worlds/custos/runs/ is byte-identical
// before and after, so the harness never rewrites the committed
// patrol record it scores against.

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { assessCustos, runCustosEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(path.dirname(here));
const scenarios = JSON.parse(fs.readFileSync(path.join(here, "scenarios.json"), "utf8")).scenarios;

function snapshotRuns() {
  const dir = path.join(root, "os", "worlds", "custos", "runs");
  const out = {};
  for (const name of fs.readdirSync(dir).sort()) {
    out[name] = fs.readFileSync(path.join(dir, name));
  }
  return out;
}

function sameSnapshot(a, b) {
  const keysA = Object.keys(a).sort();
  const keysB = Object.keys(b).sort();
  if (JSON.stringify(keysA) !== JSON.stringify(keysB)) return false;
  return keysA.every((k) => a[k].equals(b[k]));
}

test("scenario ids are unique and every scenario has a checker", () => {
  const ids = scenarios.map((s) => s.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const s of scenarios) {
    const r = assessCustos(s);
    assert.notEqual(r.evidence, "no checker for scenario " + s.id, s.id);
  }
});

test("every scenario cites committed material, never an invented input", () => {
  const markers = ["PACK.md", "tests/custos", "patrol.py", "runs/", "validate_pack.py", "pack.json", "hosts.example"];
  for (const s of scenarios) {
    assert.ok(markers.some((m) => s.source.includes(m)), s.id + " source: " + s.source);
  }
});

test("baseline passes exactly the empty-outcome scenario", () => {
  const results = scenarios.map((s) => assessBaseline(s));
  const passed = scenarios.filter((s, i) => results[i].pass).map((s) => s.id);
  assert.deepEqual(passed, ["CU-EMPTY-01"]);
});

test("real run passes every scenario and leaves runs/ byte-identical", () => {
  const before = snapshotRuns();
  const records = runCustosEval(scenarios, assessCustos);
  const failed = records.filter((r) => !r.pass);
  assert.deepEqual(failed, [], JSON.stringify(failed, null, 2));
  assert.equal(records.length, scenarios.length);
  assert.ok(sameSnapshot(before, snapshotRuns()), "runs/ changed during the eval run");
});

test("unknown scenario reports no checker instead of passing", () => {
  const r = assessCustos({ id: "CU-NOPE-01", title: "not a scenario" });
  assert.equal(r.pass, false);
  assert.match(r.evidence, /no checker/);
});
