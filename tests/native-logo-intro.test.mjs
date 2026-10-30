// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-intro.test.mjs
//
// LOGO-NATIVE-5 (Del direction, Oct 30): the native Logo panel
// gains its intro note, the counterpart to the web panel's
// opening paragraph. Until now the native panel jumped straight
// from its heading to the swatches, while every other native
// panel carries its intro note at 13pt. Static checks on the
// shipped Swift only: no Swift toolchain exists in this sandbox,
// so no Mac build run is claimed. Heading, presets, picker,
// value lines, slider, pause button, and the large-logo note are
// untouched.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const panel = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../index.html", import.meta.url), "utf8");

const intro =
  "The spinning ASCII Meta loop behind these panels. Pick a color to re-tint it, set its rotation speed, or pause it — the choices are saved on this Mac and come back on relaunch. Reset returns the color to the selected product's color.";

test("logo intro: web panel being matched opens with its intro paragraph", () => {
  assert.ok(
    web.includes("The spinning ASCII Meta loop behind these panels."),
    "web intro paragraph must exist to be matched",
  );
  assert.ok(web.includes("saved in this browser and come back on reload"));
  assert.ok(web.includes("Reset returns the color to the selected product's color."));
});

test("logo intro: native panel carries the intro in Mac words", () => {
  assert.ok(panel.includes(intro), "native intro must carry the web meaning, adapted for the Mac");
  assert.ok(!panel.includes("saved in this browser"), "browser wording must not leak into the Mac panel");
});

test("logo intro: intro sits between the heading and the presets, at 13pt muted with wrapping", () => {
  const headingAt = panel.indexOf('PanelHeading(title: "Logo"');
  const introAt = panel.indexOf(intro);
  const presetsAt = panel.indexOf("ForEach(LogoColor.presets");
  assert.ok(headingAt !== -1 && introAt !== -1 && presetsAt !== -1);
  assert.ok(headingAt < introAt, "intro must follow the panel heading");
  assert.ok(introAt < presetsAt, "intro must precede the preset swatches");
  const styled = panel.slice(introAt, presetsAt);
  assert.ok(styled.includes(".font(.system(size: 13))"), "intro must read at 13pt, the native note size");
  assert.ok(styled.includes(".foregroundStyle(.secondary)"), "intro must be muted");
  assert.ok(
    styled.includes(".fixedSize(horizontal: false, vertical: true)"),
    "intro must wrap instead of clipping",
  );
});

test("logo intro: panel body otherwise untouched", () => {
  assert.ok(panel.includes('PanelHeading(title: "Logo"'), "Logo heading untouched");
  assert.ok(panel.includes("ForEach(LogoColor.presets"), "presets untouched");
  assert.ok(panel.includes('ColorPicker("Custom logo color"'), "custom picker untouched");
  assert.ok(panel.includes("Logo color: ") && panel.includes("customHex.uppercased()"), "color value line untouched");
  assert.ok(panel.includes('Button("Reset to product color")'), "reset button untouched");
  assert.ok(panel.includes("Slider("), "speed slider untouched");
  assert.ok(panel.includes("Rotation speed: ") && panel.includes("min(100, max(0, speedPercent))"), "speed value line untouched");
  assert.ok(panel.includes('paused ? "Resume logo" : "Pause logo"'), "pause label untouched");
  assert.ok(panel.includes('.accessibilityValue(paused ? "Paused" : "Playing")'), "pause spoken state untouched");
  assert.ok(panel.includes('"Large logo stays in the web studio."'), "large-logo note untouched");
});
