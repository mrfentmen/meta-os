// Node built-in test runner, no dependencies:
//   node --test tests/request-scenario.test.mjs
//
// Web <-> native request-scenario parity. The web frontend (js/app.js)
// used to read the scenario label when a request settled, so a scenario
// change made while a request was in flight relabelled that request's
// session-log entry with ground truth it was never assessed under —
// the same flaw the request-product fix closed for the product, which
// is captured at sample or tap time. The native app had the same flaw:
// recordLog read currentScenarioLabel at record time, after the await.
// Both sides now capture the label at sample or tap time and thread it
// through to the log. This test reads app.js and AppModel.swift (it
// cannot run Swift in this sandbox) to assert the capture-before-await
// wiring on every submit path: live sample, still image, video frame,
// and both capture-failure paths.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

test("web: submitAssessment takes the scenario label as a parameter, captured at sample/tap time", () => {
  assert.match(web, /async function submitAssessment\(product, timestamp, image, scenarioLabel, source\)/);
  // Success and failure log entries use the parameter, never a fresh read.
  assert.match(web, /status: "ok",\n\s+response: assessment,\n\s+scenarioLabel,/);
  assert.match(web, /status,\n\s+error: err\.message,\n\s+scenarioLabel,/);
  assert.doesNotMatch(web, /scenarioLabel: currentScenarioLabel\(\),/);
  // Live sample captures the label before capture, beside the product.
  assert.match(
    web,
    /async function runSample\(\) \{\n\s+const product = currentProductId;\n\s+const timestamp = new Date\(\)\.toISOString\(\);\n\s+\/\/ Captured with the product, before any capture or request: a\n\s+\/\/ scenario change mid-sample must not relabel this sample's entry\.\n\s+const scenarioLabel = currentScenarioLabel\(\);/,
  );
  assert.match(web, /await submitAssessment\(product, timestamp, image, scenarioLabel, "live-camera"\);/);
  // Still-image and video handlers capture at tap time and pass it on.
  assert.match(web, /await submitAssessment\(currentProductId, new Date\(\)\.toISOString\(\), stillImageDataUrl, scenarioLabel, "still-image"\);/);
  assert.match(web, /await submitAssessment\(currentProductId, timestamp, image, scenarioLabel, "recorded-video"\);/);
});

test("native: submitAssessment takes the scenario label as a parameter", () => {
  assert.match(
    model,
    /private func submitAssessment\(product: ProductID, timestamp: String, imageDataURL: String, scenarioLabel: String\?, generation: Int\)/,
  );
});

test("native: live sample, still image, and video capture the label before any await", () => {
  const sample = model.slice(
    model.indexOf("private func runSample()"),
    model.indexOf("try await submitAssessment(product: requestProduct"),
  );
  assert.match(sample, /let requestScenarioLabel = currentScenarioLabel/);
  assert.match(
    model,
    /func assessStillImage\(\) \{[\s\S]*?let requestScenarioLabel = currentScenarioLabel[\s\S]*?runStillImageAssessment\(dataURL: dataURL, product: requestProduct, scenarioLabel: requestScenarioLabel, generation: requestGeneration\)/,
  );
  assert.match(
    model,
    /func assessVideoFrame\(\) \{[\s\S]*?let requestScenarioLabel = currentScenarioLabel[\s\S]*?runVideoFrameAssessment\(url: url, seconds: seconds, product: requestProduct, scenarioLabel: requestScenarioLabel, generation: requestGeneration\)/,
  );
});

test("native: after the await, the captured label (never a fresh read) labels the log", () => {
  const submit = model.slice(
    model.indexOf("private func submitAssessment("),
    model.indexOf("private func recordLog("),
  );
  assert.match(submit, /recordLog\(product: product, timestamp: timestamp, latencyMs: latencyMs, status: \.ok, response: response, scenarioLabel: scenarioLabel\)/);
  assert.match(submit, /recordLog\(product: product, timestamp: timestamp, latencyMs: error\.latencyMs, status: status, error: error\.message, scenarioLabel: scenarioLabel\)/);
  assert.doesNotMatch(submit, /currentScenarioLabel/);
  // Capture-failure paths log the captured label too.
  assert.match(model, /recordLog\(product: requestProduct, timestamp: timestamp, latencyMs: nil, status: \.invalidResponse, error: message, scenarioLabel: requestScenarioLabel\)/);
  assert.match(model, /recordLog\(product: product, timestamp: timestamp, latencyMs: nil, status: \.invalidResponse, error: message, scenarioLabel: scenarioLabel\)/);
});

test("native: recordLog threads its scenario parameter into the session log, with no silent default", () => {
  const record = model.slice(model.indexOf("private func recordLog("));
  assert.match(record, /scenarioLabel: String\?\n\s+\) \{/);
  assert.match(record, /scenarioLabel: scenarioLabel/);
  assert.doesNotMatch(record, /currentScenarioLabel/);
});

test("native: no submit-path call site still reads the label after an await", () => {
  assert.doesNotMatch(model, /recordLog\(timestamp:/);
  assert.doesNotMatch(model, /submitAssessment\(timestamp:/);
  assert.doesNotMatch(model, /submitAssessment\(product: product, timestamp: ISO8601\.now\(\), imageDataURL: dataURL\)/);
  assert.doesNotMatch(model, /submitAssessment\(product: requestProduct, timestamp: timestamp, imageDataURL: image\)/);
});
