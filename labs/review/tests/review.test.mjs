// labs/review/tests/review.test.mjs — node:test, no dependencies.
// Tier counter on the known-count sample (3 yellow, 2 red) and 20-sample
// schema spot-check against the repo's js/schema.js (read-only import).
// Run: node --test labs/review/tests/review.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { validateAssessment } from "../../../js/schema.js";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..");

test("tier counter reports 3 yellow and 2 red on the sample", () => {
  const out = execFileSync("node", [join(dir, "tier-counter.mjs"), join(dir, "sample-records.jsonl")], { encoding: "utf8" });
  assert.match(out, /records: 6/);
  assert.match(out, /yellow: 3/);
  assert.match(out, /red: 2/);
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
