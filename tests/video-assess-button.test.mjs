// Node built-in test runner, no dependencies:
//   node --test tests/video-assess-button.test.mjs
//
// Video Assess button readiness. Choosing a prerecorded-video file
// creates its object URL at once, but the video has no frame to capture
// until its metadata loads — and the panel's own comment has always
// said the button stays disabled until then. Every place that
// re-enabled the button tested only the URL, so two interleavings
// broke the promise: a video chosen while a request was out came back
// enabled from the request's settle path before its metadata loaded
// (a tap then failed capture on a frameless video), and metadata
// arriving for that mid-request video enabled the button under the
// request (a tap was then silently dropped by the assessing guard).
// One helper now owns the button: enabled only with a URL, loaded
// metadata, and no assessment in flight. No browser exists in this
// suite, so these are static checks on the shipped wiring, in the same
// style as the other Agent 1 tests. The still-image panel needs no
// equivalent: its data URL is null while a read is in flight, so its
// settle path already enables only a truly ready image. Native needs
// no change: its Assess button is already gated on assessing, and a
// not-ready native player fails extraction with the real error.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(
  new URL("../js/app.js", import.meta.url),
  "utf8",
);

const videoSection = app.slice(app.indexOf("let videoObjectUrl = null;"));

test("video: one helper owns the Assess button, requiring a URL, loaded metadata, and no assessment in flight", () => {
  assert.match(
    videoSection,
    /function refreshVideoAssessButton\(\) \{\s*els\.btnVideoAssess\.disabled = !videoObjectUrl \|\| !videoMetadataLoaded \|\| videoAssessing;\s*\}/,
  );
});

test("video: no settle or event path re-enables the button directly, bypassing the helper", () => {
  // Full assignments only: the helper line itself starts with the same
  // prefix, so the semicolon terminator is what separates a direct
  // re-enable from the helper's three-condition assignment.
  assert.doesNotMatch(videoSection, /btnVideoAssess\.disabled = !videoObjectUrl;/);
  assert.doesNotMatch(videoSection, /btnVideoAssess\.disabled = false;/);
  assert.doesNotMatch(videoSection, /btnVideoAssess\.disabled = true;/);
});

test("video: Clear (and therefore Reset and a new choice) resets the metadata flag before refreshing", () => {
  const clearBody = videoSection.slice(
    videoSection.indexOf("function clearVideoInput() {"),
    videoSection.indexOf("els.btnVideoClear.addEventListener"),
  );
  const flagAt = clearBody.indexOf("videoMetadataLoaded = false;");
  const refreshAt = clearBody.indexOf("refreshVideoAssessButton();");
  assert.notEqual(flagAt, -1, "clearVideoInput is missing its metadata-flag reset");
  assert.ok(flagAt < refreshAt, "the flag must reset before the button refreshes");
});

test("video: loadedmetadata sets the flag and refreshes, so a mid-request arrival cannot enable the button under the request", () => {
  const loadedBody = videoSection.slice(
    videoSection.indexOf('addEventListener("loadedmetadata"'),
    videoSection.indexOf('addEventListener("error"'),
  );
  const flagAt = loadedBody.indexOf("videoMetadataLoaded = true;");
  const refreshAt = loadedBody.indexOf("refreshVideoAssessButton();");
  assert.notEqual(flagAt, -1, "loadedmetadata is missing its flag set");
  assert.ok(flagAt < refreshAt, "the flag must set before the button refreshes");
});

test("video: a playback error clears the flag and refreshes, so a failed video never stays enabled", () => {
  const errorBody = videoSection.slice(
    videoSection.indexOf('els.videoPreview.addEventListener("error"'),
    videoSection.indexOf('els.btnVideoAssess.addEventListener("click"'),
  );
  assert.match(errorBody, /videoMetadataLoaded = false;\s*refreshVideoAssessButton\(\);/);
});

test("video: the Assess tap itself is guarded on metadata, not just on a URL and the assessing flag", () => {
  const clickBody = videoSection.slice(
    videoSection.indexOf('els.btnVideoAssess.addEventListener("click"'),
  );
  assert.match(
    clickBody,
    /if \(!videoObjectUrl \|\| !videoMetadataLoaded \|\| videoAssessing\) return;/,
  );
});

test("video: both settle paths — capture failure and request settle — refresh instead of re-enabling directly", () => {
  const clickBody = videoSection.slice(
    videoSection.indexOf('els.btnVideoAssess.addEventListener("click"'),
  );
  const refreshCount = (clickBody.match(/refreshVideoAssessButton\(\);/g) || []).length;
  // Tap (disable), capture-failure return, and request-settle finally.
  assert.ok(
    refreshCount >= 3,
    `expected at least 3 refresh calls in the Assess handler, found ${refreshCount}`,
  );
});
