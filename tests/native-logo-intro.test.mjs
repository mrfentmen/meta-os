// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-intro.test.mjs
//
// LOGO-NATIVE-5 (Del direction, Oct 30): the native Logo panel
// gained its intro note, the counterpart to the web panel's
// opening paragraph, so a Mac user met the controls with a
// sentence saying what the loop is and that the choices persist.
//
// UPDATED 2026-11-01 (boss order): the LOGO-1 color section is
// removed everywhere. The web panel's intro no longer mentions
// picking a color or Reset, and the native Logo panel file
// (LogoColorPanel.swift) is deleted, so there is no native
// intro left to match. These checks pin the web panel's new
// intro wording and the panel's absence.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const web = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const panelExists = existsSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
);

test("logo intro: web panel opens with its intro paragraph, speed and pause only", () => {
  assert.ok(
    web.includes("The spinning ASCII Meta loop behind these panels."),
    "web intro paragraph must exist",
  );
  assert.ok(web.includes("Set its rotation speed or pause it"));
  assert.ok(web.includes("saved in this browser and come back on reload"));
  assert.ok(!web.includes("Pick a color to re-tint it"), "color wording must be gone from the intro");
  assert.ok(!web.includes("Reset returns the color"), "reset wording must be gone from the intro");
});

test("logo intro: the native Logo panel is removed with the color section", () => {
  assert.equal(panelExists, false, "LogoColorPanel.swift must stay deleted");
});

test("logo intro: web panel body otherwise intact", () => {
  assert.ok(web.includes('id="logo-speed"'), "speed slider untouched");
  assert.ok(web.includes('id="logo-speed-value"'), "speed value line untouched");
  assert.ok(web.includes('id="logo-pause"'), "pause button untouched");
  assert.ok(web.includes("Open the full logo studio"), "large-logo link untouched");
  assert.ok(!web.includes('id="logo-color-picker"'), "custom picker gone");
  assert.ok(!web.includes('id="logo-color-reset"'), "reset button gone");
  assert.ok(!web.includes('id="logo-color-value"'), "color value line gone");
});
