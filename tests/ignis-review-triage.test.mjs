// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-triage.test.mjs
//
// IGNIS-ONEOFONE-6 (Del's one-of-one bar, Oct 29): the Ignis
// review-triage panel counts flagged-for-review Ignis assessments by
// the category they themselves carried — the flagged queue from
// ONEOFONE-3 split by ONEOFONE-1's contract classes. Real state
// only: clear and unknown-flag entries are not awaiting review and
// move no bucket, failures contribute nothing, other products move
// no bucket, and an empty or held session reads all zeros rather
// than inventing a queue. A flagged entry with no usable category
// still counts in the total. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewTriage } from "../js/ignis-review-triage.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const flagged = (category) => ({
  status: "ok",
  product: "ignis",
  response: { assessment: { requires_human_review: true, category } },
});
const unflagged = (flag, category) => ({
  status: "ok",
  product: "ignis",
  response: { assessment: { requires_human_review: flag, category } },
});

const zero = {
  total: 0,
  visibleSmoke: 0,
  visibleFlame: 0,
  steamOrFog: 0,
  flameLikeLighting: 0,
  obscuredOrDistant: 0,
  noHazard: 0,
  indeterminate: 0,
};

test("review triage: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewTriage([]), zero);
  assert.deepEqual(ignisReviewTriage(null), zero);
  assert.deepEqual(ignisReviewTriage(undefined), zero);
});

test("review triage: buckets follow the flagged assessments' own categories", () => {
  const counts = ignisReviewTriage([
    flagged("visible smoke"),
    flagged("visible smoke"),
    flagged("visible flame"),
    flagged("steam or fog"),
    flagged("flame-like lighting"),
    flagged("obscured or distant hazard"),
    flagged("no hazard visible"),
    flagged("indeterminate"),
    flagged("not a contract category"),
    flagged(null),
    flagged(undefined),
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: true } } },
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: true, category: 42 } } },
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: true } } },
    { status: "ok", product: "ignis", response: null },
    { status: "ok", product: "ignis" },
  ]);
  assert.deepEqual(counts, {
    total: 14,
    visibleSmoke: 2,
    visibleFlame: 1,
    steamOrFog: 1,
    flameLikeLighting: 1,
    obscuredOrDistant: 1,
    noHazard: 1,
    indeterminate: 1,
  });
});

test("review triage: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewTriage([
    unflagged(false, "visible smoke"),
    unflagged(null, "visible smoke"),
    unflagged("yes", "visible smoke"),
    { status: "ok", product: "ignis", response: { assessment: { category: "visible smoke" } } },
    { status: "failed", product: "ignis", response: { assessment: { requires_human_review: true, category: "visible smoke" } } },
    { status: "network_error", product: "ignis", response: { assessment: { requires_human_review: true, category: "visible smoke" } } },
    { status: "ok", product: "vigiles", response: { assessment: { requires_human_review: true, category: "visible smoke" } } },
    { status: "ok", product: "sanitas", response: { assessment: { requires_human_review: true, category: "visible smoke" } } },
    flagged("visible smoke"),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    visibleSmoke: 1,
    visibleFlame: 0,
    steamOrFog: 0,
    flameLikeLighting: 0,
    obscuredOrDistant: 0,
    noHazard: 0,
    indeterminate: 0,
  });
});

test("review triage: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-review-triage"'));
  assert.ok(html.includes("ignis-review-triage-panel"));
  assert.ok(css.includes(".ignis-review-triage-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-triage-panel'));
  assert.ok(app.includes("ignisReviewTriage"));
  assert.ok(app.includes("els.ignisReviewTriage.textContent"));
});
