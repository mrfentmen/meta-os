// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-observation-category.test.mjs
//
// IGNIS-ONEOFONE-16 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by observation category counts only the
// observations inside assessments already awaiting human review —
// recorded ok Ignis assessments whose assessment itself carried
// requires_human_review === true — bucketed by the category each
// observation itself carried, the same contract categories
// ONEOFONE-7 reads for all successful Ignis assessments. Real
// state only: clear and unknown-flag entries move no bucket,
// failures and other products move no bucket, a flagged entry
// with no usable observations array contributes nothing, and an
// observation with no usable or non-contract category counts in
// the total only, never inventing a bucket. An empty or held
// session reads all zeros. The panel itself lives in index.html
// (hidden under Vigiles/Medicus by styles.css) and is rendered
// from log.entries() inside updateLogStats in js/app.js. No
// contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByObservationCategory } from "../js/ignis-review-observation-category.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const zero = () => ({
  total: 0,
  visibleSmoke: 0,
  visibleFlame: 0,
  steamOrFog: 0,
  flameLikeLighting: 0,
  obscuredOrDistant: 0,
  noHazard: 0,
  indeterminate: 0,
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

const obs = (category) => ({ category });

test("review by observation category: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByObservationCategory([]), zero());
  assert.deepEqual(ignisReviewByObservationCategory(null), zero());
  assert.deepEqual(ignisReviewByObservationCategory(undefined), zero());
});

test("review by observation category: flagged observations bucket by their own recorded category", () => {
  assert.deepEqual(
    ignisReviewByObservationCategory([
      flagged([
        obs("visible smoke"),
        obs("steam or fog"),
        obs("steam or fog"),
      ]),
      flagged([obs("visible flame"), obs("indeterminate")]),
      flagged([obs("no hazard visible")]),
      flagged([obs("flame-like lighting"), obs("obscured or distant hazard")]),
    ]),
    {
      ...zero(),
      total: 8,
      visibleSmoke: 1,
      visibleFlame: 1,
      steamOrFog: 2,
      flameLikeLighting: 1,
      obscuredOrDistant: 1,
      noHazard: 1,
      indeterminate: 1,
    },
  );
});

test("review by observation category: observations on the response itself count, like ONEOFONE-7", () => {
  const entry = {
    status: "ok",
    product: "ignis",
    response: {
      observations: [obs("visible smoke")],
      assessment: { requires_human_review: true },
    },
  };
  assert.deepEqual(ignisReviewByObservationCategory([entry]), {
    ...zero(),
    total: 1,
    visibleSmoke: 1,
  });
});

test("review by observation category: unusable or non-contract categories count in the total only", () => {
  assert.deepEqual(
    ignisReviewByObservationCategory([
      flagged([obs("visible smoke"), obs("not a contract category"), obs(undefined), obs(null), {}]),
    ]),
    {
      ...zero(),
      total: 5,
      visibleSmoke: 1,
    },
  );
});

test("review by observation category: a flagged entry with no observations array contributes nothing", () => {
  assert.deepEqual(
    ignisReviewByObservationCategory([
      flagged(undefined),
      flagged(null),
      flagged("not an array"),
      flagged([obs("visible smoke")]),
    ]),
    {
      ...zero(),
      total: 1,
      visibleSmoke: 1,
    },
  );
});

test("review by observation category: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByObservationCategory([
    flagged([obs("visible smoke")], {
      response: { assessment: { requires_human_review: false, observations: [obs("visible smoke")] } },
    }),
    flagged([obs("visible smoke")], {
      response: { assessment: { observations: [obs("visible smoke")] } },
    }),
    flagged([obs("visible smoke")], { status: "network_error" }),
    flagged([obs("visible smoke")], { product: "vigiles" }),
    flagged([obs("visible smoke")], { product: "medicus" }),
    flagged([obs("visible smoke")]),
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    total: 1,
    visibleSmoke: 1,
  });
});

test("review by observation category: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-observation-category"'));
  assert.ok(html.includes("ignis-review-observation-category-panel"));
  assert.ok(css.includes(".ignis-review-observation-category-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-observation-category-panel'));
  assert.ok(app.includes("ignisReviewByObservationCategory"));
  assert.ok(app.includes('ignisReviewObservationCategory: $("ignis-review-observation-category")'));
  assert.ok(app.includes("els.ignisReviewObservationCategory.textContent"));
});
