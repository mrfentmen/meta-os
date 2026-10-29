// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-live-tracking.test.mjs
//
// IGNIS-UI-39 (Del UI push, Oct 29): native CAMERA LIVE label tracking
// parity. The web frontend carries its live indicator as a span with
// class .camera-indicator — styles.css sets it at 12px, weight 700,
// letter-spacing 0.08em — but the native camera panel's CAMERA LIVE
// label used .caption (12pt) bold with no tracking, so its letters
// read tighter than the web indicator's letterspaced capitals while
// the review flag (UI-16) already matched its own 0.05em web tracking.
// The fix gives the label 0.96pt tracking (0.08em of its own 12pt
// size), keeping its caption size, bold weight, white text, red badge,
// and wording. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 600) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const label = blockAfter('Label("CAMERA LIVE"');

test("native CAMERA LIVE label: web contract — .camera-indicator at 12px, 700, 0.08em tracking", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.camera-indicator \{\s+font-size: 12px;\s+font-weight: 700;\s+letter-spacing: 0\.08em;/,
    "web .camera-indicator is 12px, weight 700, letter-spacing 0.08em",
  );
});

test("native CAMERA LIVE label: web indicator carries the class and wording", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /class="camera-indicator"[^>]*><span class="dot"[^>]*><\/span>CAMERA LIVE<\/span>/,
    "web indicator carries class camera-indicator and reads CAMERA LIVE",
  );
});

test("native CAMERA LIVE label: takes 0.96pt tracking, keeps caption size and bold weight", () => {
  assert.match(label, /\.font\(\.caption\)/, "label keeps caption size");
  assert.match(label, /\.fontWeight\(\.bold\)/, "label keeps bold weight");
  assert.match(label, /\.tracking\(0\.96\)/, "label takes 0.96pt tracking");
});

test("native CAMERA LIVE label: badge and wording unchanged", () => {
  assert.match(
    label,
    /Label\("CAMERA LIVE", systemImage: "record\.circle\.fill"\)/,
    "label wording and icon unchanged",
  );
  assert.match(
    label,
    /\.foregroundStyle\(\.white\)/,
    "label keeps white text",
  );
  assert.match(label, /\.background\(Color\.red\)/, "label keeps red badge");
});
