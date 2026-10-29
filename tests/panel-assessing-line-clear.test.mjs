// Node built-in test runner, no dependencies:
//   node --test tests/panel-assessing-line-clear.test.mjs
//
// The "Sending still image…" / "Sending video frame…" lines vs Clear.
// The Assess button's disabled state already survives a Clear during a
// request (see native-clear-assessing.test.mjs): the assessing flags
// are owned by the in-flight request, not by Clear. The sending lines
// did not follow the same rule on the web frontend. clearStillImageInput
// and clearVideoInput each hid their line unconditionally, so clearing
// the input — or choosing a new file, or Reset, which reuses both
// helpers — during a request left the panel silent while that request
// was still outstanding, the very wait the line exists to show. The
// native panels have no such hole: each shows its progress line while
// its assessing flag is true whatever the input is, and only the
// in-flight Task's defer clears the flag. The web Clear paths now set
// the line from the flag instead, and the Assess settle paths still
// hide it when the request finishes. Swift cannot run in this sandbox,
// so the native side is asserted from source, in the same style as the
// other native tests.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(
  new URL("../js/app.js", import.meta.url),
  "utf8",
);
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function slice(source, start, end) {
  return source.slice(source.indexOf(start), source.indexOf(end));
}

const webClearStillImage = slice(
  app,
  "function clearStillImageInput() {",
  "els.btnImageClear",
);
const webClearVideo = slice(
  app,
  "function clearVideoInput() {",
  "els.btnVideoClear",
);
const webReset = slice(
  app,
  "els.btnReset.addEventListener",
  "els.intervalSeconds.addEventListener",
);
const stillClick = slice(
  app,
  'els.btnImageAssess.addEventListener("click"',
  "// Prerecorded-video input state",
);
const videoClick = slice(
  app,
  'els.btnVideoAssess.addEventListener("click"',
  'els.btnCameraStart.addEventListener("click"',
);

test("still-image: Clear sets the sending line from the assessing flag, never hides it outright", () => {
  assert.doesNotMatch(webClearStillImage, /els\.imageAssessing\.hidden = true;/);
  assert.match(webClearStillImage, /els\.imageAssessing\.hidden = !stillImageAssessing;/);
});

test("video: Clear sets the sending line from the assessing flag, never hides it outright", () => {
  assert.doesNotMatch(webClearVideo, /els\.videoAssessing\.hidden = true;/);
  assert.match(webClearVideo, /els\.videoAssessing\.hidden = !videoAssessing;/);
});

test("reset: Reset reaches both Clear helpers and hides neither sending line itself", () => {
  assert.match(webReset, /clearStillImageInput\(\);/);
  assert.match(webReset, /clearVideoInput\(\);/);
  assert.doesNotMatch(webReset, /imageAssessing\.hidden/);
  assert.doesNotMatch(webReset, /videoAssessing\.hidden/);
});

test("assess settle: the Assess paths still hide their sending line when the request finishes", () => {
  assert.match(stillClick, /els\.imageAssessing\.hidden = false;/);
  assert.match(stillClick, /els\.imageAssessing\.hidden = true;/);
  assert.match(videoClick, /els\.videoAssessing\.hidden = false;/);
  assert.match(videoClick, /els\.videoAssessing\.hidden = true;/);
});

test("native: each panel shows its sending line while its assessing flag is true, whatever the input is", () => {
  assert.match(
    contentView,
    /if model\.stillImageAssessing \{[\s\S]*?Text\("Sending still image…"\)/,
  );
  assert.match(
    contentView,
    /if model\.videoAssessing \{[\s\S]*?Text\("Sending video frame…"\)/,
  );
});
