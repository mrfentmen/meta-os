// Node built-in test runner, no dependencies:
//   node --test tests/native-still-image-intro-size.test.mjs
//
// IGNIS-UI-25 (Del UI push, Oct 29): native still-image intro note
// size parity. The web frontend carries the still-image panel's
// intro as a <p class="note"> — styles.css sets .note at 13px in
// --muted — but the native panel's equivalent intro used .caption
// (12pt), so it read one point smaller than the web intro while
// the Latest-panel notes (UI-21) and footer (UI-23) already matched
// their own 13px web rules. The fix gives the intro a 13pt system
// font, keeping its muted color, wrapping, and words verbatim. No
// Swift toolchain exists in this sandbox, so these are static
// checks on the shipped Swift.

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

const introStart = content.indexOf('Text("For prerecorded or photographed scenes');
assert.ok(introStart >= 0, "still-image intro exists");
const intro = content.slice(introStart, introStart + 1200);
assert.ok(intro.length > 0, "intro block exists");

const introWords =
  "For prerecorded or photographed scenes — the input Ignis and Sanitas demos use when a live camera is not the source. The image is sent once to the assessment endpoint, under the product selected above, and is logged exactly like a live frame. It is not stored by this app.";

test("native still-image intro: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native still-image intro: web panel carries the same intro words", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes(`<p class="note">${introWords}</p>`),
    "web still-image panel carries the intro verbatim as a note",
  );
});

test("native still-image intro: intro takes the 13pt system font", () => {
  assert.match(
    intro,
    /Text\("For prerecorded[\s\S]{0,600}?\.font\(\.system\(size: 13\)\)/,
    "still-image intro takes the 13pt font",
  );
});

test("native still-image intro: no caption font left on the intro", () => {
  const introBlock = intro.slice(0, intro.indexOf("if let image"));
  assert.doesNotMatch(
    introBlock,
    /\.font\(\.caption\)/,
    "no caption font left on the still-image intro",
  );
  assert.match(
    introBlock,
    /\.foregroundStyle\(\.secondary\)/,
    "still-image intro keeps its muted color",
  );
  assert.ok(
    introBlock.includes(introWords),
    "still-image intro keeps the web panel's words verbatim",
  );
});
