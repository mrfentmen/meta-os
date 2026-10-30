// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-accessibility.test.mjs
//
// LOGO-NATIVE-4 (Del direction, Oct 30): VoiceOver state parity
// for the web LOGO-1/LOGO-2 aria-pressed states, for the native
// Logo panel. The web swatches toggle aria-pressed and the web
// pause button toggles aria-pressed, but the native panel only
// showed the state visually, so VoiceOver never heard which
// preset was chosen or whether the loop was paused. Static
// checks on the shipped Swift only: no Swift toolchain exists in
// this sandbox, so no Mac build run is claimed. Heading, presets,
// picker, value lines, slider, pause label, and the large-logo
// note are untouched.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const panel = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
  "utf8",
);
const webColor = readFileSync(
  new URL("../js/logo-color.js", import.meta.url),
  "utf8",
);
const webAnimation = readFileSync(
  new URL("../js/logo-animation.js", import.meta.url),
  "utf8",
);

test("logo accessibility: web states being matched are the aria-pressed toggles", () => {
  assert.ok(webColor.includes('swatch.setAttribute("aria-pressed", String(selected))'));
  assert.ok(webAnimation.includes('pauseButton.setAttribute("aria-pressed", String(paused))'));
});

test("logo accessibility: chosen preset carries isSelected, gated by the same match as its ring", () => {
  assert.ok(
    panel.includes(".accessibilityAddTraits(customHex.lowercased() == preset.hex ? .isSelected : [])"),
    "chosen preset must carry isSelected, and no other preset must",
  );
  assert.ok(
    panel.includes("lineWidth: customHex.lowercased() == preset.hex ? 2 : 0"),
    "the white ring still keys on the same saved-hex match",
  );
  assert.ok(panel.includes(".accessibilityLabel(preset.name)"), "preset name label untouched");
});

test("logo accessibility: pause button carries a Paused/Playing value from the stored pause flag", () => {
  assert.ok(
    panel.includes('.accessibilityValue(paused ? "Paused" : "Playing")'),
    "pause button must speak its state from the same paused flag that drives its label",
  );
  assert.ok(panel.includes('paused ? "Resume logo" : "Pause logo"'), "pause label untouched");
  assert.ok(panel.includes("paused.toggle()"), "pause action untouched");
});

test("logo accessibility: panel body otherwise untouched", () => {
  assert.ok(panel.includes('PanelHeading(title: "Logo"'), "Logo heading untouched");
  assert.ok(panel.includes('ColorPicker("Custom logo color"'), "custom picker untouched");
  assert.ok(panel.includes('"Logo color: \\(customHex.uppercased())"'), "color value line untouched");
  assert.ok(panel.includes('Button("Reset to product color")'), "reset button untouched");
  assert.ok(panel.includes("Slider("), "speed slider untouched");
  assert.ok(panel.includes('"Rotation speed: \\(min(100, max(0, speedPercent)))%"'), "speed value line untouched");
  assert.ok(panel.includes('"Large logo stays in the web studio."'), "large-logo note untouched");
});
