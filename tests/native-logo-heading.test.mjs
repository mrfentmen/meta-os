// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-heading.test.mjs
//
// LOGO-NATIVE-3 (Del direction, Oct 30): native parity for the
// web OPS-CONSOLE panel headings, for the Logo panel. The Logo
// panel was the one panel still carrying a plain 15pt bold title,
// so under Ignis, Vigiles, or Medicus it missed the console
// heading treatment the web .panel h2 carries for that product.
// This slice wires its title into the shared PanelHeading, which
// already implements all three branches. Static checks on the
// shipped Swift only: no Swift toolchain exists in this sandbox,
// so no Mac build run is claimed. Presets, picker, slider, pause,
// and the large-logo note are untouched.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const panel = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
  "utf8",
);
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

test("logo heading: panel title uses PanelHeading with all three product gates", () => {
  assert.ok(
    panel.includes(
      'PanelHeading(title: "Logo", isIgnis: model.selectedProduct == .ignis, isVigiles: model.selectedProduct == .vigiles, isMedicus: model.selectedProduct == .medicus)',
    ),
    "Logo title must call PanelHeading gated by the selected product, like the other panel titles",
  );
});

test("logo heading: plain 15pt bold title is gone", () => {
  assert.ok(!panel.includes('Text("Logo")'), "plain Logo title must not remain");
  assert.ok(
    !panel.includes('Text("Logo")\n                    .font(.system(size: 15, weight: .bold))'),
    "plain 15pt bold Logo title must not remain",
  );
});

test("logo heading: PanelHeading still carries the three web console branches", () => {
  // Ignis: uppercase mono 15pt bold, 1.8pt tracking, red tick.
  assert.ok(contentView.includes("Text(title.uppercased())"));
  assert.ok(contentView.includes(".font(.system(size: 15, weight: .bold, design: .monospaced))"));
  assert.ok(contentView.includes(".tracking(1.8)"));
  assert.ok(contentView.includes("Color(red: 217 / 255, green: 43 / 255, blue: 43 / 255)"));
  // Vigiles: same shape in Vigiles blue.
  assert.ok(contentView.includes("Color(red: 79 / 255, green: 126 / 255, blue: 194 / 255)"));
  // Medicus: uppercase plain 15pt bold, 1.2pt tracking, no tick branch.
  assert.ok(contentView.includes(".font(.system(size: 15, weight: .bold))"));
  assert.ok(contentView.includes(".tracking(1.2)"));
});

test("logo heading: VoiceOver still hears the plain title, and the panel body is untouched", () => {
  assert.ok(
    contentView.includes(".accessibilityLabel(title)"),
    "PanelHeading keeps the original title as the accessibility label",
  );
  assert.ok(panel.includes('ColorPicker("Custom logo color"'), "custom picker untouched");
  assert.ok(panel.includes("Slider("), "speed slider untouched");
  assert.ok(panel.includes('paused ? "Resume logo" : "Pause logo"'), "pause button untouched");
  assert.ok(panel.includes('"Large logo stays in the web studio."'), "large-logo note untouched");
  assert.ok(panel.includes('Button("Reset to product color")'), "reset button untouched");
});
