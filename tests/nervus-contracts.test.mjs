// Meta Nervus — contract tests (C1/C3). A stub runner, a stub model, and the two rules the
// spec calls non-negotiable. No model is loaded; nothing here is evidence about one.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { validateRecord, validateTray, OPERATIONS, DOSE_ZONES } from "../nervus/contracts.mjs";
import { runStub, runAndFile } from "../nervus/stub-runner.mjs";

const HASH = "a".repeat(64);

test("N1 every operation has a minimal record that validates", () => {
  const minimal = {
    map_layers: { model_hash: HASH, operation: "map_layers", result: { layers: 12 } },
    sweep: { model_hash: HASH, operation: "sweep", layer_from: 0, layer_to: 2, result: { neurons: 3 } },
    steer: { model_hash: HASH, operation: "steer", layer: 1, neuron: 7, dose: 0.5, zone: "inert", probe: "p", result: { changed: true } },
    ablate: { model_hash: HASH, operation: "ablate", layer: 1, neuron: 7, probe: "p", result: {} },
    evaluate_delta: { model_hash: HASH, operation: "evaluate_delta", before_hash: "b".repeat(64), after_hash: "c".repeat(64), probe: "p", result: { delta: 0 } },
  };
  for (const [op, rec] of Object.entries(minimal)) {
    assert.deepEqual(validateRecord(rec), [], op);
    assert.ok(OPERATIONS[op], op + " is declared");
  }
});

test("N2 probe dependence: an effect without its probe is refused, a sweep is not", () => {
  const steer = { model_hash: HASH, operation: "steer", layer: 1, neuron: 1, dose: 1, zone: "inert", result: {} };
  assert.ok(validateRecord(steer).some((e) => /probe required/.test(e)));
  const ablate = { model_hash: HASH, operation: "ablate", layer: 1, neuron: 1, result: {} };
  assert.ok(validateRecord(ablate).some((e) => /probe required/.test(e)));
  const sweep = { model_hash: HASH, operation: "sweep", layer_from: 0, layer_to: 1, result: {} };
  assert.deepEqual(validateRecord(sweep), []);
});

test("N3 a steer must name one of the three dose windows", () => {
  const base = { model_hash: HASH, operation: "steer", layer: 1, neuron: 2, dose: 1, probe: "p", result: {} };
  assert.deepEqual(validateRecord({ ...base, zone: "inert" }), []);
  assert.deepEqual(validateRecord({ ...base, zone: "persona" }), []);
  assert.deepEqual(validateRecord({ ...base, zone: "collapse" }), []);
  const bad = validateRecord({ ...base, zone: "a little" });
  assert.ok(bad.some((e) => /zone must be one of/.test(e)));
  assert.deepEqual(DOSE_ZONES, ["inert", "persona", "collapse"]);
});

test("N4 when windows are loaded, the zone claim must match the numbers", () => {
  const windows = { source: "neuron-surgery@abc123 levels.json", zones: { inert: { min: 0, max: 0.2 }, persona: { min: 0.2, max: 1 }, collapse: { min: 1, max: 10 } } };
  const rec = (dose, zone) => ({ model_hash: HASH, operation: "steer", layer: 1, neuron: 2, dose, zone, probe: "p", result: {} });
  assert.deepEqual(validateRecord(rec(0.1, "inert"), { doseWindows: windows }), []);
  assert.ok(validateRecord(rec(0.5, "inert"), { doseWindows: windows }).some((e) => /outside the inert window/.test(e)));
  const unsourced = { source: null, zones: windows.zones };
  assert.ok(validateRecord(rec(0.1, "inert"), { doseWindows: unsourced }).some((e) => /no named source/.test(e)));
});

test("N5 the subspace correction: a low-dimensional effect cannot be filed as a neuron", () => {
  const base = { model_hash: HASH, operation: "steer", layer: 1, neuron: 3, dose: 1, zone: "persona", probe: "p", result: {} };
  assert.ok(validateRecord({ ...base, scope: "subspace", subspace_dim: 4 }).some((e) => /must not name a single neuron/.test(e)));
  assert.ok(validateRecord({ ...base, scope: "subspace" }).some((e) => /subspace_dim/.test(e)));
  // A subspace record legitimately has no neuron, so the neuron requirement is waived for it.
  const noNeuron = { model_hash: HASH, operation: "steer", layer: 1, dose: 1, zone: "persona", probe: "p", result: {} };
  assert.deepEqual(validateRecord({ ...noNeuron, scope: "subspace", subspace_dim: 4 }), []);
  assert.ok(validateRecord(noNeuron).some((e) => /neuron required/.test(e)), "a plain steer still needs its neuron");
});

test("N6 a model hash is a hash, not a path", () => {
  const rec = { model_hash: "/Users/someone/models/granite", operation: "map_layers", result: {} };
  assert.ok(validateRecord(rec).some((e) => /must be 8-64 hex/.test(e)));
});

test("N7 evaluate_delta without both receipts is refused", () => {
  const rec = { model_hash: HASH, operation: "evaluate_delta", before_hash: "b".repeat(64), probe: "p", result: {} };
  assert.ok(validateRecord(rec).some((e) => /after_hash required/.test(e)));
});

test("N8 the stub runner emits a valid record for every operation and marks it a stub", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "nervus-"));
  const ledger = path.join(dir, "ledger.jsonl");
  for (const op of Object.keys(OPERATIONS)) {
    const r = runAndFile({ operation: op, params: {}, ledgerFile: ledger });
    assert.equal(r.ok, true, op + ": " + r.errors.join("; "));
    assert.equal(r.record.result.source, "STUB");
  }
  const lines = fs.readFileSync(ledger, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(lines.length, Object.keys(OPERATIONS).length);
  assert.ok(lines.every((l) => l.stub === true), "every written record is marked stub");
});

test("N9 the tray names tools the gateway actually serves, checked against the real files", () => {
  const root = path.resolve(import.meta.dirname, "..");
  const tray = JSON.parse(fs.readFileSync(path.join(root, "nervus", "tray.json"), "utf8"));
  const backends = JSON.parse(fs.readFileSync(path.join(root, "mcp-gateway", "backends.json"), "utf8"));
  const r = validateTray(tray, backends);
  assert.deepEqual(r.missing, []);
  assert.deepEqual(r.duplicates, []);
  assert.equal(r.ok, true);
  assert.ok(r.count >= 15, "the spec's tray list is all present");
});

test("N10 a tray naming a tool that does not exist is a failure, not a footnote", () => {
  const tray = { tools: [{ tool: "ghost-bench", prefix: "ghost" }] };
  const r = validateTray(tray, { backends: [{ prefix: "osv" }] });
  assert.equal(r.ok, false);
  assert.equal(r.missing[0].reason, "not in the gateway's backend list");
});
