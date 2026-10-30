// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-tooltips.test.mjs
//
// LOGO-NATIVE-6 (Del direction, Oct 30): the native Logo panel's
// preset swatches gain their hover names, the counterpart to the
// web swatches' title attributes. Until now a native swatch was
// only a colored circle: VoiceOver heard its name, but a sighted
// Mac user hovering it got no name, while the web swatch shows
// its title on hover. Static checks on the shipped Swift only:
// no Swift toolchain exists in this sandbox, so no Mac build run
// is claimed. Heading, intro, picker, value lines, slider, pause
// button, pause spoken state, and the large-logo note are
// untouched.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const panel = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const model = readFileSync(
  new URL("../native/Sources/MetaTrio/Models/LogoColor.swift", import.meta.url),
  "utf8",
);

const presets = [
  ["Meta blue", "#1877f2"],
  ["Cyan", "#00c8ff"],
  ["Violet", "#8b5cf6"],
  ["Pink", "#ff4f9a"],
  ["Emerald", "#20d6a3"],
  ["Gold", "#ffbd4a"],
];

test("logo tooltips: web swatches being matched carry a hover title per preset", () => {
  for (const [name, hex] of presets) {
    assert.ok(
      web.includes(`data-logo-color="${hex}"`) && web.includes(`title="${name}"`),
      `web swatch ${name} must carry its title`,
    );
  }
});

test("logo tooltips: native presets carry the same six names as the web titles", () => {
  for (const [name, hex] of presets) {
    assert.ok(
      model.includes(`("${name}", "${hex}")`),
      `native preset list must carry ${name} at ${hex}`,
    );
  }
});

test("logo tooltips: native preset buttons carry a hover name from the preset itself", () => {
  const loopAt = panel.indexOf("ForEach(LogoColor.presets");
  assert.ok(loopAt !== -1, "preset loop must exist");
  const loop = panel.slice(loopAt);
  assert.ok(loop.includes(".help(preset.name)"), "preset button must carry .help(preset.name)");
  assert.ok(
    loop.includes(".accessibilityLabel(preset.name)"),
    "hover name must come from the same preset name as the spoken label",
  );
  assert.ok(!loop.includes('.help("'), "hover name must not be a hardcoded string");
});

test("logo tooltips: panel body otherwise untouched", () => {
  assert.ok(panel.includes('PanelHeading(title: "Logo"'), "Logo heading untouched");
  assert.ok(panel.includes("choices are saved on this Mac"), "intro untouched");
  assert.ok(panel.includes('ColorPicker("Custom logo color"'), "custom picker untouched");
  assert.ok(panel.includes("Logo color: ") && panel.includes("customHex.uppercased()"), "color value line untouched");
  assert.ok(panel.includes('Button("Reset to product color")'), "reset button untouched");
  assert.ok(panel.includes("Slider("), "speed slider untouched");
  assert.ok(panel.includes("Rotation speed: ") && panel.includes("min(100, max(0, speedPercent))"), "speed value line untouched");
  assert.ok(panel.includes('paused ? "Resume logo" : "Pause logo"'), "pause label untouched");
  assert.ok(panel.includes('.accessibilityValue(paused ? "Paused" : "Playing")'), "pause spoken state untouched");
  assert.ok(panel.includes('"Large logo stays in the web studio."'), "large-logo note untouched");
});
