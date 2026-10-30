// Node built-in test runner, no dependencies:
//   node --test tests/ignis-reported-confidence.test.mjs
//
// IGNIS-ONEOFONE-2 (Del's one-of-one bar, Oct 29): the Ignis
// reported-confidence spread counts the confidence values recorded
// Ignis assessments themselves reported on their observations,
// banded high / medium / low / unreported. Real state only:
// failures contribute nothing, other products move no bucket, and
// an empty or held session reads all zeros rather than inventing a
// reading. Bands group reported values; they never re-score an
// assessment or collapse it to alarm / no-alarm. No contract,
// server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReportedConfidence } from "../js/ignis-confidence.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const obs = (confidence) => ({ confidence });
const ok = (product, observations) => ({
  status: "ok",
  product,
  response: { assessment: { observations } },
});

const zero = {
  total: 0,
  high: 0,
  medium: 0,
  low: 0,
  unreported: 0,
};

test("confidence spread: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReportedConfidence([]), zero);
  assert.deepEqual(ignisReportedConfidence(null), zero);
  assert.deepEqual(ignisReportedConfidence(undefined), zero);
});

test("confidence spread: band boundaries are high >= 0.8, medium >= 0.5, else low", () => {
  const counts = ignisReportedConfidence([
    ok("ignis", [obs(1), obs(0.8), obs(0.79), obs(0.5), obs(0.49), obs(0)]),
  ]);
  assert.deepEqual(counts, {
    total: 6,
    high: 2,
    medium: 2,
    low: 2,
    unreported: 0,
  });
});

test("confidence spread: null, missing, and non-finite confidences count as unreported", () => {
  const counts = ignisReportedConfidence([
    ok("ignis", [obs(null), obs(undefined), {}, obs("0.9"), obs(NaN), obs(0.9)]),
  ]);
  assert.deepEqual(counts, {
    total: 6,
    high: 1,
    medium: 0,
    low: 0,
    unreported: 5,
  });
});

test("confidence spread: failures, other products, and missing observations move no bucket", () => {
  const counts = ignisReportedConfidence([
    { status: "failed", product: "ignis", response: { assessment: { observations: [obs(1)] } } },
    ok("vigiles", [obs(1)]),
    ok("sanitas", [obs(1)]),
    ok("ignis", null),
    { status: "ok", product: "ignis" },
    ok("ignis", [obs(0.6)]),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    high: 0,
    medium: 1,
    low: 0,
    unreported: 0,
  });
});

test("confidence spread: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-confidence"'));
  assert.ok(html.includes("ignis-confidence-panel"));
  assert.ok(css.includes(".ignis-confidence-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-confidence-panel'));
  assert.ok(app.includes('ignisReportedConfidence'));
  assert.ok(app.includes('els.ignisConfidence.textContent'));
});
