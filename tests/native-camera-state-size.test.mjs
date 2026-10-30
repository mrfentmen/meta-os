// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-state-size.test.mjs
//
// IGNIS-UI-35 (Del UI push, Oct 29): native camera state text size
// parity. The web frontend carries its camera state as
// <p id="camera-state" class="note"> — styles.css sets .note at 13px
// in --muted (red for the error states via the app's error styling)
// — but the native camera panel's equivalent lines (off, waiting,
// live, stopped, denied, no-camera, failed) carried no font at all,
// so they read at the default body size, larger than the web line,
// while the camera-facing note (UI-28) and the product-guidance note
// (UI-29) already matched their own 13px web rules. The fix gives
// all seven state lines a 13pt system font, keeping their muted
// color, the errors' red, the denied and failed lines' wrapping,
// and their wording. OPS-CONSOLE-5 later gave the lines a
// conditional mono face and 0.26pt tracking on Ignis (see
// native-ignis-ops-console-status.test.mjs), widened to Ignis or
// Vigiles by OPS-CONSOLE-9; the size assertions below were rewired
// to the two-gate font call, and 13pt itself is unchanged. No Swift toolchain exists in this sandbox, so
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

function blockAfter(marker, length = 450) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const idle = blockAfter('Text("Camera is off.")');
const waiting = blockAfter('Text("Waiting for camera permission…")');
const running = blockAfter('Text("Camera is live. No frames are sent anywhere until analysis is started.")');
const stopped = blockAfter('Text("Camera stopped.")');
const denied = blockAfter('Text("Camera permission denied.');
const noCamera = blockAfter('Text("No camera was found on this Mac.")');
const failed = blockAfter('Text("Camera error:');

test("native camera state: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native camera state: web camera-state carries the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="camera-state" class="note"/,
    "web camera-state carries class note",
  );
});

test("native camera state: off, waiting, live, and stopped lines take 13pt", () => {
  for (const [name, block] of [["off", idle], ["waiting", waiting], ["live", running], ["stopped", stopped]]) {
    assert.match(block, /\.font\(\.system\(size: 13, design: \(isIgnisSelected \|\| isVigilesSelected\) \? \.monospaced : .default\)\)/, `${name} line takes 13pt`);
    assert.match(block, /\.foregroundStyle\(\.secondary\)/, `${name} line keeps muted color`);
  }
});

test("native camera state: denied, no-camera, and failed lines take 13pt", () => {
  for (const [name, block] of [["denied", denied], ["no-camera", noCamera], ["failed", failed]]) {
    assert.match(block, /\.font\(\.system\(size: 13, design: \(isIgnisSelected \|\| isVigilesSelected\) \? \.monospaced : .default\)\)/, `${name} line takes 13pt`);
    assert.match(block, /\.foregroundStyle\(\.red\)/, `${name} line keeps its red color`);
  }
  assert.match(
    denied,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "denied line keeps its wrapping",
  );
  assert.match(
    failed,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "failed line keeps its wrapping",
  );
});
