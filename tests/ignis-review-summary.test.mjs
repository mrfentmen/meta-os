// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-summary.test.mjs
//
// IGNIS-ONEOFONE-21 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by summary completeness counts only the recorded
// ok Ignis assessments already awaiting human review —
// requires_human_review === true — bucketed by the summary the
// assessment itself carried: with summary (a string with
// non-whitespace content), empty summary (an empty or
// whitespace-only string), or unrecorded (no usable summary
// string at all). Real state only: clear and unknown-flag
// entries move no bucket, failures and other products move no
// bucket, a flagged entry with a missing, null, or non-string
// summary counts as unrecorded (never a silent empty), and an
// empty or held session reads all zeros. The panel itself lives
// in index.html (hidden under Vigiles/Medicus by styles.css)
// and is rendered from log.entries() inside updateLogStats in
// js/app.js. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewBySummary } from "../js/ignis-review-summary.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const zero = () => ({
  totalFlagged: 0,
  withSummary: 0,
  emptySummary: 0,
  unrecorded: 0,
});

const flagged = (summary, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: {
      requires_human_review: true,
      summary,
    },
  },
  ...overrides,
});

test("review by summary: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewBySummary([]), zero());
  assert.deepEqual(ignisReviewBySummary(null), zero());
  assert.deepEqual(ignisReviewBySummary(undefined), zero());
});

test("review by summary: flagged assessments bucket by their own summary", () => {
  assert.deepEqual(
    ignisReviewBySummary([
      flagged("Smoke visible above the roofline."),
      flagged("  Flame at the window.  "),
      flagged(""),
      flagged("   "),
      flagged("\n\t"),
    ]),
    {
      totalFlagged: 5,
      withSummary: 2,
      emptySummary: 3,
      unrecorded: 0,
    },
  );
});

test("review by summary: missing, null, and non-string summaries count as unrecorded, never empty", () => {
  assert.deepEqual(
    ignisReviewBySummary([
      flagged(null),
      flagged(undefined),
      flagged(42),
      flagged(true),
      flagged(["Smoke."]),
      {
        status: "ok",
        product: "ignis",
        response: { assessment: { requires_human_review: true } },
      },
      flagged("Readable summary."),
    ]),
    {
      ...zero(),
      totalFlagged: 7,
      withSummary: 1,
      unrecorded: 6,
    },
  );
});

test("review by summary: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewBySummary([
    flagged("Smoke.", {
      response: {
        assessment: { requires_human_review: false, summary: "Smoke." },
      },
    }),
    flagged("Smoke.", {
      response: { assessment: { summary: "Smoke." } },
    }),
    flagged("Smoke.", { status: "network_error" }),
    flagged("Smoke.", { product: "vigiles" }),
    flagged("Smoke.", { product: "medicus" }),
    flagged("Smoke."),
  ]);
  assert.deepEqual(counts, {
    ...zero(),
    totalFlagged: 1,
    withSummary: 1,
  });
});

test("review by summary: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-summary"'));
  assert.ok(html.includes("ignis-review-summary-panel"));
  assert.ok(css.includes(".ignis-review-summary-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-summary-panel'));
  assert.ok(app.includes("ignisReviewBySummary"));
  assert.ok(app.includes('ignisReviewSummary: $("ignis-review-summary")'));
  assert.ok(app.includes("els.ignisReviewSummary.textContent"));
});
