// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-observation-count.test.mjs
//
// IGNIS-ONEOFONE-19 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by observation count counts only the recorded
// ok Ignis assessments already awaiting human review —
// requires_human_review === true — bucketed by how many
// observations the response itself recorded: none (empty array),
// one, two or three, four or more, or unrecorded where no usable
// observations array exists to read. Real state only: clear and
// unknown-flag entries move no bucket, failures and other
// products move no bucket, a flagged entry with no usable
// observations array counts as unrecorded (never a silent none),
// observations nested under assessment count the same as
// top-level response observations, and an empty or held
// session reads all zeros. The panel itself lives in index.html
// (hidden under Vigiles/Medicus by styles.css) and is rendered
// from log.entries() inside updateLogStats in js/app.js. No
// contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByObservationCount } from "../js/ignis-review-observation-count.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const zero = () => ({
  totalFlagged: 0,
  none: 0,
  one: 0,
  twoOrThree: 0,
  fourOrMore: 0,
  unrecorded: 0,
});

const obs = (category) => ({ category, description: "seen", evidence: "" });
const flagged = (observations, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: {
      requires_human_review: true,
    },
    observations,
  },
  ...overrides,
});

test("review by observation count: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByObservationCount([]), zero());
  assert.deepEqual(ignisReviewByObservationCount(null), zero());
  assert.deepEqual(ignisReviewByObservationCount(undefined), zero());
});

test("review by observation count: flagged assessments bucket by their own observation count", () => {
  assert.deepEqual(
    ignisReviewByObservationCount([
      flagged([]),
      flagged([obs("visible smoke")]),
      flagged([obs("visible smoke"), obs("steam or fog")]),
      flagged([obs("visible smoke"), obs("steam or fog"), obs("visible flame")]),
      flagged([obs("a"), obs("b"), obs("c"), obs("d")]),
      flagged([obs("a"), obs("b"), obs("c"), obs("d"), obs("e")]),
      flagged(undefined),
      flagged(null),
      flagged("not an array"),
    ]),
    {
      totalFlagged: 9,
      none: 1,
      one: 1,
      twoOrThree: 2,
      fourOrMore: 2,
      unrecorded: 3,
    },
  );
});

test("review by observation count: assessment-nested observations count the same as top-level ones", () => {
  const counts = ignisReviewByObservationCount([
    {
      status: "ok",
      product: "ignis",
      response: {
        assessment: {
          requires_human_review: true,
          observations: [obs("visible smoke"), obs("visible flame")],
        },
      },
    },
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    totalFlagged: 1,
    twoOrThree: 1,
  });
});

test("review by observation count: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByObservationCount([
    flagged([obs("visible smoke")], {
      response: { assessment: { requires_human_review: false }, observations: [obs("visible smoke")] },
    }),
    flagged([obs("visible smoke")], {
      response: { assessment: {}, observations: [obs("visible smoke")] },
    }),
    flagged([obs("visible smoke")], { status: "network_error" }),
    flagged([obs("visible smoke")], { product: "vigiles" }),
    flagged([obs("visible smoke")], { product: "medicus" }),
    flagged([obs("visible smoke")]),
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    totalFlagged: 1,
    one: 1,
  });
});

test("review by observation count: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-observation-count"'));
  assert.ok(html.includes("ignis-review-observation-count-panel"));
  assert.ok(css.includes(".ignis-review-observation-count-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-observation-count-panel'));
  assert.ok(app.includes("ignisReviewByObservationCount"));
  assert.ok(app.includes('ignisReviewObservationCount: $("ignis-review-observation-count")'));
  assert.ok(app.includes("els.ignisReviewObservationCount.textContent"));
});
