// Node built-in test runner, no dependencies:
//   node --test tests/native-clear-assessing.test.mjs
//
// Native Clear/Reset parity with the web frontend: the still-image and
// video assessing flags must be owned by the in-flight Task's defer,
// not by Clear or Reset Session.
//
// The web frontend's clearStillImageInput and clearVideoInput clear the
// chosen input but never touch stillImageAssessing or videoAssessing,
// so a new image or video chosen while the old request is still out
// cannot be sent until that request settles — the refresh helpers keep
// the Assess button disabled on the flag alone. The native Clear
// functions used to clear the flag too, so after a Clear (or a Reset
// Session, which calls both) during an in-flight request, a newly
// chosen image or video re-enabled its Assess button while the old
// request was still outstanding: a second send from the same panel,
// which the guard in assessStillImage / assessVideoFrame exists to
// prevent. The stale request itself was already harmless — its Task
// captures the generation and the payload at tap time, so it cannot
// repaint the cleared view — but the re-enabled button was not.
// Swift cannot run in this sandbox, so the ownership is asserted from
// source, in the same style as the other native tests. The web
// frontend needs no change: its Clear paths already leave the flags
// alone.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const app = readFileSync(
  new URL("../js/app.js", import.meta.url),
  "utf8",
);

function slice(source, start, end) {
  return source.slice(source.indexOf(start), source.indexOf(end));
}

const clearStillImage = slice(model, "func clearStillImage()", "// MARK: - Prerecorded-video input");
const clearVideo = slice(model, "func clearVideo()", "/// Frames are downscaled");
const webClearStillImage = slice(app, "function clearStillImageInput()", "els.btnImageClear");
const webClearVideo = slice(app, "function clearVideoInput()", "els.btnVideoClear");

test("native: clearStillImage clears the input but not the assessing flag", () => {
  assert.match(clearStillImage, /stillImage = nil/);
  assert.match(clearStillImage, /stillImageName = nil/);
  assert.match(clearStillImage, /stillImageDataURL = nil/);
  assert.match(clearStillImage, /stillImageError = nil/);
  assert.doesNotMatch(clearStillImage, /stillImageAssessing = false/);
});

test("native: clearVideo clears the input but not the assessing flag", () => {
  assert.match(clearVideo, /videoPlayer\?\.pause\(\)/);
  assert.match(clearVideo, /videoPlayer = nil/);
  assert.match(clearVideo, /videoURL = nil/);
  assert.match(clearVideo, /videoName = nil/);
  assert.match(clearVideo, /videoError = nil/);
  assert.doesNotMatch(clearVideo, /videoAssessing = false/);
});

test("native: each assessing flag is cleared exactly once, by its Task defer", () => {
  // The declaration lines read "var stillImageAssessing = false" and
  // the defers read "defer { stillImageAssessing = false }", so a
  // bare indented assignment — the Clear/Reset shape — is what counts
  // here, and there must be none left.
  const stillClears = model.match(/\n\s+stillImageAssessing = false\n/g) ?? [];
  const videoClears = model.match(/\n\s+videoAssessing = false\n/g) ?? [];
  assert.equal(stillClears.length, 0);
  assert.equal(videoClears.length, 0);
  assert.match(model, /defer \{ stillImageAssessing = false \}/);
  assert.match(model, /defer \{ videoAssessing = false \}/);
});

test("native: the Assess buttons still gate on the flag, so it is the guard", () => {
  assert.match(contentView, /\.disabled\(model\.stillImage == nil \|\| model\.stillImageAssessing\)/);
  assert.match(contentView, /\.disabled\(model\.videoPlayer == nil \|\| model\.videoAssessing\)/);
});

test("web parity: the web Clear paths already leave both flags alone", () => {
  assert.doesNotMatch(webClearStillImage, /stillImageAssessing = false/);
  assert.doesNotMatch(webClearVideo, /videoAssessing = false/);
  // And the web Reset path reaches both Clear helpers, so it inherits
  // the same rule rather than clearing the flags itself.
  const reset = slice(app, "els.btnReset.addEventListener", "els.intervalSeconds.addEventListener");
  assert.match(reset, /clearStillImageInput\(\)/);
  assert.match(reset, /clearVideoInput\(\)/);
  assert.doesNotMatch(reset, /stillImageAssessing = false/);
  assert.doesNotMatch(reset, /videoAssessing = false/);
});
