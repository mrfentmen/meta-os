// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-uncertainty.test.mjs
//
// IGNIS-ONEOFONE-18 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by uncertainty disclosure counts only the recorded
// ok Ignis assessments already awaiting human review —
// requires_human_review === true — bucketed by whether the
// assessment itself disclosed caveats, the same disclosure read
// ONEOFONE-5 applies to all successful Ignis assessments, here
// scoped to the flagged queue. Real state only: clear and
// unknown-flag entries move no bucket, failures and other
// products move no bucket, a flagged entry with no usable
// uncertainty array counts as unrecorded (never a silent none),
// an empty array counts as none disclosed, and an empty or held
// session reads all zeros. The panel itself lives in index.html
// (hidden under Vigiles/Medicus by styles.css) and is rendered
// from log.entries() inside updateLogStats in js/app.js. No
// contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByUncertainty } from "../js/ignis-review-uncertainty.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const zero = () => ({
  totalFlagged: 0,
  disclosed: 0,
  noneDisclosed: 0,
  unrecorded: 0,
});

const flagged = (uncertainty, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: {
      requires_human_review: true,
      uncertainty,
    },
  },
  ...overrides,
});

test("review by uncertainty: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByUncertainty([]), zero());
  assert.deepEqual(ignisReviewByUncertainty(null), zero());
  assert.deepEqual(ignisReviewByUncertainty(undefined), zero());
});

test("review by uncertainty: flagged assessments bucket by their own disclosed caveats", () => {
  assert.deepEqual(
    ignisReviewByUncertainty([
      flagged(["low light", "partially obscured"]),
      flagged([]),
      flagged(undefined),
      flagged(null),
      flagged("not an array"),
    ]),
    {
      totalFlagged: 5,
      disclosed: 1,
      noneDisclosed: 1,
      unrecorded: 3,
    },
  );
});

test("review by uncertainty: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByUncertainty([
    flagged(["low light"], {
      response: { assessment: { requires_human_review: false, uncertainty: ["low light"] } },
    }),
    flagged(["low light"], {
      response: { assessment: { uncertainty: ["low light"] } },
    }),
    flagged(["low light"], { status: "network_error" }),
    flagged(["low light"], { product: "vigiles" }),
    flagged(["low light"], { product: "medicus" }),
    flagged(["low light"]),
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    totalFlagged: 1,
    disclosed: 1,
  });
});

test("review by uncertainty: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-uncertainty"'));
  assert.ok(html.includes("ignis-review-uncertainty-panel"));
  assert.ok(css.includes(".ignis-review-uncertainty-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-uncertainty-panel'));
  assert.ok(app.includes("ignisReviewByUncertainty"));
  assert.ok(app.includes('ignisReviewUncertainty: $("ignis-review-uncertainty")'));
  assert.ok(app.includes("els.ignisReviewUncertainty.textContent"));
});
