// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-source.test.mjs
//
// IGNIS-ONEOFONE-11 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by footage source counts only assessments already
// awaiting human review — recorded ok Ignis assessments whose
// assessment itself carried requires_human_review === true —
// split by the input source stamp each entry carried at submit
// time (live camera, still image, recorded video). Real state
// only: clear and unknown-flag entries move no bucket, failures
// and other products move no bucket, a flagged entry with no
// usable source stamp counts in the total and in unknownSource,
// and an empty or held session reads all zeros. The panel itself
// lives in index.html (hidden under Vigiles/Sanitas by styles.css)
// and is rendered from log.entries() inside updateLogStats in
// js/app.js. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewBySource } from "../js/ignis-review-source.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const flagged = (source) => ({
  status: "ok",
  product: "ignis",
  source,
  response: { assessment: { requires_human_review: true } },
});

test("review by source: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewBySource([]), {
    totalFlagged: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknownSource: 0,
  });
  assert.deepEqual(ignisReviewBySource(null), {
    totalFlagged: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknownSource: 0,
  });
  assert.deepEqual(ignisReviewBySource(undefined), {
    totalFlagged: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknownSource: 0,
  });
});

test("review by source: flagged assessments split by their recorded source stamp", () => {
  const counts = ignisReviewBySource([
    flagged("live-camera"),
    flagged("live-camera"),
    flagged("still-image"),
    flagged("recorded-video"),
    flagged("recorded-video"),
    flagged("recorded-video"),
    flagged(null),
    flagged(undefined),
    flagged(""),
    flagged(42),
    { status: "ok", product: "ignis", response: { assessment: { requires_human_review: true } } },
    null,
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 11,
    liveCamera: 2,
    stillImage: 1,
    recordedVideo: 3,
    unknownSource: 5,
  });
});

test("review by source: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewBySource([
    flagged("live-camera"),
    { status: "ok", product: "ignis", source: "live-camera", response: { assessment: { requires_human_review: false } } },
    { status: "ok", product: "ignis", source: "live-camera", response: { assessment: {} } },
    { status: "ok", product: "ignis", source: "live-camera" },
    { status: "failed", product: "ignis", source: "live-camera", response: { assessment: { requires_human_review: true } } },
    { status: "error", product: "ignis", source: "live-camera", response: { assessment: { requires_human_review: true } } },
    { status: "ok", product: "vigiles", source: "live-camera", response: { assessment: { requires_human_review: true } } },
    { status: "ok", product: "sanitas", source: "live-camera", response: { assessment: { requires_human_review: true } } },
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 1,
    liveCamera: 1,
    stillImage: 0,
    recordedVideo: 0,
    unknownSource: 0,
  });
});

test("review by source: panel exists, is Ignis-only, and app.js renders it", () => {
  assert.ok(
    html.includes('class="panel ignis-review-source-panel"'),
    "index.html carries the Ignis review-by-source panel",
  );
  assert.ok(
    html.includes('id="ignis-review-source"'),
    "index.html carries the review-by-source line element",
  );
  assert.ok(
    css.includes(".ignis-review-source-panel"),
    "styles.css carries the review-by-source visibility block",
  );
  assert.ok(
    css.includes('body[data-product="ignis"] .ignis-review-source-panel'),
    "panel shows only under Ignis",
  );
  assert.ok(
    app.includes('from "./ignis-review-source.js"'),
    "app.js imports the review-by-source module",
  );
  assert.ok(
    app.includes("ignisReviewBySource(log.entries())"),
    "updateLogStats renders from log entries",
  );
  assert.ok(
    app.includes('ignisReviewSource: $("ignis-review-source")'),
    "app.js wires the review-by-source line element",
  );
});
