// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-latest-note-size.test.mjs
//
// IGNIS-UI-21 (Del UI push, Oct 29): native Latest-panel note size
// parity. The web Latest panel renders its notes with class "note" —
// styles.css sets .note at 13px in --muted, and js/app.js gives both
// the redisplayed-assessment note and the observable-evidence note
// that class — but the native panel's two notes used .callout (16pt),
// so both read larger than the web notes while the assessment itself
// already matched its own web rules. The fix gives both notes a 13pt
// system font, keeping their muted color, wrapping, and wording. No
// Swift toolchain exists in this sandbox, so these are static checks
// on the shipped Swift.

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

const rightColumn = content.slice(
  content.indexOf("private var rightColumn"),
  content.indexOf("TimelineView(model: model)"),
);
assert.ok(rightColumn.length > 0, "rightColumn exists");

test("native latest notes: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /const note = document\.createElement\("p"\);\s+note\.className = "note";/,
    "web redisplayed-assessment note carries the note class",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p class="note">Assessments describe observable evidence only\./,
    "web observable-evidence note carries the note class",
  );
});

test("native latest notes: redisplayed-assessment note at 13pt", () => {
  assert.match(
    rightColumn,
    /if let note = model\.displayedAssessmentNote \{\s+\/\/ UI-21[\s\S]*?Text\(note\)\s+\.font\(\.system\(size: 13\)\)\s+\.foregroundStyle\(\.secondary\)\s+\.fixedSize\(horizontal: false, vertical: true\)/,
    "displayed-assessment note takes the 13pt font, keeping its muted color and wrapping",
  );
});

test("native latest notes: observable-evidence note at 13pt", () => {
  assert.match(
    rightColumn,
    /Text\("Assessments describe observable evidence only\. Each product's limitations notice \(above\) states what its assessments never claim\."\)\s+\.font\(\.system\(size: 13\)\)\s+\.foregroundStyle\(\.secondary\)\s+\.fixedSize\(horizontal: false, vertical: true\)/,
    "observable-evidence note takes the 13pt font, keeping its wording, muted color, and wrapping",
  );
});

test("native latest notes: no callout font left in the Latest panel notes", () => {
  const notes = rightColumn.match(/\.font\(\.callout\)/g) || [];
  assert.equal(notes.length, 0, "no callout font left in rightColumn");
});
