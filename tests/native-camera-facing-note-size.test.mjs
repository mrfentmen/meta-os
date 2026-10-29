// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-facing-note-size.test.mjs
//
// IGNIS-UI-28 (Del UI push, Oct 29): native camera facing note size
// parity. The web frontend carries its facing note as a <p
// class="note"> right after the camera-facing picker — styles.css
// sets .note at 13px in --muted — but the native camera panel's
// equivalent note used .caption (12pt), so it read one point smaller
// than the web note while the still-image and video intros (UI-25,
// UI-26) and the header limitations (UI-27) already matched their own
// 13px web rules. The fix gives the facing note a 13pt system font,
// keeping its muted color, wrapping, and wording, and the picker above
// keeps its menu style. No Swift toolchain exists in this sandbox, so
// these are static checks on the shipped Swift.

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

const noteStart = content.indexOf(
  'Text("A facing is a preference, not a requirement:',
);
assert.ok(noteStart >= 0, "facing note exists");
const note = content.slice(noteStart, noteStart + 500);
assert.ok(note.length > 0, "facing note block exists");

test("native camera facing note: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native camera facing note: web note carries the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p class="note">A preference, not a requirement:/,
    "web camera-facing note carries class note",
  );
});

test("native camera facing note: note takes the 13pt system font", () => {
  assert.match(
    note,
    /\.font\(\.system\(size: 13\)\)/,
    "facing note takes the 13pt font",
  );
});

test("native camera facing note: no caption left, note unchanged", () => {
  assert.doesNotMatch(
    note,
    /\.font\(\.caption\)/,
    "no caption font left on the facing note",
  );
  assert.match(
    note,
    /\.foregroundStyle\(\.secondary\)/,
    "facing note keeps its muted color",
  );
  assert.match(
    note,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "facing note keeps its wrapping",
  );
});
