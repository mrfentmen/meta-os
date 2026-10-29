// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-failure-announcement.test.mjs
//
// Web <-> native camera-failure announcement parity. The web frontend's
// camera-state line is a polite live region, so a permission denial, a
// missing camera, or a failed start is read aloud there the moment its
// error text is set. The native app used to set the same state text
// silently: its preview carries the state only as an accessibilityValue,
// which speaks when navigated to, never on change, so a VoiceOver user
// who had just tapped Start Camera heard nothing about why no preview
// went live. The native app now announces camera failure states too,
// in the panel's own state-text words — a camera that never started
// touches no backend and sends no frame, so it must never be announced
// as a backend or capture failure. This test reads the Swift sources
// (it cannot run Swift in this sandbox) to assert the announcement
// exists, is wired into the single state funnel every failure path
// uses, and stays silent for non-failure states.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const camera = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/CameraService.swift", import.meta.url),
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

const cameraFailureFn = announcement.slice(
  announcement.indexOf("static func cameraFailure("),
);
const setStateFn = camera.slice(camera.indexOf("private func setState("));

test("web anchor: the camera-state line is a polite live region, so a camera failure set there is read aloud", () => {
  assert.match(webHtml, /id="camera-state"[^>]*aria-live="polite"/);
  assert.match(web, /setCameraState\(describeCameraError\(err\)\)/);
});

test("native: AccessibilityAnnouncement has a cameraFailure that posts the message verbatim", () => {
  assert.match(announcement, /static func cameraFailure\(_ message: String\)/);
  assert.match(cameraFailureFn, /post\(message\)/);
  assert.doesNotMatch(cameraFailureFn, /Model backend not connected/);
  assert.doesNotMatch(cameraFailureFn, /Frame capture failed/);
});

test("native: setState announces all three failure states in the panel's own words", () => {
  assert.match(
    setStateFn,
    /case \.denied:\s*return "Camera permission denied\. Grant access in System Settings → Privacy & Security → Camera, then start the camera again\."/,
  );
  assert.match(setStateFn, /case \.noCamera:\s*return "No camera was found on this Mac\."/);
  assert.match(setStateFn, /case \.failed\(let message\):\s*return "Camera error: \\\(message\)"/);
  assert.match(setStateFn, /AccessibilityAnnouncement\.cameraFailure\(failureMessage\)/);
  assert.doesNotMatch(setStateFn, /AccessibilityAnnouncement\.backendFailure/);
  assert.doesNotMatch(setStateFn, /AccessibilityAnnouncement\.captureFailure/);
});

test("native: the announced words are exactly the state text the panel shows", () => {
  assert.match(
    contentView,
    /Text\("Camera permission denied\. Grant access in System Settings → Privacy & Security → Camera, then start the camera again\."\)/,
  );
  assert.match(contentView, /Text\("No camera was found on this Mac\."\)/);
  assert.match(contentView, /Text\("Camera error: \\\(message\)"\)/);
});

test("native: non-failure states announce nothing", () => {
  assert.match(setStateFn, /default:\s*return nil/);
  assert.doesNotMatch(setStateFn, /case \.running:/);
  assert.doesNotMatch(setStateFn, /case \.stopped:/);
  assert.doesNotMatch(setStateFn, /case \.requestingPermission:/);
});
