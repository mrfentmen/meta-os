// Round 12, R12-036/037 — every Nervus operation's record shape, and the proof that a stub
// record cannot lose its stub label on the way to a ledger or the hosted receipt.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { validateRecord, OPERATIONS, DOSE_ZONES } from "../nervus/contracts.mjs";
import { runAndFile } from "../nervus/stub-runner.mjs";

const HASH = "a".repeat(64);
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "nervus-shape-"));

const REQUIRED = {
  map_layers: ["model_hash", "operation", "result"],
  sweep: ["model_hash", "operation", "layer_from", "layer_to", "result"],
  steer: ["model_hash", "operation", "layer", "neuron", "dose", "zone", "probe", "result"],
  ablate: ["model_hash", "operation", "layer", "neuron", "probe", "result"],
  evaluate_delta: ["model_hash", "operation", "before_hash", "after_hash", "probe", "result"],
};

test("R12-036 each of the five operations carries its required fields with the right types", () => {
  const ledger = path.join(tmp(), "ledger.jsonl");
  const records = {};
  for (const op of Object.keys(OPERATIONS)) {
    const r = runAndFile({ operation: op, params: {}, ledgerFile: ledger });
    assert.equal(r.ok, true, op + ": " + r.errors.join("; "));
    records[op] = r.record;
  }
  for (const [op, fields] of Object.entries(REQUIRED)) {
    const rec = records[op];
    assert.equal(rec.operation, op);
    for (const f of fields) assert.ok(f in rec, op + " missing " + f);
    assert.match(rec.model_hash, /^[0-9a-f]{8,64}$/);
    assert.deepEqual(validateRecord(rec), [], op + " validates");
    if (op === "sweep") {
      assert.equal(typeof rec.layer_from, "number");
      assert.equal(typeof rec.layer_to, "number");
      assert.ok(rec.layer_to >= rec.layer_from);
    }
    if (op === "steer" || op === "ablate") {
      assert.equal(typeof rec.layer, "number");
      assert.equal(typeof rec.neuron, "number");
    }
    if (op === "steer") {
      assert.equal(typeof rec.dose, "number");
      assert.ok(DOSE_ZONES.includes(rec.zone));
    }
    if (op === "evaluate_delta") {
      assert.match(rec.before_hash, /^[0-9a-f]{8,64}$/);
      assert.match(rec.after_hash, /^[0-9a-f]{8,64}$/);
    }
  }
});

test("R12-036 the written ledger is JSONL, one valid record per line, appended in order", () => {
  const ledger = path.join(tmp(), "ledger.jsonl");
  const ops = Object.keys(OPERATIONS);
  for (const op of ops) runAndFile({ operation: op, params: {}, ledgerFile: ledger });
  const raw = fs.readFileSync(ledger, "utf8");
  assert.ok(raw.endsWith("\n"));
  const lines = raw.trim().split("\n").map((l) => JSON.parse(l));
  assert.deepEqual(lines.map((l) => l.operation), ops);
  for (const [i, line] of lines.entries()) {
    assert.equal(line.stub, true, "ledger line " + (i + 1) + " is labelled stub");
    assert.equal(line.result.source, "STUB");
    assert.deepEqual(validateRecord(line), [], "ledger line " + (i + 1) + " validates as a record");
  }
});

test("R12-037 no stub result can be produced without the STUB label", () => {
  for (const op of Object.keys(OPERATIONS)) {
    const r = runAndFile({ operation: op, params: {}, ledgerFile: path.join(tmp(), "l.jsonl") });
    assert.equal(r.record.result.source, "STUB", op + " names its result a stub");
  }
});

test("R12-037 the hosted receipt's stub records are labelled in the file itself", () => {
  const receiptFile = path.resolve(import.meta.dirname, "..", "os-build", "nervus", "hosted-receipt.json");
  const receipt = JSON.parse(fs.readFileSync(receiptFile, "utf8"));
  assert.equal(receipt.stub, true, "the hosted receipt says it is a stub run");
  assert.ok(Array.isArray(receipt.rows), "the receipt carries one row per stage");
  for (const row of receipt.rows) {
    assert.equal(row.ok, true, row.op + " reported ok");
  }
  // The receipt points at the ledger; every line in that ledger is a stub record. A receipt
  // that said stub while its ledger held unlabelled records would be the lie this proves out.
  const ledgerFile = path.resolve(path.dirname(receiptFile), "..", "..", receipt.ledger);
  const lines = fs.readFileSync(ledgerFile, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.ok(lines.length >= receipt.rows.length);
  for (const rec of lines) {
    assert.equal(rec.stub, true, "every ledger record is labelled a stub");
    assert.equal(rec.result.source, "STUB");
  }
});
