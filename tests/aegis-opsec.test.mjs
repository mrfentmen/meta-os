// Aegis OPSEC v1 — the checks, the allow markers, and the rule that the report never quotes.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { scanText, scanFiles, findingsFrom, renderReport, CHECKS } from "../aegis/opsec.mjs";

test("P1 each check fires on its own shape", () => {
  const text = [
    "run from /Users/delgado/work/meta-os",
    "the box is at 192.168.4.20",
    "mail me at someone@personal.example",
    "the api lives at queue.internal",
    "tested on MacBook-Pro-7",
  ].join("\n");
  const hits = scanText(text, { path: "x.md" });
  assert.deepEqual(hits.map((h) => h.id).sort(), ["email", "home-path", "internal-host", "machine-name", "private-ip"]);
  assert.equal(hits.find((h) => h.id === "home-path").line, 1);
});

test("P2 example markers opt a line out, and nothing else does", () => {
  assert.equal(scanText("copy it to /Users/you/meta-os").length, 0);
  assert.equal(scanText("see <your-name> and <path>").length, 0);
  assert.equal(scanText("served at localhost:3000").length, 0, "localhost is not a private-ip leak");
  assert.equal(scanText("deployed at example.com").length, 0);
});

test("P3 a public domain is not an internal host", () => {
  assert.equal(scanText("see https://meta-os.pages.dev for the demo").length, 0);
  assert.equal(scanText("the db is at db.corp").length, 1);
});

test("P4 the report carries locations and never the matched text", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-opsec-"));
  fs.writeFileSync(path.join(dir, "README.md"), "built on /Users/delgado/meta and mailed to a@b.example\n");
  const scan = scanFiles(["README.md"], { root: dir });
  assert.equal(scan.files.length, 1);
  const md = renderReport(scan, [], { runId: "opsec-run", materials: ["README.md"] });
  assert.match(md, /`README.md` \| 1 \| `home-path`/);
  assert.ok(!md.includes("delgado"), "the account name is not republished");
  assert.ok(!md.includes("a@b.example"));
});

test("P5 one finding per check, with every location named in the evidence", () => {
  const scan = {
    files: ["a.md"], missing: [], counts: {},
    hits: [
      { id: "home-path", severity: "low", path: "a.md", line: 1 },
      { id: "home-path", severity: "low", path: "a.md", line: 9 },
      { id: "email", severity: "low", path: "a.md", line: 4 },
    ],
  };
  const f = findingsFrom(scan, { runId: "r" });
  assert.equal(f.length, 2);
  const home = f.find((x) => x.title.startsWith("home-path"));
  assert.match(home.evidence, /a\.md:1, a\.md:9/);
  assert.equal(home.severity, "low");
});

test("P6 missing materials are named, not silently skipped", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-opsec-"));
  const scan = scanFiles(["nope.md"], { root: dir });
  assert.deepEqual(scan.missing, ["nope.md"]);
  const md = renderReport(scan, [], { runId: "r", materials: ["nope.md"] });
  assert.match(md, /Not found \(not reviewed\)/);
});

test("P7 every check declares a severity the finding record accepts", () => {
  const allowed = ["info", "low", "medium", "high", "critical"];
  for (const c of CHECKS) assert.ok(allowed.includes(c.severity), c.id);
});
