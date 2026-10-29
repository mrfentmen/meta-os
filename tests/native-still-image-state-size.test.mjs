// Node built-in test runner, no dependencies:
//   node --test tests/native-still-image-state-size.test.mjs
//
// IGNIS-UI-30 (Del UI push, Oct 29): native still-image state text
// size parity. The web frontend carries its still-image state as
// <p id="image-state" class="note"> and its assessing line as
// <p id="image-assessing" class="note"> — styles.css sets .note at
// 13px in --muted — but the native still-image panel's equivalent
// lines (ready, no-image, error, assessing) used .caption (12pt),
// so they read one point smaller than the web lines while the
// still-image intro (UI-25) already matched its own 13px web rule.
// The fix gives all four state lines a 13pt system font, keeping
// their muted color, the error's red, their wrapping, and their
// wording. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

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

const ready = blockAfter('Text("Image ready:');
const noImage = blockAfter('Text("No image chosen.")');
const error = blockAfter("if let error = model.stillImageError");
const assessing = blockAfter('Text("Sending still image…")');

test("native still-image state: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native still-image state: web state lines carry the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="image-state" class="note"/,
    "web image-state carries class note",
  );
  assert.match(
    html,
    /<p id="image-assessing" class="note"/,
    "web image-assessing carries class note",
  );
});

test("native still-image state: ready and no-image lines take 13pt", () => {
  assert.match(ready, /\.font\(\.system\(size: 13\)\)/, "ready line takes 13pt");
  assert.doesNotMatch(ready, /\.font\(\.caption\)/, "no caption left on ready line");
  assert.match(noImage, /\.font\(\.system\(size: 13\)\)/, "no-image line takes 13pt");
  assert.doesNotMatch(noImage, /\.font\(\.caption\)/, "no caption left on no-image line");
  assert.match(ready, /\.foregroundStyle\(\.secondary\)/, "ready line keeps muted color");
  assert.match(noImage, /\.foregroundStyle\(\.secondary\)/, "no-image line keeps muted color");
});

test("native still-image state: error and assessing lines take 13pt", () => {
  assert.match(error, /\.font\(\.system\(size: 13\)\)/, "error line takes 13pt");
  assert.doesNotMatch(error, /\.font\(\.caption\)/, "no caption left on error line");
  assert.match(error, /\.foregroundStyle\(\.red\)/, "error line keeps its red color");
  assert.match(assessing, /\.font\(\.system\(size: 13\)\)/, "assessing line takes 13pt");
  assert.doesNotMatch(assessing, /\.font\(\.caption\)/, "no caption left on assessing line");
  assert.match(assessing, /\.foregroundStyle\(\.secondary\)/, "assessing line keeps muted color");
});
