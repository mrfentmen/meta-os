// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-queue.test.mjs
//
// IGNIS-ONEOFONE-3 (Del's one-of-one bar, Oct 29): the Ignis
// duty-officer review queue counts recorded Ignis assessments by
// the requires_human_review flag the assessment itself carried —
// flagged, clear, or unknown when the flag is missing or not a
// boolean. Real state only: failures contribute nothing, other
// products move no bucket, and an empty or held session reads all
// zeros rather than inventing a queue. The queue never flags
// anything itself and never notifies anyone. No contract, server,
// or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewQueue } from "../js/ignis-review-queue.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const ok = (product, assessment) => ({
  status: "ok",
  product,
  response: { assessment },
});

const zero = {
  total: 0,
  flagged: 0,
  clear: 0,
  unknown: 0,
};

test("review queue: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewQueue([]), zero);
  assert.deepEqual(ignisReviewQueue(null), zero);
  assert.deepEqual(ignisReviewQueue(undefined), zero);
});

test("review queue: flagged, clear, and unknown follow the flag itself", () => {
  const counts = ignisReviewQueue([
    ok("ignis", { requires_human_review: true }),
    ok("ignis", { requires_human_review: true }),
    ok("ignis", { requires_human_review: false }),
    ok("ignis", {}),
    ok("ignis", { requires_human_review: "yes" }),
    ok("ignis", { requires_human_review: null }),
    ok("ignis", null),
    { status: "ok", product: "ignis" },
  ]);
  assert.deepEqual(counts, {
    total: 8,
    flagged: 2,
    clear: 1,
    unknown: 5,
  });
});

test("review queue: failures and other products move no bucket", () => {
  const counts = ignisReviewQueue([
    { status: "failed", product: "ignis", response: { assessment: { requires_human_review: true } } },
    ok("vigiles", { requires_human_review: true }),
    ok("sanitas", { requires_human_review: false }),
    ok("ignis", { requires_human_review: false }),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    flagged: 0,
    clear: 1,
    unknown: 0,
  });
});

test("review queue: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-review-queue"'));
  assert.ok(html.includes("ignis-review-queue-panel"));
  assert.ok(css.includes(".ignis-review-queue-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-queue-panel'));
  assert.ok(app.includes("ignisReviewQueue"));
  assert.ok(app.includes("els.ignisReviewQueue.textContent"));
});
