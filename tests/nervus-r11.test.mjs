// Round 11 finish — Nervus: inspector (262), layer map (263), planner (264), dose/probe
// contracts (265/266), tray (267), stub sweep/steer/ablate (268/269), signed delta (270).
// Every record here is STUB; no model is loaded and nothing is evidence about one.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { inspectModel, InspectError } from "../nervus/inspect.mjs";
import { buildLayerMap, validateLayerMap } from "../nervus/layermap.mjs";
import { planReduction, validatePlan } from "../nervus/planner.mjs";
import { signedDelta, renderDelta } from "../nervus/delta.mjs";
import { validateRecord, validateTray } from "../nervus/contracts.mjs";
import { runAndFile } from "../nervus/stub-runner.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "nervus-r11-"));

function fixtureModel() {
  const dir = tmp();
  fs.writeFileSync(path.join(dir, "config.json"), JSON.stringify({
    architectures: ["LlamaForCausalLM"], num_hidden_layers: 4, hidden_size: 32,
  }));
  fs.writeFileSync(path.join(dir, "model-00001.safetensors"), Buffer.alloc(100, 1));
  fs.writeFileSync(path.join(dir, "model-00002.safetensors"), Buffer.alloc(200, 2));
  fs.writeFileSync(path.join(dir, "README.md"), "not a weight");
  return dir;
}

test("R11-262 the inspector reports what is on disk, and refuses a directory with no config", () => {
  const i = inspectModel(fixtureModel());
  assert.equal(i.architecture, "LlamaForCausalLM");
  assert.equal(i.layer_count, 4);
  assert.equal(i.total_bytes, 300);
  assert.equal(i.files.length, 2, "README is not a weight");
  assert.match(i.inspection_hash, /^[0-9a-f]{16}$/);
  assert.throws(() => inspectModel(tmp()), InspectError);
});

test("R11-263 the layer map is drawable, ordered, and says when it is shape-only", () => {
  const i = inspectModel(fixtureModel());
  const map = buildLayerMap(i, { perLayer: [10, 20, 30, 40] });
  assert.deepEqual(validateLayerMap(map), []);
  assert.equal(map.layers.length, 4);
  assert.deepEqual(map.layers.map((l) => l.index), [0, 1, 2, 3]);
  assert.equal(map.completeness, "per-layer sizes supplied by caller");

  const shape = buildLayerMap(i);
  assert.equal(shape.layers[0].bytes, null);
  assert.match(shape.completeness, /shape-only/);
  assert.throws(() => buildLayerMap(i, { perLayer: [1, 2] }), /exactly 4/);
  assert.ok(validateLayerMap({ ...map, layers: [] }).length > 0);
});

test("R11-264 the planner proposes cuts and names the proof every cut would need", () => {
  const map = buildLayerMap(inspectModel(fixtureModel()));
  const plan = planReduction(map, { keepLayers: 2 });
  assert.deepEqual(validatePlan(plan), []);
  assert.equal(plan.cuts.length, 2);
  assert.deepEqual(plan.cuts[0].removes, [3]);
  assert.deepEqual(plan.cuts[1].removes, [2, 3]);
  for (const c of plan.cuts) {
    assert.equal(c.status, "proposed");
    assert.ok(c.proof_required.some((p) => /before_hash/.test(p)));
    assert.ok(c.proof_required.some((p) => /probe/.test(p)));
    assert.equal(c.after.model_hash, null, "a proposal does not invent the after hash");
  }
  assert.match(plan.note, /proposals only/);
  assert.throws(() => planReduction(map, { keepLayers: 4 }), /between/);
});

test("R11-265/266 a steer outside its window is refused, and an effect with no probe is refused", () => {
  const windows = {
    source: "test fixture only (not the repo's numbers)",
    zones: { inert: { min: 0, max: 0.2 }, persona: { min: 0.2, max: 1 }, collapse: { min: 1, max: 10 } },
  };
  const base = { model_hash: "a".repeat(64), operation: "steer", layer: 1, neuron: 2, dose: 0.1, zone: "inert", probe: "p", result: {} };
  assert.deepEqual(validateRecord({ ...base, dose: 0.1 }, { doseWindows: windows }), []);
  assert.ok(validateRecord({ ...base, dose: 2 }, { doseWindows: windows }).some((e) => /outside the inert window/.test(e)));
  const noProbe = { ...base, dose: 0.1 };
  delete noProbe.probe;
  assert.ok(validateRecord(noProbe).some((e) => /probe required/.test(e)));
  assert.ok(validateRecord({ ...base, steered: true }).length === 0, "extra fields are not a refusal");
});

test("R11-267 the tray check still holds against the real gateway list", () => {
  const root = path.resolve(import.meta.dirname, "..");
  const tray = JSON.parse(fs.readFileSync(path.join(root, "nervus", "tray.json"), "utf8"));
  const backends = JSON.parse(fs.readFileSync(path.join(root, "mcp-gateway", "backends.json"), "utf8"));
  assert.equal(validateTray(tray, backends).ok, true);
  assert.equal(validateTray({ tools: [{ tool: "ghost", prefix: "ghost" }] }, backends).ok, false);
});

test("R11-268/269/270 every stub operation files a valid record, marked STUB", () => {
  const dir = tmp();
  const ledger = path.join(dir, "stub.jsonl");
  for (const op of ["sweep", "steer", "ablate", "evaluate_delta"]) {
    const r = runAndFile({ operation: op, params: {}, ledgerFile: ledger });
    assert.equal(r.ok, true, op + ": " + r.errors.join("; "));
    assert.equal(r.record.result.source, "STUB");
  }
  const rows = fs.readFileSync(ledger, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(rows.length, 4);
  assert.ok(rows.every((r) => r.stub === true));
});

test("R11-270 a delta is signed, relative, and cannot be rendered as an absolute", () => {
  const d = signedDelta(10, 8);
  assert.equal(d.delta, -2);
  assert.equal(d.sign, "negative");
  assert.equal(d.direction, "decrease");
  assert.equal(d.relative, -0.2);

  const good = renderDelta({
    before_hash: "b".repeat(64), after_hash: "c".repeat(64), probe: "probe-7",
    reading: { before: 10, after: 8 }, summary: "the reading moved",
  });
  assert.equal(good.ok, true);
  assert.match(good.text, /probe-7: 10 -> 8 \(delta -2, decrease\)/);

  assert.equal(renderDelta({ before_hash: "b".repeat(64), after_hash: "c".repeat(64), probe: "p", reading: { before: 1, after: 2 }, summary: "this is better" }).reason, "absolute-claim");
  assert.equal(renderDelta({ probe: "p", reading: { before: 1, after: 2 } }).reason, "no-before-after-hash");
  assert.equal(renderDelta({ before_hash: "b".repeat(64), after_hash: "c".repeat(64), reading: { before: 1, after: 2 } }).reason, "no-probe");
});
