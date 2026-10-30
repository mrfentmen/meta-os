// Node built-in test runner, no dependencies:
//   node --test tests/studio-reset.test.mjs
//
// HANA Agent1: STUDIO-RESET — the full logo studio's Reset button
// used to reset rotation only: it re-homed the angles and resumed
// playback, but left the picked color, the speed, and all three
// shared saved keys untouched. Since STUDIO-PERSIST, a reload
// after Reset therefore resurrected the old color and speed —
// Reset looked like it worked and then quietly undid itself.
// Now Reset restores the studio defaults (Meta blue, 30%,
// playing, rotation home) and clears the shared keys, so a reload
// after Reset shows the defaults, and the console panel returns
// to its product color on its next reload too. The shipped root
// studio (logo-studio.html) is untouched — it is the verbatim v2
// file, and this slice does not change it. These are static
// checks over the shipped source, the same pattern as the other
// logo tests; no live browser click is witnessed here.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const studio = readFileSync(
  new URL("../design/meta-ascii-logo-studio.html", import.meta.url),
  "utf8",
);
const rootStudio = readFileSync(
  new URL("../logo-studio.html", import.meta.url),
  "utf8",
);

test("studio Reset restores color, speed, pause, and rotation", () => {
  const handler = studio.slice(
    studio.indexOf("getElementById('reset-button')"),
  );
  const block = handler.slice(0, handler.indexOf("});") + 2);
  assert.match(block, /resetRotation\(\);/, "Reset still re-homes rotation");
  assert.match(block, /setPaused\(false\);/, "Reset resumes playback");
  assert.match(
    block,
    /setAccentColor\(DEFAULT_ACCENT\);/,
    "Reset returns the color to the studio default",
  );
  assert.match(
    block,
    /speedSlider\.value = '30';/,
    "Reset returns the speed slider to the studio default",
  );
  assert.match(
    block,
    /speedValue\.textContent = '30%';/,
    "Reset updates the speed readout to the studio default",
  );
});

test("studio Reset clears the shared saved keys", () => {
  assert.match(
    studio,
    /function clearStored\(key\) \{[\s\S]*?window\.localStorage\.removeItem\(key\);/s,
    "studio has a clearStored helper that removes a key",
  );
  const handler = studio.slice(
    studio.indexOf("getElementById('reset-button')"),
  );
  const block = handler.slice(0, handler.indexOf("});") + 2);
  for (const key of ["LOGO_COLOR_KEY", "LOGO_SPEED_KEY", "LOGO_PAUSED_KEY"]) {
    assert.match(
      block,
      new RegExp(`clearStored\\(${key}\\);`),
      `Reset clears ${key}`,
    );
  }
  assert.doesNotMatch(
    block,
    /saveStored\(LOGO_PAUSED_KEY, '0'\);/,
    "Reset no longer re-saves a paused value after clearing",
  );
});

test("studio Reset button says what it resets", () => {
  assert.match(
    studio,
    /<button id="reset-button" type="button" aria-label="Reset logo settings" title="Reset color, speed, rotation, and pause">/,
    "Reset button label and title describe the full reset, not rotation only",
  );
  assert.doesNotMatch(
    studio,
    /aria-label="Reset rotation"/,
    "no rotation-only Reset label remains in the studio",
  );
});

test("studio defaults and shipped root studio are unchanged", () => {
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
  assert.ok(
    !rootStudio.includes("clearStored"),
    "logo-studio.html carries no clearStored helper — the verbatim v2 file is unchanged",
  );
});
