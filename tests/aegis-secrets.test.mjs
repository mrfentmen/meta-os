// Aegis secret hygiene — the one property that matters is that the value never leaves the file.
// Every test here checks that as hard as it checks the count.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { scanText, scanTree, renderReport, PATTERNS } from "../aegis/secrets.mjs";

const AWS = "AKIA" + "Z".repeat(16);
const KEY_BLOCK = "-----BEGIN " + "OPENSSH PRIVATE KEY-----";
const GH = "ghp_" + "a".repeat(36);

test("H1 counts by pattern and records location, never the value", () => {
  const text = ["line one", "key " + AWS + " here", "nothing", KEY_BLOCK, "gh " + GH].join("\n");
  const hits = scanText(text, { path: "x.txt" });
  const ids = hits.map((h) => h.id).sort();
  assert.deepEqual(ids, ["aws-access-key-id", "github-token", "private-key-block"]);
  assert.deepEqual(hits.find((h) => h.id === "aws-access-key-id"), { id: "aws-access-key-id", confidence: "confirmed", path: "x.txt", line: 2 });
  assert.ok(!JSON.stringify(hits).includes(AWS), "the matched value is not in the result");
  assert.ok(!JSON.stringify(hits).includes(GH));
});

test("H2 a generic assignment is counted as review, not as confirmed", () => {
  const hits = scanText('api_key = "abcdefghijklmnopqrst"', { path: "cfg" });
  assert.equal(hits.length, 1);
  assert.equal(hits[0].id, "assigned-secret");
  assert.equal(hits[0].confidence, "review");
  assert.ok(!JSON.stringify(hits).includes("abcdefghijklmnopqrst"));
});

test("H3 a short value is not an assigned secret", () => {
  assert.equal(scanText('password = "short"').length, 0);
});

test("H4 allowlisted fixture lines are counted separately and excluded from locations", () => {
  const text = "EXAMPLE " + AWS;
  const hits = scanText(text, { path: "f", allow: (line) => line.includes("EXAMPLE") });
  assert.equal(hits.length, 1);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-sec-"));
  fs.writeFileSync(path.join(dir, "f.txt"), text);
  const r = scanTree(dir, { allow: (line) => line.includes("EXAMPLE") });
  assert.equal(r.allowlisted.length, 1);
  assert.equal(r.locations.length, 0);
});

test("H5 the tree scan skips binary, cache dirs and non-text, and says how many", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-sec-"));
  fs.writeFileSync(path.join(dir, "a.js"), "const x = 1;");
  // A .png is skipped as not-text before it is ever read, so a png fixture would test the
  // extension filter and not the binary check. This file has a text name and NUL bytes.
  fs.writeFileSync(path.join(dir, "blob.js"), Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x00, 0x01]));
  fs.writeFileSync(path.join(dir, "pic.png"), Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x00, 0x01]));
  fs.mkdirSync(path.join(dir, "node_modules"), { recursive: true });
  fs.writeFileSync(path.join(dir, "node_modules", "deep.js"), "AKIA" + "Q".repeat(16));
  const r = scanTree(dir);
  assert.equal(r.scanned, 1);
  assert.equal(r.skipped.binary, 1, "a text-named file with NUL bytes is counted binary");
  assert.equal(r.skipped.notText, 1, "the .png never reaches the binary check");
  assert.equal(r.skipped.dirs, 1);
  assert.equal(r.byConfidence.confirmed, 0, "a key in node_modules is not the tree's key");
});

test("H6 a clean tree reports zero and says how many files were read", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-sec-"));
  fs.writeFileSync(path.join(dir, "a.js"), "export const answer = 42;\n");
  const r = scanTree(dir);
  const md = renderReport(r, { runId: "sec-run" });
  assert.match(md, /Zero is the result, not an empty section: 1 files were read/);
  assert.equal(r.byConfidence.confirmed + r.byConfidence.review, 0);
});

test("H7 the report never contains a matched value", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-sec-"));
  fs.writeFileSync(path.join(dir, "a.js"), "const k = \"" + AWS + "\";\n");
  const r = scanTree(dir);
  const md = renderReport(r, { runId: "sec-run" });
  assert.match(md, /aws-access-key-id/);
  assert.ok(!md.includes(AWS), "the report is public; the value must not be in it");
  assert.ok(!JSON.stringify(r).includes(AWS));
});

test("H8 every pattern has a confidence level the report knows how to group", () => {
  for (const p of PATTERNS) assert.ok(["confirmed", "review"].includes(p.confidence), p.id);
});
