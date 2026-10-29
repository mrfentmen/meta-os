// Node built-in test runner, no dependencies:
//   node --test tests/native-input-ready-announcement.test.mjs
//
// Web <-> native input-ready announcement parity. The web frontend's
// image-state and video-state lines are polite, atomic live regions, so
// choosing a file reads its "ready" line aloud there the moment it is
// set — and the web still-image read failure is a live-region change
// too. The native app already announced the still-image read failure
// (inputError), but a successfully chosen image or video only set its
// panel's ready text silently: a VoiceOver user who had just picked a
// file heard nothing confirming the Assess button was now enabled.
// The native app now announces both ready lines, in the panels' own
// words. Clearing an input deliberately stays silent: the user tapped
// Clear themselves, and nothing new becomes possible.
// This test reads the Swift sources (it cannot run Swift in this sandbox)
// to assert the announcements exist and are called from both choice paths.

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
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const webHtml = readFileSync(new URL("../index.html", import.meta.url), "utf8");

const slice = (from, to) => model.slice(model.indexOf(from), model.indexOf(to));
const chooseStillImage = slice("func chooseStillImage()", "func assessStillImage()");
const chooseVideo = slice("func chooseVideo()", "func assessVideoFrame()");
const clearStillImage = slice("func clearStillImage()", "// MARK: - Prerecorded-video input");
const clearVideo = slice("func clearVideo()", "/// Frames are downscaled");
const inputReadyFn = announcement.slice(announcement.indexOf("static func inputReady("));

const stillReady = "Image ready: ";
const videoReady = "Video ready: ";

test("web anchor: the image-state and video-state lines are polite, atomic live regions that read their ready lines aloud", () => {
  assert.match(webHtml, /id="image-state"[^>]*aria-live="polite"[^>]*aria-atomic="true"/);
  assert.match(webHtml, /id="video-state"[^>]*aria-live="polite"[^>]*aria-atomic="true"/);
  assert.ok(web.includes("Image ready: "), "web never sets an image ready line");
  assert.ok(web.includes("Video ready: "), "web never sets a video ready line");
});

test("native: AccessibilityAnnouncement has an inputReady that posts the message verbatim", () => {
  assert.ok(
    announcement.includes("static func inputReady(_ message: String)"),
    "AccessibilityAnnouncement is missing inputReady",
  );
  assert.ok(inputReadyFn.includes("post(message)"), "inputReady does not post verbatim");
  assert.ok(!inputReadyFn.includes("Model backend not connected"), "inputReady must not prefix a backend message");
  assert.ok(!inputReadyFn.includes("capture failed"), "inputReady must not describe a chosen file as a capture failure");
});

test("native: a successfully chosen still image announces the panel's own ready words", () => {
  assert.ok(
    chooseStillImage.includes(
      "AccessibilityAnnouncement.inputReady(\"Image ready: \\(url.lastPathComponent). Tap “Assess this image” to send it once.\")",
    ),
    "chooseStillImage never announces its ready line",
  );
  assert.ok(
    contentView.includes("Image ready: \\(name). Tap “Assess this image” to send it once."),
    "announced still-image words differ from the panel's on-screen ready text",
  );
  assert.ok(!chooseStillImage.includes("AccessibilityAnnouncement.backendFailure"), "ready path must not announce a backend failure");
  assert.ok(!chooseStillImage.includes("AccessibilityAnnouncement.captureFailure"), "ready path must not announce a capture failure");
});

test("native: a successfully chosen video announces the panel's own ready words", () => {
  assert.ok(
    chooseVideo.includes(
      "AccessibilityAnnouncement.inputReady(\"Video ready: \\(url.lastPathComponent). Play it, pause on the frame you want assessed, and tap “Assess this frame”. Only that frame is sent; the video is not stored by this app.\")",
    ),
    "chooseVideo never announces its ready line",
  );
  assert.ok(
    contentView.includes("Video ready: \\(name). Play it, pause on the frame you want assessed, and tap “Assess this frame”. Only that frame is sent; the video is not stored by this app."),
    "announced video words differ from the panel's on-screen ready text",
  );
  assert.ok(!chooseVideo.includes("AccessibilityAnnouncement.backendFailure"), "ready path must not announce a backend failure");
  assert.ok(!chooseVideo.includes("AccessibilityAnnouncement.captureFailure"), "ready path must not announce a capture failure");
});

test("native: clearing an input stays silent — no announcement from either Clear path", () => {
  assert.ok(!clearStillImage.includes("AccessibilityAnnouncement."), "clearStillImage must not announce");
  assert.ok(!clearVideo.includes("AccessibilityAnnouncement."), "clearVideo must not announce");
});
