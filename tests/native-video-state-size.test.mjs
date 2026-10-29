// Node built-in test runner, no dependencies:
//   node --test tests/native-video-state-size.test.mjs
//
// IGNIS-UI-31 (Del UI push, Oct 29): native prerecorded-video state
// text size parity. The web frontend carries its video state as
// <p id="video-state" class="note"> and its assessing line as
// <p id="video-assessing" class="note"> — styles.css sets .note at
// 13px in --muted — but the native video panel's equivalent lines
// (ready, no-video, error, assessing) used .caption (12pt), so they
// read one point smaller than the web lines while the video intro
// (UI-26) already matched its own 13px web rule. The fix gives all
// four state lines a 13pt system font, keeping their muted color,
// the error's red, their wrapping, and their wording. No Swift
// toolchain exists in this sandbox, so these are static checks on
// the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
    import.meta.url,
  ),
  "utf8",
);

function blockAfter(marker, length = 400) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const ready = blockAfter('Text("Video ready:');
const noVideo = blockAfter('Text("No video chosen.")');
const error = blockAfter("if let error = model.videoError");
const assessing = blockAfter('Text("Sending video frame…")');

test("native video state: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native video state: web state lines carry the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="video-state" class="note"/,
    "web video-state carries class note",
  );
  assert.match(
    html,
    /<p id="video-assessing" class="note"/,
    "web video-assessing carries class note",
  );
});

test("native video state: ready and no-video lines take 13pt", () => {
  assert.match(ready, /\.font\(\.system\(size: 13\)\)/, "ready line takes 13pt");
  assert.doesNotMatch(ready, /\.font\(\.caption\)/, "no caption left on ready line");
  assert.match(noVideo, /\.font\(\.system\(size: 13\)\)/, "no-video line takes 13pt");
  assert.doesNotMatch(noVideo, /\.font\(\.caption\)/, "no caption left on no-video line");
  assert.match(ready, /\.foregroundStyle\(\.secondary\)/, "ready line keeps muted color");
  assert.match(noVideo, /\.foregroundStyle\(\.secondary\)/, "no-video line keeps muted color");
});

test("native video state: error and assessing lines take 13pt", () => {
  assert.match(error, /\.font\(\.system\(size: 13\)\)/, "error line takes 13pt");
  assert.doesNotMatch(error, /\.font\(\.caption\)/, "no caption left on error line");
  assert.match(error, /\.foregroundStyle\(\.red\)/, "error line keeps its red color");
  assert.match(assessing, /\.font\(\.system\(size: 13\)\)/, "assessing line takes 13pt");
  assert.doesNotMatch(assessing, /\.font\(\.caption\)/, "no caption left on assessing line");
  assert.match(assessing, /\.foregroundStyle\(\.secondary\)/, "assessing line keeps muted color");
});
