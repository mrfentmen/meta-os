// CB2-498 — Aegis findings record shape.
//
// aegis/findings.mjs is the writer: append-only JSONL, severity from the
// documented set, and the writer stamps its own timestamp so a record cannot
// be backdated. Evidence is counts-only by contract — the record carries no
// `value` field, so a finding can never smuggle a scanned secret or a raw
// payload into the ledger.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { SEVERITIES, FindingError, appendFinding, readFindings } from "../aegis/findings.mjs";

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-findings-"));
const ledger = path.join(dir, "findings.jsonl");

const fixture = {
  severity: "low",
  title: "certificate expires in 9 days",
  evidence: "counts: expiring=1, scanned=4",
  source: "sweep",
  run: "run-001",
  target: "meta-os.pages.dev",
};

test("CB2-498 a finding carries severity from the documented set and no value field", () => {
  const rec = appendFinding(ledger, fixture);
  assert.deepEqual(Object.keys(rec).sort(), [
    "evidence", "run", "severity", "source", "target", "title", "ts", "v",
  ]);
  assert.ok(SEVERITIES.includes(rec.severity), "severity is documented");
  assert.equal(rec.severity, "low");
  assert.equal(rec.v, 1);
  assert.equal(rec.target, "meta-os.pages.dev");
  assert.equal(hasOwn(rec, "value"), false, "no value field on a finding");
  assert.match(rec.ts, /^\d{4}-\d{2}-\d{2}T/);
});

test("CB2-498b a severity outside the set is refused and nothing is written", () => {
  const before = fs.readFileSync(ledger, "utf8");
  assert.throws(
    () => appendFinding(ledger, { ...fixture, severity: "urgent" }),
    (e) => e instanceof FindingError && /severity must be one of info, low, medium, high, critical/.test(e.message),
  );
  assert.equal(fs.readFileSync(ledger, "utf8"), before, "ledger is unchanged after a refusal");
});

test("CB2-498c the ledger reads back one record per append, in order, with nothing torn", () => {
  appendFinding(ledger, { ...fixture, severity: "medium", title: "second" });
  const { findings, torn } = readFindings(ledger);
  assert.equal(torn, 0);
  assert.equal(findings.length, 2);
  assert.deepEqual(findings.map((f) => f.severity), ["low", "medium"]);
  assert.equal(findings.some((f) => hasOwn(f, "value")), false, "no record carries a value field");
});

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}
