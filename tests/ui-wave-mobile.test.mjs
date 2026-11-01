// Node built-in test runner, no dependencies:  node --test tests/ui-wave-mobile.test.mjs
// Covers HN-016 (mobile pass at 390 px): the 480 px block stacks
// the camera wall instead of scrolling it sideways, lifts every
// tap target to 44 px, and clips horizontal overflow. No browser
// runs in this sandbox, so these are rule tests on the shipped
// stylesheet — a real-device 390 px check stays owed at gate and
// is named in the HN-021/HN-025 record, never claimed here.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const mobile = css.slice(css.indexOf("@media (max-width: 480px)"));
assert.ok(mobile.length > 0, "480px block exists");

test("camera wall stacks vertically at phone width", () => {
  assert.match(mobile, /\.cmd-wall \{ flex-direction: column; overflow-x: visible; \}/);
  assert.match(mobile, /\.cmd-tile \{ flex: 1 1 auto; \}/);
});

test("tap targets reach 44 px in both views", () => {
  assert.match(mobile, /\.command-view button,\n\s+\.command-view input,\n\s+\.command-view select \{ min-height: 44px; \}/);
  assert.match(mobile, /main button,\n\s+main input,\n\s+main select \{ min-height: 44px; \}/);
  assert.match(mobile, /\.maplibregl-ctrl button \{ min-height: 44px; min-width: 44px; \}/);
});

test("no horizontal scroll at phone width", () => {
  assert.match(mobile, /\.command-view \{ overflow-x: clip; \}/);
  assert.match(mobile, /main \{ overflow-x: clip; padding: 8px; \}/);
  assert.match(mobile, /\.command-view \.cmd-sys-value \{ overflow-wrap: anywhere; \}/);
});

test("map stays a sane height on a phone", () => {
  assert.match(mobile, /\.cmd-map \{ height: 300px; \}/);
});
