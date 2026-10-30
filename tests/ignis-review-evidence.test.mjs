// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-evidence.test.mjs
//
// IGNIS-ONEOFONE-17 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by evidence completeness counts only the recorded
// ok Ignis assessments already awaiting human review —
// requires_human_review === true — bucketed by whether their
// observations carry evidence a human reviewer can actually
// inspect, the same completeness read ONEOFONE-4 applies to all
// successful Ignis assessments, here scoped to the flagged
// queue. Real state only: clear and unknown-flag entries move no
// bucket, failures and other products move no bucket, a flagged
// entry with no usable observations array counts as
// unassessable (never a silent unevidenced), an empty
// observations array counts as unevidenced, and an empty or held
// session reads all zeros. The panel itself lives in index.html
// (hidden under Vigiles/Medicus by styles.css) and is rendered
// from log.entries() inside updateLogStats in js/app.js. No
// contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByEvidence } from "../js/ignis-review-evidence.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const zero = () => ({
  totalFlagged: 0,
  fullyEvidenced: 0,
  partiallyEvidenced: 0,
  unevidenced: 0,
  unassessable: 0,
});

const flagged = (observations, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: {
      requires_human_review: true,
      observations,
    },
  },
  ...overrides,
});

const obs = (evidence) => ({ evidence });

test("review by evidence: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByEvidence([]), zero());
  assert.deepEqual(ignisReviewByEvidence(null), zero());
  assert.deepEqual(ignisReviewByEvidence(undefined), zero());
});

test("review by evidence: flagged assessments bucket by their observations' evidence completeness", () => {
  assert.deepEqual(
    ignisReviewByEvidence([
      flagged([obs("smoke column, left frame"), obs("heat shimmer")]),
      flagged([obs("smoke column"), obs(""), obs(null), {}]),
      flagged([obs(""), obs(null)]),
      flagged([]),
      flagged(undefined),
      flagged("not an array"),
    ]),
    {
      totalFlagged: 6,
      fullyEvidenced: 1,
      partiallyEvidenced: 1,
      unevidenced: 2,
      unassessable: 2,
    },
  );
});

test("review by evidence: observations on the response itself count, like ONEOFONE-4", () => {
  const entry = {
    status: "ok",
    product: "ignis",
    response: {
      observations: [obs("smoke column")],
      assessment: { requires_human_review: true },
    },
  };
  assert.deepEqual(ignisReviewByEvidence([entry]), {
    ...zero(),
    totalFlagged: 1,
    fullyEvidenced: 1,
  });
});

test("review by evidence: whitespace-only evidence strings count as no evidence", () => {
  assert.deepEqual(
    ignisReviewByEvidence([flagged([obs("   "), obs("\n")])]),
    {
      ...zero(),
      totalFlagged: 1,
      unevidenced: 1,
    },
  );
});

test("review by evidence: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByEvidence([
    flagged([obs("smoke column")], {
      response: { assessment: { requires_human_review: false, observations: [obs("smoke column")] } },
    }),
    flagged([obs("smoke column")], {
      response: { assessment: { observations: [obs("smoke column")] } },
    }),
    flagged([obs("smoke column")], { status: "network_error" }),
    flagged([obs("smoke column")], { product: "vigiles" }),
    flagged([obs("smoke column")], { product: "medicus" }),
    flagged([obs("smoke column")]),
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    totalFlagged: 1,
    fullyEvidenced: 1,
  });
});

test("review by evidence: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-evidence"'));
  assert.ok(html.includes("ignis-review-evidence-panel"));
  assert.ok(css.includes(".ignis-review-evidence-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-evidence-panel'));
  assert.ok(app.includes("ignisReviewByEvidence"));
  assert.ok(app.includes('ignisReviewEvidence: $("ignis-review-evidence")'));
  assert.ok(app.includes("els.ignisReviewEvidence.textContent"));
});
