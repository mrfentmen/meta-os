// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-guidance-size.test.mjs
//
// IGNIS-UI-29 (Del UI push, Oct 29): native camera product-guidance
// note size parity. The web frontend carries its product guidance as
// a <p id="product-guidance" class="note"> — styles.css sets .note at
// 13px in --muted — but the native camera panel's equivalent note
// used .caption (12pt), so it read one point smaller than the web
// note while the facing note (UI-28) and the still-image and video
// intros (UI-25, UI-26) already matched their own 13px web rules.
// The fix gives the guidance note a 13pt system font, keeping its
// muted color, wrapping, and per-product wording. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.

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

const noteStart = content.indexOf("Text(model.config.inputGuidance)");
assert.ok(noteStart >= 0, "guidance note exists");
const note = content.slice(noteStart, noteStart + 600);
assert.ok(note.length > 0, "guidance note block exists");

test("native camera guidance note: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native camera guidance note: web note carries the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="product-guidance" class="note">/,
    "web product-guidance note carries class note",
  );
});

test("native camera guidance note: note takes the 13pt system font", () => {
  assert.match(
    note,
    /\.font\(\.system\(size: 13\)\)/,
    "guidance note takes the 13pt font",
  );
});

test("native camera guidance note: no caption left, note unchanged", () => {
  assert.doesNotMatch(
    note,
    /\.font\(\.caption\)/,
    "no caption font left on the guidance note",
  );
  assert.match(
    note,
    /\.foregroundStyle\(\.secondary\)/,
    "guidance note keeps its muted color",
  );
  assert.match(
    note,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "guidance note keeps its wrapping",
  );
});
