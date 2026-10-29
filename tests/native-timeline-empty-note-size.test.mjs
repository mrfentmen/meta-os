// Node built-in test runner, no dependencies:
//   node --test tests/native-timeline-empty-note-size.test.mjs
//
// IGNIS-UI-47 (Del UI push, Oct 29): native timeline empty-state note
// size parity. The web history panel carries its empty note as
// #history-empty with class .note (13px, muted), but the native
// TimelineView empty-state notes were plain Texts at the default body
// size, so they read four points larger than the web note while the
// timeline intro note just above them (UI-34) already matched its own
// 13px web rule. The fix gives both notes a 13pt system font, keeping
// their muted color and their wording, which match the web strings
// exactly. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

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

const running = blockAfter(
  'Text("Analysis is running — assessments and errors will appear here as they arrive.")',
);
const idle = blockAfter(
  'Text("No events yet. Assessments and errors will appear here.")',
);

test("native timeline empty notes: web contract — #history-empty carries .note at 13px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes('<p id="history-empty" class="note"'),
    "web history-empty note carries .note",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.ok(
    app.includes(
      '"Analysis is running — assessments and errors will appear here as they arrive."',
    ),
    "web running string matches the native running note",
  );
  assert.ok(
    app.includes('"No events yet. Assessments and errors will appear here."'),
    "web idle string matches the native idle note",
  );
});

test("native timeline empty notes: both take 13pt, keep muted color", () => {
  assert.match(running, /\.font\(\.system\(size: 13\)\)/, "running note takes 13pt");
  assert.match(
    running,
    /\.foregroundStyle\(\.secondary\)/,
    "running note keeps muted color",
  );
  assert.match(idle, /\.font\(\.system\(size: 13\)\)/, "idle note takes 13pt");
  assert.match(
    idle,
    /\.foregroundStyle\(\.secondary\)/,
    "idle note keeps muted color",
  );
});

test("native timeline empty notes: no default-size note left in the empty state", () => {
  const emptyState = timeline.slice(
    timeline.indexOf("if model.timeline.isEmpty {"),
    timeline.indexOf("List(model.timeline)"),
  );
  assert.doesNotMatch(
    emptyState,
    /Text\("[^"]+"\)\s+\.foregroundStyle\(\.secondary\)/,
    "no bare Text-then-secondary note without a font in the empty state",
  );
});
