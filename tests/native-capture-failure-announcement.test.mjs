// Node built-in test runner, no dependencies:
//   node --test tests/native-capture-failure-announcement.test.mjs
//
// Web <-> native capture-failure announcement parity. The web frontend's
// backend-status line is a polite live region, so a frame-capture failure
// (live sample or prerecorded-video frame) is read aloud there the moment
// its error status is set. The native app used to set the same error
// status silently: its status bar is not a live region, and only a new
// assessment or a backend failure was announced, so a VoiceOver user
// never heard that a tick or a frame extraction had failed. The native
// app now announces capture failures too, with their own message — a
// capture failure is not a backend failure, because no request was made,
// so it must never be announced as "Model backend not connected".
// This test reads the Swift sources (it cannot run Swift in this sandbox)
// to assert the announcement exists and is called from both capture paths.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const announcement = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/AccessibilityAnnouncement.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const webHtml = readFileSync(new URL("../index.html", import.meta.url), "utf8");

const runSample = model.slice(
  model.indexOf("private func runSample()"),
  model.indexOf("private func submitAssessment("),
);
const videoFrame = model.slice(
  model.indexOf("private func runVideoFrameAssessment("),
  model.indexOf("func clearVideo()"),
);
const captureFailureFn = announcement.slice(
  announcement.indexOf("static func captureFailure("),
);

test("web anchor: the backend-status line is a polite live region, so a capture failure set there is read aloud", () => {
  assert.match(webHtml, /id="backend-status"[^>]*aria-live="polite"/);
  assert.match(web, /setBackendStatus\("error", message\)/);
});

test("native: AccessibilityAnnouncement has a captureFailure that posts the message verbatim", () => {
  assert.match(announcement, /static func captureFailure\(message: String\)/);
  assert.match(captureFailureFn, /post\(message\)/);
  assert.doesNotMatch(captureFailureFn, /Model backend not connected/);
});

test("native: a live-sample capture failure announces, verbatim, instead of as a backend failure", () => {
  assert.match(runSample, /AccessibilityAnnouncement\.captureFailure\(message: message\)/);
  assert.doesNotMatch(runSample, /AccessibilityAnnouncement\.backendFailure/);
});

test("native: a video-frame extraction failure announces inside the view-generation guard, with the error on screen", () => {
  assert.match(
    videoFrame,
    /if generation == viewGeneration \{[\s\S]*?videoError = message[\s\S]*?backendStatus = \.error\(message\)[\s\S]*?AccessibilityAnnouncement\.captureFailure\(message: message\)[\s\S]*?timeline\.insert\(/,
  );
  assert.doesNotMatch(videoFrame, /AccessibilityAnnouncement\.backendFailure/);
});
