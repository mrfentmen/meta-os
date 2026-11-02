// Node built-in test runner, no dependencies:
//   node --test tests/latest-region-frame.test.mjs
//
// BUILD WAVE W1 live wiring (2026-11-02): the latest panel draws
// the assessed frame with its region boxes, from the exact frame
// that was sent — never a guessed frame, never a live preview.
//
// Wiring, checked against js/app.js source (renderLatest is a
// browser-DOM function, like the other latest-panel tests):
// - app.js imports regionBoxes from ./surfaces.js.
// - renderLatest takes an optional frameImage third argument.
// - Inside renderLatest, the frame draws only when frameImage is
//   a data:image URL AND regionBoxes(assessment) is non-empty.
// - submitAssessment passes its image (the frame it sent) through.
// - A redisplayed past assessment (history/restore) passes no
//   frame, so it stays text-only.
// - styles.css positions the frame, overlay, and boxes so percent
//   boxes land on the frame.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const render = app.slice(
  app.indexOf("function renderLatest"),
  app.indexOf("function addHistoryItem"),
);
assert.ok(render.length > 0, "renderLatest exists");

test("app.js imports regionBoxes from surfaces.js", () => {
  assert.ok(
    app.includes('import { regionBoxes } from "./surfaces.js";'),
    "regionBoxes imported",
  );
});

test("renderLatest takes an optional frameImage third argument", () => {
  assert.match(
    render,
    /function renderLatest\(assessment, earlierNote = null, frameImage = null\)/,
  );
});

test("renderLatest draws the frame only with a data:image URL and real boxes", () => {
  assert.ok(render.includes("regionBoxes(assessment)"), "boxes computed in renderLatest");
  assert.ok(
    render.includes('frameImage.startsWith("data:image/")'),
    "frame must be a locally produced data:image URL",
  );
  assert.ok(render.includes('boxes !== ""'), "no boxes means no frame");
  assert.ok(render.includes('className = "assessed-frame"'), "frame container created");
  assert.ok(render.includes('img.src = frameImage'), "frame image is the passed frame");
  assert.ok(render.includes("overlay.innerHTML = boxes"), "boxes overlaid on the frame");
});

test("submitAssessment passes the sent frame to renderLatest", () => {
  assert.ok(
    app.includes("renderLatest(assessment, null, image);"),
    "fresh assessment carries its sent frame",
  );
});

test("history and restore redisplay pass no frame, so they stay text-only", () => {
  const historyCall = app.slice(app.indexOf("Show assessment"));
  assert.ok(
    historyCall.includes("renderLatest(\n        assessment,"),
    "history Show assessment calls renderLatest without a frame",
  );
  assert.ok(
    app.includes("if (latestOk) renderLatest(latestOk);"),
    "restore calls renderLatest without a frame",
  );
});

test("styles.css positions the frame, overlay, and boxes", () => {
  assert.match(css, /\.assessed-frame \{\s*position: relative;/);
  assert.match(css, /\.assessed-frame-overlay \{\s*position: absolute;\s*inset: 0;/);
  assert.match(css, /\.assessed-frame-overlay \.region-boxes \{\s*position: absolute;\s*inset: 0;/);
  assert.match(css, /\.region-box \{\s*position: absolute;/);
});
