// Node built-in test runner, no dependencies:
//   node --test tests/ignis-model-attribution.test.mjs
//
// IGNIS-ONEOFONE-8 (Del's one-of-one bar, Oct 29): the Ignis
// model-attribution breakdown counts recorded ok Ignis assessments
// by the model string each assessment itself reported in
// response.processing.model. Real state only: failures contribute
// nothing, other products move no bucket, assessments with no
// usable model string count in the total and in unattributed, and
// an empty or held session reads all zeros rather than inventing
// attributions. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisModelAttribution } from "../js/ignis-model-attribution.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const entryWithModel = (model) => ({
  status: "ok",
  product: "ignis",
  response: { processing: { model } },
});
const entryWithoutProcessing = () => ({
  status: "ok",
  product: "ignis",
  response: {},
});
const entryWithoutResponse = () => ({
  status: "ok",
  product: "ignis",
});

test("model attribution: an empty session reads all zeros", () => {
  assert.deepEqual(ignisModelAttribution([]), {
    total: 0,
    unattributed: 0,
    byModel: {},
  });
  assert.deepEqual(ignisModelAttribution(null), {
    total: 0,
    unattributed: 0,
    byModel: {},
  });
  assert.deepEqual(ignisModelAttribution(undefined), {
    total: 0,
    unattributed: 0,
    byModel: {},
  });
});

test("model attribution: buckets follow the assessments' own reported models", () => {
  const counts = ignisModelAttribution([
    entryWithModel("spark-vision-1"),
    entryWithModel("spark-vision-1"),
    entryWithModel("spark-vision-2"),
    entryWithoutProcessing(),
    entryWithoutResponse(),
    { status: "ok", product: "ignis", response: { processing: { model: "" } } },
    { status: "ok", product: "ignis", response: { processing: { model: 42 } } },
    { status: "ok", product: "ignis", response: { processing: null } },
    { status: "ok", product: "ignis", response: null },
    null,
  ]);
  assert.deepEqual(counts, {
    total: 9,
    unattributed: 6,
    byModel: { "spark-vision-1": 2, "spark-vision-2": 1 },
  });
});

test("model attribution: failed and other-product entries move no bucket", () => {
  const counts = ignisModelAttribution([
    { status: "failed", product: "ignis", response: { processing: { model: "spark-vision-1" } } },
    { status: "network_error", product: "ignis", response: { processing: { model: "spark-vision-1" } } },
    { status: "ok", product: "vigiles", response: { processing: { model: "spark-vision-1" } } },
    { status: "ok", product: "medicus", response: { processing: { model: "spark-vision-1" } } },
    null,
    entryWithModel("spark-vision-1"),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    unattributed: 0,
    byModel: { "spark-vision-1": 1 },
  });
});

test("model attribution: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-model-attribution"'));
  assert.ok(html.includes("ignis-model-attribution-panel"));
  assert.ok(css.includes(".ignis-model-attribution-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-model-attribution-panel'));
  assert.ok(app.includes("ignisModelAttribution"));
  assert.ok(app.includes("els.ignisModelAttribution.textContent"));
});
