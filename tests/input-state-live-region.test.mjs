// Node built-in test runner, no dependencies:
//   node --test tests/input-state-live-region.test.mjs
//
// Web still-image and video state announcements. The image-state and
// video-state lines are the panels that carry the honest input
// outcomes — "That file is not an image", "Image ready: …", "Could not
// read that image: …", "That video could not be played in this
// browser", "Could not capture this frame: …" — and they used to be
// plain text with no live region, so a screen-reader user who had just
// chosen a file heard nothing about whether it was usable, while the
// web frontend's own camera-state, backend-status, backend-health, and
// latest-assessment lines are all aria-live="polite". They are now
// polite, atomic live regions, like camera-state: the whole sentence
// is read, not just the changed words. Both lines change only on a
// user action (choosing, clearing, or failing a file), never on a
// timer, so unlike the sampler-stats line there is no per-second spam
// risk in announcing them. The native side needs one change, not two:
// its video panel has no read-failure surface of its own (an
// unplayable video surfaces as a capture failure, which is already
// announced verbatim), but its still-image read failure set the error
// text silently, so a VoiceOver user heard nothing about why the
// Assess button stayed disabled — unlike the video-frame capture
// failure and the export failure, which are both announced. That
// failure is now announced verbatim through a helper of its own: it
// touches no backend and captures no frame, so neither backendFailure
// nor captureFailure describes it.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const model = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/ViewModels/AppModel.swift",
    import.meta.url,
  ),
  "utf8",
);
const announcements = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Services/AccessibilityAnnouncement.swift",
    import.meta.url,
  ),
  "utf8",
);

const imageStateTag = page.match(/<p id="image-state"[^>]*>/);
assert.ok(imageStateTag, "index.html is missing its image-state element");
const videoStateTag = page.match(/<p id="video-state"[^>]*>/);
assert.ok(videoStateTag, "index.html is missing its video-state element");

test("web: image-state is a polite, atomic live region", () => {
  assert.match(imageStateTag[0], /aria-live="polite"/);
  assert.match(imageStateTag[0], /aria-atomic="true"/);
});

test("web: video-state is a polite, atomic live region", () => {
  assert.match(videoStateTag[0], /aria-live="polite"/);
  assert.match(videoStateTag[0], /aria-atomic="true"/);
});

test("native: still-image read failure is announced verbatim", () => {
  const choose = model.match(
    /func chooseStillImage\(\) \{[\s\S]*?\n    \}/,
  );
  assert.ok(choose, "AppModel is missing chooseStillImage");
  assert.match(
    choose[0],
    /stillImageError = "Could not read that image as a JPEG\."/,
  );
  assert.match(
    choose[0],
    /AccessibilityAnnouncement\.inputError\("Could not read that image as a JPEG\."\)/,
  );
});

test("native: inputError posts verbatim, not as a backend or capture failure", () => {
  const helper = announcements.match(
    /static func inputError\(_ message: String\) \{[\s\S]*?\n    \}/,
  );
  assert.ok(helper, "AccessibilityAnnouncement is missing inputError");
  assert.match(helper[0], /post\(message\)/);
  assert.doesNotMatch(helper[0], /backendFailure|captureFailure/);
});
