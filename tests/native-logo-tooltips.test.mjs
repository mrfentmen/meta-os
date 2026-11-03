// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-tooltips.test.mjs
//
// LOGO-NATIVE-6 (Del direction, Oct 30): the native Logo panel's
// preset swatches gained their hover names, the counterpart to
// the web swatches' title attributes, so a sighted Mac user
// hovering a swatch read the same name a web user read.
//
// UPDATED 2026-11-01 (boss order): the LOGO-1 color section is
// removed everywhere. The web swatches and their titles are gone
// from index.html, and both native files behind the tooltips
// (Models/LogoColor.swift and Views/LogoColorPanel.swift) are
// deleted. These checks pin the absence on both sides, so the
// swatches cannot quietly come back on one surface only.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const web = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const panelExists = existsSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
);
const modelExists = existsSync(
  new URL("../native/Sources/MetaTrio/Models/LogoColor.swift", import.meta.url),
);

const presets = [
  ["Meta blue", "#1877f2"],
  ["Cyan", "#00c8ff"],
  ["Violet", "#8b5cf6"],
  ["Pink", "#ff4f9a"],
  ["Emerald", "#20d6a3"],
  ["Gold", "#ffbd4a"],
];

test("logo tooltips: web swatches and their hover titles are gone", () => {
  for (const [name, hex] of presets) {
    assert.ok(
      !web.includes(`data-logo-color="${hex}"`),
      `web swatch ${name} must stay removed`,
    );
  }
  assert.ok(!web.includes("logo-swatch"), "no swatch markup remains");
});

test("logo tooltips: the native preset model and panel are gone", () => {
  assert.equal(modelExists, false, "LogoColor.swift must stay deleted");
  assert.equal(panelExists, false, "LogoColorPanel.swift must stay deleted");
});

test("logo tooltips: web panel body otherwise intact", () => {
  assert.ok(web.includes('id="logo-speed"'), "speed slider untouched");
  assert.ok(web.includes('id="logo-pause"'), "pause button untouched");
  assert.ok(web.includes("Open the full logo studio"), "large-logo link untouched");
});
