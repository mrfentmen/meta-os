// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-audit-trail.test.mjs
//
// IGNIS-ONEOFONE-13 (Del's one-of-one bar, Oct 30): the Ignis
// review audit trail counts only assessments already awaiting
// human review — recorded ok Ignis assessments whose assessment
// itself carried requires_human_review === true — bucketed by how
// complete the provenance trail each entry itself carries is:
// request_timestamp, the reported processing.model, the supplied
// scenario_label, and the stamped input source. Real state only:
// clear and unknown-flag entries move no bucket, failures and
// other products move no bucket, a flagged entry with some fields
// missing counts as partial (never filled in), a flagged entry
// with none counts as no trail, and an empty or held session
// reads all zeros. The panel itself lives in index.html (hidden
// under Vigiles/Medicus by styles.css) and is rendered from
// log.entries() inside updateLogStats in js/app.js. No contract,
// server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewAuditTrail } from "../js/ignis-review-audit-trail.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const flagged = (overrides = {}) => ({
  status: "ok",
  product: "ignis",
  request_timestamp: "2026-10-30T02:00:00.000Z",
  scenario_label: "staged-smoke-01",
  source: "recorded-video",
  response: {
    assessment: { requires_human_review: true },
    processing: { model: "muse-spark-1.3" },
  },
  ...overrides,
});

test("review audit trail: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewAuditTrail([]), {
    totalFlagged: 0,
    fullTrail: 0,
    partialTrail: 0,
    noTrail: 0,
  });
  assert.deepEqual(ignisReviewAuditTrail(null), {
    totalFlagged: 0,
    fullTrail: 0,
    partialTrail: 0,
    noTrail: 0,
  });
  assert.deepEqual(ignisReviewAuditTrail(undefined), {
    totalFlagged: 0,
    fullTrail: 0,
    partialTrail: 0,
    noTrail: 0,
  });
});

test("review audit trail: a fully recorded flagged entry counts as full trail", () => {
  assert.deepEqual(ignisReviewAuditTrail([flagged()]), {
    totalFlagged: 1,
    fullTrail: 1,
    partialTrail: 0,
    noTrail: 0,
  });
});

test("review audit trail: missing fields demote full to partial, never invent", () => {
  const counts = ignisReviewAuditTrail([
    flagged({ request_timestamp: null }),
    flagged({ scenario_label: "" }),
    flagged({ source: "hand-typed" }),
    flagged({ response: { assessment: { requires_human_review: true }, processing: {} } }),
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 4,
    fullTrail: 0,
    partialTrail: 4,
    noTrail: 0,
  });
});

test("review audit trail: a flagged entry with no usable field counts as no trail", () => {
  assert.deepEqual(
    ignisReviewAuditTrail([
      flagged({
        request_timestamp: "",
        scenario_label: null,
        source: null,
        response: { assessment: { requires_human_review: true } },
      }),
    ]),
    {
      totalFlagged: 1,
      fullTrail: 0,
      partialTrail: 0,
      noTrail: 1,
    },
  );
});

test("review audit trail: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewAuditTrail([
    flagged({ response: { assessment: { requires_human_review: false }, processing: { model: "muse-spark-1.3" } } }),
    flagged({ response: { assessment: {}, processing: { model: "muse-spark-1.3" } } }),
    flagged({ status: "network_error" }),
    flagged({ product: "vigiles" }),
    flagged(),
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 1,
    fullTrail: 1,
    partialTrail: 0,
    noTrail: 0,
  });
});

test("review audit trail: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-audit-trail"'));
  assert.ok(html.includes("ignis-review-audit-trail-panel"));
  assert.ok(css.includes(".ignis-review-audit-trail-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-audit-trail-panel'));
  assert.ok(app.includes('ignisReviewAuditTrail'));
  assert.ok(app.includes('ignisReviewAuditTrail: $("ignis-review-audit-trail")'));
  assert.ok(app.includes("els.ignisReviewAuditTrail.textContent"));
});
