// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-latency.test.mjs
//
// IGNIS-ONEOFONE-20 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by reported latency counts only the recorded
// ok Ignis assessments already awaiting human review —
// requires_human_review === true — bucketed by the
// server-reported processing latency the response itself
// carried: under one second, one to five seconds, five seconds
// or more, or unreported where no usable latency value exists
// to read. Real state only: clear and unknown-flag entries move
// no bucket, failures and other products move no bucket, a
// flagged entry with a null, missing, non-finite, or negative
// latency counts as unreported (never a silent zero), band
// boundaries fall on the slower side (exactly 1000 ms counts as
// one-to-five, exactly 5000 ms counts as five-or-more), and an
// empty or held session reads all zeros. The panel itself lives
// in index.html (hidden under Vigiles/Medicus by styles.css)
// and is rendered from log.entries() inside updateLogStats in
// js/app.js. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByLatency } from "../js/ignis-review-latency.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const zero = () => ({
  totalFlagged: 0,
  under1s: 0,
  oneTo5s: 0,
  fiveOrMore: 0,
  unreported: 0,
});

const flagged = (latencyMs, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: {
      requires_human_review: true,
    },
    processing: { model: "spark", latency_ms: latencyMs },
  },
  ...overrides,
});

test("review by latency: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByLatency([]), zero());
  assert.deepEqual(ignisReviewByLatency(null), zero());
  assert.deepEqual(ignisReviewByLatency(undefined), zero());
});

test("review by latency: flagged assessments bucket by their own reported latency", () => {
  assert.deepEqual(
    ignisReviewByLatency([
      flagged(0),
      flagged(999),
      flagged(1000),
      flagged(3000),
      flagged(4999),
      flagged(5000),
      flagged(10800),
    ]),
    {
      totalFlagged: 7,
      under1s: 2,
      oneTo5s: 3,
      fiveOrMore: 2,
      unreported: 0,
    },
  );
});

test("review by latency: null, missing, non-finite, and negative latencies count as unreported, never zero", () => {
  assert.deepEqual(
    ignisReviewByLatency([
      flagged(null),
      flagged(undefined),
      flagged("3000"),
      flagged(Number.NaN),
      flagged(Number.POSITIVE_INFINITY),
      flagged(-1),
      {
        status: "ok",
        product: "ignis",
        response: { assessment: { requires_human_review: true } },
      },
      {
        status: "ok",
        product: "ignis",
        response: {
          assessment: { requires_human_review: true },
          processing: { model: "spark" },
        },
      },
    ]),
    {
      ...zero(),
      totalFlagged: 8,
      unreported: 8,
    },
  );
});

test("review by latency: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByLatency([
    flagged(3000, {
      response: {
        assessment: { requires_human_review: false },
        processing: { model: "spark", latency_ms: 3000 },
      },
    }),
    flagged(3000, {
      response: {
        assessment: {},
        processing: { model: "spark", latency_ms: 3000 },
      },
    }),
    flagged(3000, { status: "network_error" }),
    flagged(3000, { product: "vigiles" }),
    flagged(3000, { product: "medicus" }),
    flagged(3000),
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    totalFlagged: 1,
    oneTo5s: 1,
  });
});

test("review by latency: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-latency"'));
  assert.ok(html.includes("ignis-review-latency-panel"));
  assert.ok(css.includes(".ignis-review-latency-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-latency-panel'));
  assert.ok(app.includes("ignisReviewByLatency"));
  assert.ok(app.includes('ignisReviewLatency: $("ignis-review-latency")'));
  assert.ok(app.includes("els.ignisReviewLatency.textContent"));
});
