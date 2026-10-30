// Node built-in test runner, no dependencies:
//   node --test tests/ignis-evidence-transparency.test.mjs
//
// IGNIS-ONEOFONE-4 (Del's one-of-one bar, Oct 29): the Ignis
// transparent-eval panel counts recorded Ignis assessments by
// whether their observations carry non-empty evidence strings —
// fully evidenced, partially evidenced, unevidenced, or
// unassessable when no usable observations array exists. Real state
// only: failures contribute nothing, other products move no bucket,
// and an empty or held session reads all zeros rather than
// inventing transparency. A filled evidence field is never claimed
// to make an assessment correct. No contract, server, or Spark-gate
// change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisEvidenceTransparency } from "../js/ignis-evidence.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const ok = (product, response) => ({
  status: "ok",
  product,
  response,
});
const obs = (evidence) => ({ evidence });

const zero = {
  total: 0,
  fullyEvidenced: 0,
  partiallyEvidenced: 0,
  unevidenced: 0,
  unassessable: 0,
};

test("evidence transparency: an empty session reads all zeros", () => {
  assert.deepEqual(ignisEvidenceTransparency([]), zero);
  assert.deepEqual(ignisEvidenceTransparency(null), zero);
  assert.deepEqual(ignisEvidenceTransparency(undefined), zero);
});

test("evidence transparency: buckets follow the recorded evidence strings", () => {
  const counts = ignisEvidenceTransparency([
    ok("ignis", { observations: [obs("smoke at window"), obs("flame at eave")] }),
    ok("ignis", { observations: [obs("smoke at window"), obs(""), obs(null)] }),
    ok("ignis", { observations: [obs(""), obs("   ")] }),
    ok("ignis", { observations: [] }),
    ok("ignis", { observations: "not an array" }),
    ok("ignis", {}),
    ok("ignis", null),
    { status: "ok", product: "ignis" },
    // Assessment-nested observations (ONEOFONE-2 fixture shape) still read.
    ok("ignis", { assessment: { observations: [obs("nested evidence")] } }),
  ]);
  assert.deepEqual(counts, {
    total: 9,
    fullyEvidenced: 2,
    partiallyEvidenced: 1,
    unevidenced: 2,
    unassessable: 4,
  });
});

test("evidence transparency: failures and other products move no bucket", () => {
  const counts = ignisEvidenceTransparency([
    { status: "failed", product: "ignis", response: { observations: [obs("x")] } },
    { status: "network_error", product: "ignis", response: { observations: [obs("x")] } },
    ok("vigiles", { observations: [obs("x")] }),
    ok("sanitas", { observations: [obs("x")] }),
    ok("ignis", { observations: [obs("x")] }),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    fullyEvidenced: 1,
    partiallyEvidenced: 0,
    unevidenced: 0,
    unassessable: 0,
  });
});

test("evidence transparency: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-evidence"'));
  assert.ok(html.includes("ignis-evidence-panel"));
  assert.ok(css.includes(".ignis-evidence-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-evidence-panel'));
  assert.ok(app.includes("ignisEvidenceTransparency"));
  assert.ok(app.includes("els.ignisEvidence.textContent"));
});
