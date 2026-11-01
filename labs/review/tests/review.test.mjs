// labs/review/tests/review.test.mjs — node:test, no dependencies.
// Tier counter on the known-count sample (3 yellow, 2 red) and 20-sample
// schema spot-check against the repo's js/schema.js (read-only import).
// Run: node --test labs/review/tests/review.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { tmpdir as osTmp } from "node:os";
import { writeFileSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { validateAssessment } from "../../../js/schema.js";
import { guardNoName } from "../bolo-guard.mjs";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..");

test("tier counter reports 3 yellow and 2 red on the sample", () => {
  const out = execFileSync("node", [join(dir, "tier-counter.mjs"), join(dir, "sample-records.jsonl")], { encoding: "utf8" });
  assert.match(out, /records: 13/);
  assert.match(out, /yellow: 6/);
  assert.match(out, /red: 4/);
});

function fakeAssessment(product, category) {
  const flagged = category !== "normal activity" && category !== "no hazard visible";
  return {
    product,
    timestamp: "2026-11-01T10:00:00+00:00",
    category,
    flagged,
    observations: [{ category, description: "test observation", evidence: "test frame", confidence: 0.8 }],
    assessment: { category, summary: "test summary", uncertainty: ["test"], flagged, requires_human_review: product === "medicus" ? true : flagged },
    processing: { ms: 12, latency_ms: 12, model: "test-model" },
  };
}

test("schema spot-check: 20 generated samples validate", () => {
  const cats = {
    vigiles: ["normal activity", "energetic movement", "possible altercation", "person down", "indeterminate"],
    ignis: ["no hazard visible", "visible flame", "visible smoke", "steam or fog"],
    medicus: ["normal activity", "person on ground"],
  };
  let n = 0;
  for (const [product, list] of Object.entries(cats)) {
    for (const category of list) {
      for (let k = 0; k < 2 && n < 20; k++) {
        const r = validateAssessment(fakeAssessment(product, category), product);
        assert.equal(r.ok, true, `${product}/${category} sample ${k} validates`);
        n++;
      }
    }
  }
  assert.equal(n, 20);
});

test("NC-074 guard refuses a smuggled name, accepts clean records", () => {
  assert.throws(() => guardNoName({ description: "x", name: "John Doe" }), /refused/);
  assert.equal(guardNoName({ description: "x", identity: "UNIDENTIFIED" }), true);
  assert.equal(guardNoName({ description: "x" }), true);
});

test("NC-075 purge on a copy: byte counts and no gaps", () => {
  const out = execFileSync("node", [join(dir, "purge-copy.mjs"),
    join(dir, "sample-records.jsonl"), join(osTmp(), "purge-test.jsonl"),
    "SIM-2026-11-01-002", "SIM-2026-11-01-009"], { encoding: "utf8" });
  assert.match(out, /purged=2/);
  assert.match(out, /gaps=false/);
});

test("NC-076 fuzz exact proportions", () => {
  const lines = [];
  for (let i = 0; i < 200; i++) {
    const tier = i < 80 ? "yellow" : i < 150 ? "red" : "none";
    lines.push(JSON.stringify({ incident: { id: "F" + i, tier } }));
  }
  const fp = join(osTmp(), "fuzz-test.jsonl");
  writeFileSync(fp, lines.join("\n") + "\n");
  const out = execFileSync("node", [join(dir, "tier-counter.mjs"), fp], { encoding: "utf8" });
  assert.match(out, /yellow: 80/);
  assert.match(out, /red: 70/);
  assert.match(out, /none: 50/);
});

test("NC-081 every sample record carries the incident contract", () => {
  const recs = readFileSync(join(dir, "sample-records.jsonl"), "utf8").split("\n").filter((l) => l.trim()).map(JSON.parse);
  assert.ok(recs.length >= 13, "13+ samples");
  for (const r of recs) {
    for (const k of ["id", "product", "category", "tier", "timestamp", "description", "identity"]) {
      assert.ok(r.incident[k] !== undefined, `${r.incident.id} has ${k}`);
    }
    assert.equal(r.incident.identity, "UNIDENTIFIED");
  }
});