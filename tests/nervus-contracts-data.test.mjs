// CB2-494..496 — the Nervus contracts and the recorded layer curve, as data.
//
// Nothing here runs a model. The contracts are the spec in code: what each
// operation needs, what it produces, and the fact that none of it has run for
// real yet. The curve is the four points that were measured, read back exactly.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { OPERATIONS, SHARED_LEDGER, RECORD_FIELDS } from "../nervus/contracts.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const curve = JSON.parse(fs.readFileSync(path.join(ROOT, "nervus", "layer-curve.json"), "utf8"));
const EXPECTED_OPS = ["sweep", "steer", "ablate", "evaluate_delta", "map_layers"];

test("CB2-494 every operation declares its inputs, its outputs, and that it needs a real run", () => {
  assert.deepEqual(Object.keys(OPERATIONS).sort(), [...EXPECTED_OPS].sort(), "the five operations");

  for (const name of EXPECTED_OPS) {
    const op = OPERATIONS[name];
    assert.ok(Array.isArray(op.requires) && op.requires.length > 0, name + " declares inputs");
    assert.ok(Array.isArray(op.produces) && op.produces.length > 0, name + " declares outputs");
    assert.equal(typeof op.requires_real_run, "boolean", name + " carries the flag as a boolean");
    assert.equal(op.requires_real_run, true, name + " has not run for real, so the flag says so");
    assert.ok(op.why && op.why.length > 10, name + " says why it exists");
  }

  // The flag is a real field, not prose: adding an operation without it fails here.
  for (const [name, op] of Object.entries(OPERATIONS)) {
    assert.ok("requires_real_run" in op, name + " must declare requires_real_run");
  }
});

test("CB2-495 both doors write one ledger: every contract names the same one", () => {
  assert.equal(typeof SHARED_LEDGER, "string");
  assert.ok(SHARED_LEDGER.length > 0);

  for (const [name, op] of Object.entries(OPERATIONS)) {
    assert.equal(op.ledger, SHARED_LEDGER, name + " writes the shared ledger");
  }

  // The ledger is part of the record shape a reader is given, not a private field.
  assert.ok(RECORD_FIELDS.includes("operation") && RECORD_FIELDS.includes("model_hash"));
});

test("CB2-496 the layer curve is the four recorded points, unchanged", () => {
  assert.equal(curve.record, "layer-curve");
  assert.equal(curve.operation, "map_layers");
  assert.ok(curve.source && curve.source.length > 10, "the curve says where it came from");
  assert.deepEqual(curve.points, [
    { layer: 4, score: 4.6 },
    { layer: 8, score: 19.5 },
    { layer: 16, score: 12.8 },
    { layer: 24, score: 10.2 },
  ]);

  // Ascending layers, finite scores, no invented points between them.
  for (let i = 1; i < curve.points.length; i++) {
    assert.ok(curve.points[i].layer > curve.points[i - 1].layer, "layers ascend");
  }
  for (const p of curve.points) assert.ok(Number.isFinite(p.score), "score is a number: " + p.layer);
  assert.equal(curve.points.length, 4, "four measured points, no interpolation");
});
