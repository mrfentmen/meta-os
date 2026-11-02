import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import * as mod from "../aegis/findings.mjs";
import { appendFinding, readFindings, summarize, FindingError, SEVERITIES } from "../aegis/findings.mjs";

function tmpFile() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "aegis-findings-")), "findings.jsonl");
}

const good = {
  severity: "medium",
  title: "example finding",
  evidence: "the sweep saw exactly this",
  source: "test",
  run: "run-1",
};

test("appends a record with a recorder-set timestamp", () => {
  const file = tmpFile();
  const rec = appendFinding(file, { ...good, ts: "1999-01-01T00:00:00.000Z" });
  assert.equal(rec.v, 1);
  assert.equal(rec.severity, "medium");
  assert.notEqual(rec.ts, "1999-01-01T00:00:00.000Z");
  assert.ok(Math.abs(Date.now() - Date.parse(rec.ts)) < 5000);
  assert.equal(fs.readFileSync(file, "utf8").trim().split("\n").length, 1);
});

test("reads back in append order", () => {
  const file = tmpFile();
  appendFinding(file, { ...good, title: "first" });
  appendFinding(file, { ...good, title: "second", severity: "high" });
  const { findings, torn } = readFindings(file);
  assert.equal(torn, 0);
  assert.deepEqual(findings.map((f) => f.title), ["first", "second"]);
  assert.deepEqual(findings.map((f) => f.severity), ["medium", "high"]);
});

test("refuses an invalid record and writes nothing", () => {
  const file = tmpFile();
  const bad = [
    { ...good, severity: "urgent" },
    { ...good, severity: undefined },
    { ...good, evidence: "   " },
    { ...good, source: undefined },
    { ...good, run: "" },
    { ...good, title: "x".repeat(201) },
    { ...good, evidence: "x".repeat(4001) },
  ];
  for (const f of bad) assert.throws(() => appendFinding(file, f), FindingError);
  assert.equal(fs.existsSync(file), false);
});

test("the module offers no way to change or remove a record", () => {
  assert.deepEqual(Object.keys(mod).sort(), ["FindingError", "SEVERITIES", "appendFinding", "readFindings", "summarize"]);
});

test("a torn line is skipped, and the next append still parses", () => {
  const file = tmpFile();
  appendFinding(file, { ...good, title: "before crash" });
  fs.appendFileSync(file, '{"ts":"torn');           // a crash mid-append: no newline
  appendFinding(file, { ...good, title: "after crash" });
  const { findings, torn } = readFindings(file);
  assert.equal(torn, 1);
  assert.deepEqual(findings.map((f) => f.title), ["before crash", "after crash"]);
});

test("missing file reads as zero findings, and summary names every severity", () => {
  const file = tmpFile();
  assert.deepEqual(readFindings(file), { findings: [], torn: 0 });
  const s = summarize([]);
  assert.equal(s.total, 0);
  assert.deepEqual(Object.keys(s.bySeverity), SEVERITIES);
  assert.ok(SEVERITIES.every((k) => s.bySeverity[k] === 0));
});
