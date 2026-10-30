// Node built-in test runner, no dependencies:
//   node --test tests/logo-color.test.mjs
//
// HANA Agent1 LOGO-1 (Del direction, Oct 30): the Logo panel on
// the main console carries the ASCII studio's color controls —
// its six presets plus a custom picker — and the choice persists
// in this browser's local storage and re-tints the spinning
// background live, with Reset returning to the product color.
// The studio's rotation speed and pause controls stay in the full
// studio page for now; this slice is color only, and says so in
// the panel's link note.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const bg = readFileSync(
  new URL("../js/logo-background.js", import.meta.url),
  "utf8",
);
const controls = readFileSync(
  new URL("../js/logo-color.js", import.meta.url),
  "utf8",
);
const studio = readFileSync(
  new URL("../design/meta-ascii-logo-studio.html", import.meta.url),
  "utf8",
);

const PRESETS = [
  "#1877f2",
  "#00c8ff",
  "#8b5cf6",
  "#ff4f9a",
  "#20d6a3",
  "#ffbd4a",
];

test("Logo panel carries the studio's six presets, a picker, and Reset", () => {
  assert.match(
    html,
    /<section class="panel" aria-label="Logo">/,
    "index.html carries a Logo panel",
  );
  for (const preset of PRESETS) {
    assert.match(
      html,
      new RegExp(`data-logo-color="${preset}"`),
      `Logo panel carries preset ${preset}`,
    );
    assert.match(
      studio,
      new RegExp(`data-color="${preset}"`),
      `studio carries the same preset ${preset}`,
    );
  }
  assert.match(
    html,
    /<input id="logo-color-picker" type="color"/,
    "Logo panel carries a custom color picker",
  );
  assert.match(
    html,
    /<button id="logo-color-reset" type="button">Reset to product color<\/button>/,
    "Logo panel carries a Reset to product color button",
  );
  assert.match(
    html,
    /<p id="logo-color-value" class="note mono">Logo color: product color<\/p>/,
    "Logo panel starts on the product color, not a preset",
  );
  assert.match(
    html,
    /<a class="logo-studio-link" href="design\/meta-ascii-logo-studio\.html">Open the full logo studio<\/a>/,
    "Logo panel links to the new studio file for speed and pause",
  );
  assert.match(
    html,
    /<script src="js\/logo-color\.js"><\/script>/,
    "index.html loads js/logo-color.js after the background script",
  );
});

test("stylesheet styles the swatches with a white ring when selected", () => {
  assert.match(
    css,
    /\.logo-color-options \{[^}]*display: flex;/,
    "styles.css lays the swatches out as a flex row",
  );
  assert.match(
    css,
    /\.logo-swatch \{[^}]*background: var\(--swatch\);/,
    "styles.css colors each swatch from its --swatch variable",
  );
  assert.match(
    css,
    /\.logo-swatch\.is-selected \{[^}]*border-color: #f5f9ff;/,
    "styles.css rings the selected swatch in white",
  );
});

test("controls persist the choice and dispatch it; background applies it", () => {
  assert.match(
    controls,
    /meta-trio-logo-color/,
    "js/logo-color.js uses the meta-trio-logo-color storage key",
  );
  assert.match(
    controls,
    /localStorage\.setItem\(STORAGE_KEY, color\)/,
    "js/logo-color.js saves the picked color",
  );
  assert.match(
    controls,
    /localStorage\.removeItem\(STORAGE_KEY\)/,
    "js/logo-color.js clears the saved color on Reset",
  );
  assert.match(
    controls,
    /new CustomEvent\("meta-trio-logo-color"/,
    "js/logo-color.js dispatches the color to the background",
  );
  assert.match(
    bg,
    /meta-trio-logo-color/,
    "js/logo-background.js shares the storage key",
  );
  assert.match(
    bg,
    /window\.addEventListener\("meta-trio-logo-color"/,
    "js/logo-background.js listens for the color event",
  );
  assert.match(
    bg,
    /localStorage\.getItem\(LOGO_COLOR_KEY\)/,
    "js/logo-background.js re-reads the saved color on load",
  );
  assert.match(
    bg,
    /if \(customColor\) return;/,
    "a saved color survives product switches until Reset",
  );
  assert.match(
    bg,
    /function buildPalette\(baseHex\)/,
    "js/logo-background.js builds its ramp from the chosen color, studio-style",
  );
});

test("background animation and reduced-motion rules are untouched", () => {
  assert.match(
    bg,
    /angleY \+= 0\.0022;/,
    "background still drifts slowly",
  );
  assert.match(
    bg,
    /prefers-reduced-motion: reduce/,
    "background still respects reduced motion",
  );
  assert.match(
    bg,
    /visibilitychange/,
    "background still pauses while the tab is hidden",
  );
});
