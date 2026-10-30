// Node built-in test runner, no dependencies:
//   node --test tests/logo-background.test.mjs
//
// HANA Agent1: the spinning ASCII Meta loop lives in the app
// background. The page carries a hidden background canvas wired
// to js/logo-background.js, the stylesheet pins that canvas
// behind the content at low opacity with no pointer input, and
// the background script itself stays still under reduced motion
// and pauses while the tab is hidden.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const bg = readFileSync(
  new URL("../js/logo-background.js", import.meta.url),
  "utf8",
);

test("page carries a hidden background canvas and its script", () => {
  assert.match(
    html,
    /<canvas id="logo-background" aria-hidden="true"><\/canvas>/,
    "index.html carries an aria-hidden logo-background canvas",
  );
  assert.match(
    html,
    /<script src="js\/logo-background\.js"><\/script>/,
    "index.html loads js/logo-background.js",
  );
});

test("stylesheet pins the background behind content, dim, untouchable", () => {
  assert.match(
    css,
    /#logo-background \{[^}]*position: fixed;[^}]*z-index: 0;[^}]*opacity: 0\.5;[^}]*pointer-events: none;/,
    "styles.css fixes the background at z-index 0, opacity 0.5, no pointer input",
  );
  assert.match(
    css,
    /--panel: rgba\(29, 32, 38, 0\.8\);/,
    "panels are see-through so the loop ghosts through them",
  );
  assert.match(
    css,
    /background: rgba\(20, 22, 26, 0\.92\);/,
    "header and footer keep a near-solid back so their text stays readable",
  );
  assert.match(
    css,
    /\.topbar,\s*main,\s*\.footer \{\s*position: relative;\s*z-index: 1;\s*\}/,
    "topbar, main, and footer sit above the background",
  );
});

test("background script is slow, still under reduced motion, paused when hidden", () => {
  assert.match(
    bg,
    /prefers-reduced-motion: reduce/,
    "logo-background.js checks prefers-reduced-motion",
  );
  assert.match(
    bg,
    /visibilitychange/,
    "logo-background.js pauses on visibilitychange",
  );
  assert.match(
    bg,
    /var speedStep = 0\.0022;/,
    "logo-background.js still defaults to a slow drift, not studio speed (LOGO-2 made the step slider-driven)",
  );
  assert.match(
    bg,
    /if \(!reducedMotion && !userPaused\) angleY \+= speedStep;/,
    "logo-background.js advances only when motion is allowed and the user has not paused",
  );
  assert.match(
    bg,
    /var SCALE = 1\.05;/,
    "logo-background.js is a little smaller than the first background size",
  );
  assert.match(
    bg,
    /vigiles: \[/,
    "logo-background.js carries a Vigiles palette",
  );
  assert.match(
    bg,
    /ignis: \[[\s\S]*?#d92b2b/,
    "logo-background.js carries an Ignis red palette around #d92b2b",
  );
  assert.match(
    bg,
    /medicus: \[[\s\S]*?#5da864/,
    "logo-background.js carries a Medicus green palette around #5da864",
  );
  assert.match(
    bg,
    /MutationObserver/,
    "logo-background.js follows product switches via MutationObserver",
  );
});
