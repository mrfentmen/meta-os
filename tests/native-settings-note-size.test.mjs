// Node built-in test runner, no dependencies:
//   node --test tests/native-settings-note-size.test.mjs
//
// IGNIS-UI-32 (Del UI push, Oct 29): native Settings panel note text
// size parity. The web frontend carries its backend-health line as
// <p id="backend-health" class="note"> and its sampling disclosure as
// <p id="sampling-disclosure" class="note"> — styles.css sets .note at
// 13px in --muted — but the native Settings panel's equivalent lines
// used .caption (12pt), so they read one point smaller than the web
// lines while the header limitations (UI-27) already matched their own
// 13px web rule. The fix gives both lines a 13pt system font, keeping
// their muted color, their wrapping, and their wording. No Swift
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

const health = blockAfter("Text(model.backendHealth)");
const sampling = blockAfter('Text("Analysis uses sampled frames:', 500);

test("native settings notes: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native settings notes: web lines carry the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="backend-health" class="note"/,
    "web backend-health carries class note",
  );
  assert.match(
    html,
    /<p id="sampling-disclosure" class="note"/,
    "web sampling-disclosure carries class note",
  );
});

test("native settings notes: backend-health line takes 13pt", () => {
  assert.match(health, /\.font\(\.system\(size: 13\)\)/, "health line takes 13pt");
  assert.doesNotMatch(health, /\.font\(\.caption\)/, "no caption left on health line");
  assert.match(health, /\.foregroundStyle\(\.secondary\)/, "health line keeps muted color");
  assert.match(
    health,
    /\.accessibilityLabel\("Backend health: /,
    "health line keeps its accessibility label",
  );
});

test("native settings notes: sampling-disclosure line takes 13pt", () => {
  assert.match(sampling, /\.font\(\.system\(size: 13\)\)/, "sampling line takes 13pt");
  assert.doesNotMatch(sampling, /\.font\(\.caption\)/, "no caption left on sampling line");
  assert.match(sampling, /\.foregroundStyle\(\.secondary\)/, "sampling line keeps muted color");
});
