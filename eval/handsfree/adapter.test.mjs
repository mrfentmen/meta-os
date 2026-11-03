// Hands-Free eval adapter tests (first slice).
//
//   node --test eval/handsfree/adapter.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { createHash } from "node:crypto";
import { assessHandsfree, runHandsfreeEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(HERE));
const WORK = path.join(ROOT, "os-build", "handsfree");

const scenarios = JSON.parse(fs.readFileSync(path.join(HERE, "scenarios.json"), "utf8")).scenarios;

function snapshot(dir) {
  if (!fs.existsSync(dir)) return null;
  const out = {};
  const walk = (d) => {
    for (const f of fs.readdirSync(d).sort()) {
      const p = path.join(d, f);
      const st = fs.statSync(p);
      if (st.isDirectory()) walk(p);
      else out[path.relative(dir, p)] = createHash("sha256").update(fs.readFileSync(p)).digest("hex");
    }
  };
  walk(dir);
  return out;
}

test("every scenario passes against the real modules", () => {
  const records = runHandsfreeEval(scenarios, (s) => assessHandsfree(s, ROOT), ROOT);
  assert.equal(records.length, 13);
  for (const r of records) {
    assert.equal(r.pass, true, r.id + " failed: " + r.evidence);
  }
});

test("scenario ids are unique and each carries an expectation", () => {
  const ids = scenarios.map((s) => s.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const s of scenarios) {
    assert.ok(s.title && s.expects, s.id + " needs a title and an expectation");
  }
});

test("baseline passes exactly the two empty rows", () => {
  const records = runHandsfreeEval(scenarios, assessBaseline, ROOT);
  const passed = records.filter((r) => r.pass).map((r) => r.id).sort();
  assert.deepEqual(passed, ["HF-BRIEF-EMPTY-01", "HF-INTAKE-EMPTY-01"]);
  assert.equal(passed.length, 2);
});

test("a real run never touches the committed os-build/handsfree workspace", () => {
  const before = snapshot(WORK);
  const records = runHandsfreeEval(scenarios, (s) => assessHandsfree(s, ROOT), ROOT);
  assert.ok(records.every((r) => r.pass), "real run must pass for the guard to mean anything");
  assert.deepEqual(snapshot(WORK), before);
});

test("unknown scenario ids fail instead of passing silently", () => {
  const r = assessHandsfree({ id: "HF-NOPE-01", title: "not a scenario" }, ROOT);
  assert.equal(r.pass, false);
  assert.match(r.evidence, /no checker/);
});
