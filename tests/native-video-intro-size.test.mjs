// Node built-in test runner, no dependencies:
//   node --test tests/native-video-intro-size.test.mjs
//
// IGNIS-UI-26 (Del UI push, Oct 29): native prerecorded-video intro
// note size parity. The web frontend carries the video panel's
// intro as a <p class="note"> — styles.css sets .note at 13px in
// --muted — but the native panel's equivalent intro used .caption
// (12pt), so it read one point smaller than the web intro while
// the still-image intro (UI-25) already matched its own 13px web
// rule. The fix gives the intro a 13pt system font, keeping its
// muted color, wrapping, and words verbatim. No Swift toolchain
// exists in this sandbox, so these are static checks on the
// shipped Swift.

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

const introStart = content.indexOf('Text("For a recorded clip');
assert.ok(introStart >= 0, "video intro exists");
const intro = content.slice(introStart, introStart + 1200);
assert.ok(intro.length > 0, "intro block exists");

const introWords =
  "For a recorded clip when neither a live camera nor a still image is the source. Play the clip, pause on the frame you want assessed, and tap “Assess this frame”: only that one frame is sent to the assessment endpoint, under the product selected above, and logged exactly like a live frame. The whole video is never sent, and it is not stored by this app.";

test("native video intro: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native video intro: web panel carries the same intro words", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes(`<p class="note">${introWords}</p>`),
    "web video panel carries the intro verbatim as a note",
  );
});

test("native video intro: intro takes the 13pt system font", () => {
  assert.match(
    intro,
    /Text\("For a recorded clip[\s\S]{0,600}?\.font\(\.system\(size: 13\)\)/,
    "video intro takes the 13pt font",
  );
});

test("native video intro: no caption font left on the intro", () => {
  const introBlock = intro.slice(0, intro.indexOf("if let player"));
  assert.doesNotMatch(
    introBlock,
    /\.font\(\.caption\)/,
    "no caption font left on the video intro",
  );
  assert.match(
    introBlock,
    /\.foregroundStyle\(\.secondary\)/,
    "video intro keeps its muted color",
  );
  assert.ok(
    introBlock.includes(introWords),
    "video intro keeps the web panel's words verbatim",
  );
});
