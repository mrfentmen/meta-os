// Node built-in test runner, no dependencies:
//   node --test tests/native-request-product.test.mjs
//
// Web <-> native request-product parity. The web frontend (js/app.js)
// captures the product when a sample starts or an Assess button is
// tapped and passes it to submitAssessment, so switching products
// while a request is in flight cannot relabel that request's log and
// history entries. The native app used to read selectedProduct after
// the request returned, so a mid-request switch mislabelled the entry.
// This test reads AppModel.swift (it cannot run Swift in this sandbox)
// to assert the product is captured before any await and threaded
// through to the client call, the session log, and the timeline.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

test("web: submitAssessment takes the product as a parameter, captured at sample/tap time", () => {
  assert.match(web, /async function submitAssessment\(product, timestamp, image, scenarioLabel\)/);
  assert.match(web, /const product = currentProductId;\n  const timestamp = new Date\(\)\.toISOString\(\)/);
});

test("native: submitAssessment takes the product as a parameter", () => {
  assert.match(
    model,
    /private func submitAssessment\(product: ProductID, timestamp: String, imageDataURL: String, scenarioLabel: String\?\)/,
  );
});

test("native: live sample captures the product before capture, still/video capture it at tap time", () => {
  const sample = model.slice(
    model.indexOf("private func runSample()"),
    model.indexOf("try await submitAssessment(product: requestProduct"),
  );
  assert.match(sample, /let requestProduct = selectedProduct/);
  assert.match(
    model,
    /func assessStillImage\(\) \{[\s\S]*?let requestProduct = selectedProduct[\s\S]*?runStillImageAssessment\(dataURL: dataURL, product: requestProduct, scenarioLabel: requestScenarioLabel\)/,
  );
  assert.match(
    model,
    /func assessVideoFrame\(\) \{[\s\S]*?let requestProduct = selectedProduct[\s\S]*?runVideoFrameAssessment\(url: url, seconds: seconds, product: requestProduct, scenarioLabel: requestScenarioLabel\)/,
  );
});

test("native: after the await, the request product (never selectedProduct) labels the client call, log, and timeline", () => {
  const submit = model.slice(
    model.indexOf("private func submitAssessment("),
    model.indexOf("private func recordLog("),
  );
  assert.match(submit, /product: product,\n                timestamp: timestamp/);
  assert.match(submit, /recordLog\(product: product,/);
  assert.match(submit, /TimelineItem\(product: product,/);
  assert.match(submit, /productDisplayName: product\.config\.displayName/);
  assert.doesNotMatch(submit, /selectedProduct/);
});

test("native: recordLog threads its product parameter into the session log", () => {
  const record = model.slice(model.indexOf("private func recordLog("));
  assert.match(record, /product: ProductID,/);
  assert.match(record, /product: product,/);
});

test("native: no submit-path call site still labels an entry with selectedProduct", () => {
  assert.doesNotMatch(model, /TimelineItem\(product: selectedProduct/);
  assert.doesNotMatch(model, /recordLog\(timestamp:/);
  assert.doesNotMatch(model, /submitAssessment\(timestamp:/);
});
