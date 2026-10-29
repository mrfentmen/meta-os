// Node built-in test runner, no dependencies:
//   node --test tests/camera-state-live-region.test.mjs
//
// Web camera-state announcements. The camera-state line is the panel
// that carries the honest camera errors — permission denied, camera
// busy in another app, no camera API — and it is the line that changes
// on every camera transition (off, waiting for permission, live,
// stopped, reset). It used to be plain text with no live region, so a
// screen-reader user heard nothing when the camera state changed: the
// web frontend's own backend-status, backend-health, and
// latest-assessment lines are all aria-live="polite", and the native
// preview carries the same camera state as its accessibilityValue, so
// the camera line was the one state surface that stayed silent. It is
// now a polite live region, atomic so the whole sentence is read, not
// just the changed words. The sampler-stats line is deliberately NOT a
// live region: its counters move on every tick, and announcing them
// would spam the user once a second for the whole run.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const view = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const cameraStateTag = page.match(/<p id="camera-state"[^>]*>/);
assert.ok(cameraStateTag, "index.html is missing its camera-state element");

test("web: camera-state is a polite, atomic live region", () => {
  assert.match(cameraStateTag[0], /aria-live="polite"/);
  assert.match(cameraStateTag[0], /aria-atomic="true"/);
});

test("web: sampler-stats stays out of the live regions (it moves every tick)", () => {
  const samplerTag = page.match(/<p id="sampler-stats"[^>]*>/);
  assert.ok(samplerTag, "index.html is missing its sampler-stats element");
  assert.doesNotMatch(samplerTag[0], /aria-live/);
});

test("native: camera state still rides the preview accessibilityValue (no change needed)", () => {
  assert.match(view, /\.accessibilityValue\(cameraAccessibilityValue\)/);
});
