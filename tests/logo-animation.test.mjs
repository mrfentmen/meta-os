// Node built-in test runner, no dependencies:
//   node --test tests/logo-animation.test.mjs
//
// HANA Agent1 LOGO-2 (Del direction, Oct 30): the Logo panel on
// the main console carries the studio's rotation speed slider
// and pause button, completing the studio controls LOGO-1 left
// in the full studio page. Speed and pause persist in this
// browser's local storage and drive the spinning background
// live; 25% is the console's usual slow drift, 0% is still,
// and a pause holds the loop on its last frame without
// disturbing the hidden-tab pause or reduced motion.

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
  new URL("../js/logo-animation.js", import.meta.url),
  "utf8",
);

test("Logo panel carries a speed slider and a pause button", () => {
  assert.match(
    html,
    /<section class="panel" aria-label="Logo">/,
    "index.html carries a Logo panel",
  );
  assert.match(
    html,
    /<input id="logo-speed" type="range" min="0" max="100" value="25"/,
    "Logo panel carries a 0-100 speed slider defaulting to 25",
  );
  assert.match(
    html,
    /<p id="logo-speed-value" class="note mono">Rotation speed: 25%<\/p>/,
    "Logo panel starts on the usual drift, 25%",
  );
  assert.match(
    html,
    /<button id="logo-pause" type="button" aria-pressed="false"><span id="logo-pause-label">Pause logo<\/span><\/button>/,
    "Logo panel carries a Pause logo button, not pressed at start",
  );
  assert.match(
    html,
    /<script src="js\/logo-animation\.js"><\/script>/,
    "index.html loads js/logo-animation.js after the color script",
  );
  assert.match(
    html,
    /<a class="logo-studio-link" href="design\/meta-ascii-logo-studio\.html">Open the full logo studio<\/a> for the large animated logo\./,
    "studio link now points at the large logo only, since speed and pause live in the panel",
  );
});

test("stylesheet spans the speed slider across the panel", () => {
  assert.match(
    css,
    /#logo-speed \{[^}]*width: 100%;/,
    "styles.css spans the speed slider across the panel",
  );
});

test("controls persist speed and pause and dispatch them; background applies them", () => {
  assert.match(
    controls,
    /meta-trio-logo-speed/,
    "js/logo-animation.js uses the meta-trio-logo-speed storage key",
  );
  assert.match(
    controls,
    /meta-trio-logo-paused/,
    "js/logo-animation.js uses the meta-trio-logo-paused storage key",
  );
  assert.match(
    controls,
    /localStorage\.setItem\(SPEED_KEY, String\(speed\)\)/,
    "js/logo-animation.js saves the picked speed",
  );
  assert.match(
    controls,
    /localStorage\.setItem\(PAUSED_KEY, paused \? "1" : "0"\)/,
    "js/logo-animation.js saves the paused state",
  );
  assert.match(
    controls,
    /new CustomEvent\("meta-trio-logo-speed"/,
    "js/logo-animation.js dispatches the speed to the background",
  );
  assert.match(
    controls,
    /new CustomEvent\("meta-trio-logo-paused"/,
    "js/logo-animation.js dispatches the pause to the background",
  );
  assert.match(
    bg,
    /window\.addEventListener\("meta-trio-logo-speed"/,
    "js/logo-background.js listens for the speed event",
  );
  assert.match(
    bg,
    /window\.addEventListener\("meta-trio-logo-paused"/,
    "js/logo-background.js listens for the pause event",
  );
  assert.match(
    bg,
    /localStorage\.getItem\(LOGO_SPEED_KEY\)/,
    "js/logo-background.js re-reads the saved speed on load",
  );
  assert.match(
    bg,
    /localStorage\.getItem\(LOGO_PAUSED_KEY\) === "1"/,
    "js/logo-background.js re-reads the saved pause on load",
  );
});

test("speed maps 25% to the usual drift; pause gates the loop without touching the other pauses", () => {
  assert.match(
    bg,
    /var speedStep = 0\.0022;/,
    "background still defaults to the usual slow drift",
  );
  assert.match(
    bg,
    /speedStep = \(value \/ 25\) \* 0\.0022;/,
    "25% reproduces the usual drift, 0% is still, 100% is four times it",
  );
  assert.match(
    bg,
    /if \(!reducedMotion && !userPaused\) angleY \+= speedStep;/,
    "background advances only when motion is allowed and the user has not paused",
  );
  assert.match(
    bg,
    /if \(running && !reducedMotion && !userPaused\) requestAnimationFrame\(renderFrame\);/,
    "background loop stops on a user pause, like it stops when hidden",
  );
  assert.match(
    bg,
    /if \(!paused && running && !reducedMotion\) requestAnimationFrame\(renderFrame\);/,
    "resuming restarts the loop only when the tab is visible",
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
  assert.match(
    controls,
    /No\n\/\/ keyboard shortcut/,
    "controls say plainly why there is no Space shortcut",
  );
});
