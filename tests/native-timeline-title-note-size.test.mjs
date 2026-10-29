// Node built-in test runner, no dependencies:
//   node --test tests/native-timeline-title-note-size.test.mjs
//
// IGNIS-UI-34 (Del UI push, Oct 29): native timeline panel title and
// intro-note size parity. The web frontend carries every panel title
// as a .panel h2 at 15px weight 700, and its history notes as .note at
// 13px in --muted — but the native TimelineView title used .headline
// (17pt semibold), so it read larger and one step lighter than the web
// history title while the Latest panel title (UI-23) already matched
// its own 15px web rule, and the timeline intro note used .caption
// (12pt), so it read one point smaller than the web notes while the
// still-image, video, header, camera-facing, and Settings notes
// (UI-25 through UI-33) already matched their own 13px web rules. The
// fix gives the title a 15pt bold system font and the note a 13pt
// system font, keeping their wording, muted note color, wrapping, and
// the title's header trait. No Swift toolchain exists in this sandbox,
// so these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const timeline = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 500) {
  const start = timeline.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return timeline.slice(start, start + length);
}

const title = blockAfter('Text("Event timeline")');
const note = blockAfter(
  'Text("Tap an assessment row to view that assessment again',
  600,
);

test("native timeline title: web contract — .panel h2 at 15px weight 700", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.panel h2 \{\s+margin: 0 0 10px;\s+font-size: 15px;\s+font-weight: 700;/,
    "web .panel h2 is 15px weight 700",
  );
});

test("native timeline note: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native timeline title: takes 15pt bold, keeps header trait", () => {
  assert.match(
    title,
    /\.font\(\.system\(size: 15, weight: \.bold\)\)/,
    "title takes 15pt bold",
  );
  assert.doesNotMatch(title, /\.font\(\.headline\)/, "no headline left on title");
  assert.match(
    title,
    /\.accessibilityAddTraits\(\.isHeader\)/,
    "title keeps its header trait",
  );
});

test("native timeline note: takes 13pt, keeps muted color and wrapping", () => {
  assert.match(note, /\.font\(\.system\(size: 13\)\)/, "note takes 13pt");
  assert.doesNotMatch(note, /\.font\(\.caption\)/, "no caption left on note");
  assert.match(
    note,
    /\.foregroundStyle\(\.secondary\)/,
    "note keeps muted color",
  );
  assert.match(
    note,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "note keeps its wrapping",
  );
});
