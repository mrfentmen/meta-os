// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-model.test.mjs
//
// IGNIS-ONEOFONE-12 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by model counts only assessments already awaiting
// human review — recorded ok Ignis assessments whose assessment
// itself carried requires_human_review === true — split by the
// model string each assessment itself reported in
// response.processing.model. Real state only: clear and
// unknown-flag entries move no bucket, failures and other
// products move no bucket, a flagged entry with no usable model
// string counts in the total and in unattributed, and an empty or
// held session reads all zeros. The panel itself lives in
// index.html (hidden under Vigiles/Medicus by styles.css) and is
// rendered from log.entries() inside updateLogStats in js/app.js.
// No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByModel } from "../js/ignis-review-model.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const flagged = (model) => ({
  status: "ok",
  product: "ignis",
  response: {
    assessment: { requires_human_review: true },
    processing: model === undefined ? undefined : { model },
  },
});

test("review by model: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByModel([]), {
    totalFlagged: 0,
    unattributed: 0,
    byModel: {},
  });
  assert.deepEqual(ignisReviewByModel(null), {
    totalFlagged: 0,
    unattributed: 0,
    byModel: {},
  });
  assert.deepEqual(ignisReviewByModel(undefined), {
    totalFlagged: 0,
    unattributed: 0,
    byModel: {},
  });
});

test("review by model: flagged assessments split by their reported model", () => {
  const counts = ignisReviewByModel([
    flagged("muse-spark-1.3"),
    flagged("muse-spark-1.3"),
    flagged("spark-vision-2"),
    flagged(null),
    flagged(undefined),
    flagged(""),
    flagged(42),
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: true } } },
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: true }, processing: {} } },
    null,
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 9,
    unattributed: 6,
    byModel: { "muse-spark-1.3": 2, "spark-vision-2": 1 },
  });
});

test("review by model: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByModel([
    flagged("muse-spark-1.3"),
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: false }, processing: { model: "muse-spark-1.3" } } },
    { status: "ok", product: "ignis", response: { assessment: {}, processing: { model: "muse-spark-1.3" } } },
    { status: "ok", product: "ignis", response: { processing: { model: "muse-spark-1.3" } } },
    { status: "failed", product: "ignis", response: { assessment: { requires_human_review: true }, processing: { model: "muse-spark-1.3" } } },
    { status: "error", product: "ignis", response: { assessment: { requires_human_review: true }, processing: { model: "muse-spark-1.3" } } },
    { status: "ok", product: "vigiles", response: { assessment: { requires_human_review: true }, processing: { model: "muse-spark-1.3" } } },
    { status: "ok", product: "medicus", response: { assessment: { requires_human_review: true }, processing: { model: "muse-spark-1.3" } } },
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 1,
    unattributed: 0,
    byModel: { "muse-spark-1.3": 1 },
  });
});

test("review by model: panel exists, is Ignis-only, and app.js renders it", () => {
  assert.ok(
    html.includes('class="panel ignis-review-model-panel"'),
    "index.html carries the Ignis review-by-model panel",
  );
  assert.ok(
    html.includes('id="ignis-review-model"'),
    "index.html carries the review-by-model line element",
  );
  assert.ok(
    css.includes(".ignis-review-model-panel"),
    "styles.css carries the review-by-model visibility block",
  );
  assert.ok(
    css.includes('body[data-product="ignis"] .ignis-review-model-panel'),
    "panel shows only under Ignis",
  );
  assert.ok(
    app.includes('from "./ignis-review-model.js"'),
    "app.js imports the review-by-model module",
  );
  assert.ok(
    app.includes("ignisReviewByModel(log.entries())"),
    "updateLogStats renders from log entries",
  );
  assert.ok(
    app.includes('ignisReviewModel: $("ignis-review-model")'),
    "app.js wires the review-by-model line element",
  );
});
