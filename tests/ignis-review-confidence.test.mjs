// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-confidence.test.mjs
//
// IGNIS-ONEOFONE-14 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by reported confidence counts only observations on
// assessments already awaiting human review — recorded ok Ignis
// assessments whose assessment itself carried
// requires_human_review === true — banded with ONEOFONE-2's bands:
// high (>= 0.8), medium (>= 0.5), low (below 0.5), or unreported
// (null, missing, or not a finite number). Real state only: clear
// and unknown-flag entries move no bucket, failures and other
// products move no bucket, a flagged entry with no observations
// array contributes nothing, and an empty or held session reads
// all zeros. The label-feedback slice this number was first slated
// for is blocked, not built: no officer-disposition field exists
// in the log or the v2 contract, so no disposition bucket is
// fabricated here. The panel itself lives in index.html (hidden
// under Vigiles/Medicus by styles.css) and is rendered from
// log.entries() inside updateLogStats in js/app.js. No contract,
// server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByConfidence } from "../js/ignis-review-confidence.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const flagged = (observations, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: { requires_human_review: true, observations },
  },
  ...overrides,
});

test("review by confidence: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByConfidence([]), {
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    unreported: 0,
  });
  assert.deepEqual(ignisReviewByConfidence(null), {
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    unreported: 0,
  });
  assert.deepEqual(ignisReviewByConfidence(undefined), {
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    unreported: 0,
  });
});

test("review by confidence: observations on a flagged entry band by reported value", () => {
  assert.deepEqual(
    ignisReviewByConfidence([
      flagged([
        { confidence: 0.95 },
        { confidence: 0.8 },
        { confidence: 0.6 },
        { confidence: 0.5 },
        { confidence: 0.2 },
        { confidence: null },
        {},
        { confidence: Number.NaN },
      ]),
    ]),
    {
      total: 8,
      high: 2,
      medium: 2,
      low: 1,
      unreported: 3,
    },
  );
});

test("review by confidence: a flagged entry with no observations array contributes nothing", () => {
  assert.deepEqual(
    ignisReviewByConfidence([
      flagged(undefined),
      flagged(null),
      flagged("not-an-array"),
    ]),
    {
      total: 0,
      high: 0,
      medium: 0,
      low: 0,
      unreported: 0,
    },
  );
});

test("review by confidence: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByConfidence([
    flagged([{ confidence: 0.9 }], {
      response: { assessment: { requires_human_review: false, observations: [{ confidence: 0.9 }] } },
    }),
    flagged([{ confidence: 0.9 }], {
      response: { assessment: { observations: [{ confidence: 0.9 }] } },
    }),
    flagged([{ confidence: 0.9 }], { status: "network_error" }),
    flagged([{ confidence: 0.9 }], { product: "vigiles" }),
    flagged([{ confidence: 0.9 }]),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    high: 1,
    medium: 0,
    low: 0,
    unreported: 0,
  });
});

test("review by confidence: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-confidence"'));
  assert.ok(html.includes("ignis-review-confidence-panel"));
  assert.ok(css.includes(".ignis-review-confidence-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-confidence-panel'));
  assert.ok(app.includes("ignisReviewByConfidence"));
  assert.ok(app.includes('ignisReviewConfidence: $("ignis-review-confidence")'));
  assert.ok(app.includes("els.ignisReviewConfidence.textContent"));
});
