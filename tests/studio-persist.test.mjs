// Node built-in test runner, no dependencies:
//   node --test tests/studio-persist.test.mjs
//
// HANA Agent1: STUDIO-PERSIST — the full logo studio page (the one
// the console Logo panel links to) used to keep its color, speed,
// and pause choices for its own visit only, so a color picked in
// the console was lost the moment the studio opened, and a studio
// choice never came back to the console. Now the studio reads and
// writes the console panel's own storage keys, so the two pages
// agree. Nothing saved means the studio keeps its own defaults
// (Meta blue, 30%, playing); an invalid saved value is ignored,
// never trusted. The studio page has no build step and no Swift
// equivalent, so these are static checks over its shipped source,
// the same pattern as the other logo tests.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const studio = readFileSync(
  new URL("../design/meta-ascii-logo-studio.html", import.meta.url),
  "utf8",
);
const panel = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("studio shares the console Logo panel's storage keys", () => {
  for (const key of [
    "meta-trio-logo-color",
    "meta-trio-logo-speed",
    "meta-trio-logo-paused",
  ]) {
    assert.ok(
      studio.includes(key),
      `studio references the console key ${key}`,
    );
  }
  assert.match(
    panel,
    /Open the full logo studio/,
    "console Logo panel still links to the full studio page",
  );
});

test("studio restores saved choices before the first frame", () => {
  assert.match(
    studio,
    /setAccentColor\(savedColor \|\| DEFAULT_ACCENT\);/,
    "saved color (or the studio default) is applied at startup",
  );
  assert.match(
    studio,
    /speedSlider\.value = String\(savedSpeed\);/,
    "saved speed is applied to the slider at startup",
  );
  assert.match(
    studio,
    /setPaused\(storedPaused\(\)\);/,
    "saved pause state is applied at startup (STUDIO-STATUS form: setPaused runs either way, so a Reduce Motion open also refreshes the status)",
  );
  const startup = studio.indexOf("setAccentColor(savedColor");
  const firstFrame = studio.indexOf("renderFrame();", startup);
  assert.ok(
    startup !== -1 && firstFrame !== -1 && firstFrame > startup,
    "restore runs before the first rendered frame",
  );
});

test("studio saves every choice it lets the user change", () => {
  assert.match(
    studio,
    /speedSlider\.addEventListener\('input', \(\) => \{[\s\S]*?saveStored\(LOGO_SPEED_KEY, speedSlider\.value\);/s,
    "speed slider input saves the speed key",
  );
  assert.match(
    studio,
    /pauseButton\.addEventListener\('click', \(\) => \{[\s\S]*?saveStored\(LOGO_PAUSED_KEY, isPaused \? '1' : '0'\);/s,
    "pause button saves the paused key",
  );
  assert.match(
    studio,
    /event\.code === 'Space'\) \{ setPaused\(!isPaused\); saveStored\(LOGO_PAUSED_KEY, isPaused \? '1' : '0'\);/,
    "Space pause toggle saves the paused key",
  );
  assert.match(
    studio,
    /colorPicker\.addEventListener\('input', event => \{[\s\S]*?saveStored\(LOGO_COLOR_KEY, colorPicker\.value\);/s,
    "custom picker input saves the color key",
  );
  assert.match(
    studio,
    /swatch\.addEventListener\('click', \(\) => \{[\s\S]*?saveStored\(LOGO_COLOR_KEY, colorPicker\.value\);/s,
    "preset swatch click saves the color key",
  );
});

test("invalid saved values are ignored, studio defaults unchanged", () => {
  assert.match(
    studio,
    /\/\^#\[0-9a-f\]\{6\}\$\/i\.test\(value \|\| ''\)/,
    "a saved color must be a six-digit hex or it is dropped",
  );
  assert.match(
    studio,
    /Number\.isFinite\(parsed\) \? Math\.max\(0, Math\.min\(100, Math\.round\(parsed\)\)\) : null/,
    "a saved speed must be a finite number, clamped to 0-100, or it is dropped",
  );
  assert.match(
    studio,
    /const DEFAULT_ACCENT = '#1877f2';/,
    "studio default color is still Meta blue",
  );
  assert.match(
    studio,
    /<input type="range" id="speed" min="0" max="100" value="30"/,
    "studio default speed is still 30%",
  );
});
