// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-color.test.mjs
//
// LOGO-NATIVE-1 (Del direction, Oct 30): native parity for Hana's
// web LOGO-1 panel. The Mac console had no logo background at all,
// so this slice adds both halves: a dim ASCII loop behind the
// panels and a Logo panel with the studio presets, a custom picker,
// persistence, and Reset. Static checks on the shipped Swift only:
// no Swift toolchain exists in this sandbox, so no Mac build run is
// claimed. Speed and pause controls stay in the web studio for the
// follow-up slice, exactly as Hana scoped the web panel.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const logoColor = readFileSync(
  new URL("../native/Sources/MetaTrio/Models/LogoColor.swift", import.meta.url),
  "utf8",
);
const loopView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoLoopView.swift", import.meta.url),
  "utf8",
);
const panel = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
  "utf8",
);
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

test("logo: shared storage key matches the web panel", () => {
  assert.ok(logoColor.includes('storageKey = "meta-trio-logo-color"'));
  assert.ok(loopView.includes('@AppStorage("meta-trio-logo-color")'));
  assert.ok(panel.includes('@AppStorage("meta-trio-logo-color")'));
});

test("logo: all six studio presets, same hexes as the web panel", () => {
  for (const [name, hex] of [
    ["Meta blue", "#1877f2"],
    ["Cyan", "#00c8ff"],
    ["Violet", "#8b5cf6"],
    ["Pink", "#ff4f9a"],
    ["Emerald", "#20d6a3"],
    ["Gold", "#ffbd4a"],
  ]) {
    assert.ok(logoColor.includes(`("${name}", "${hex}")`), `missing preset ${name}`);
  }
});

test("logo: 9-step ramp build mirrors the web amounts and anchors", () => {
  for (const amount of ["0.88", "0.72", "0.53", "0.31", "0.18", "0.38", "0.62", "0.9"]) {
    assert.ok(logoColor.includes(amount), `missing ramp amount ${amount}`);
  }
  assert.ok(logoColor.includes('"#020817"'));
  assert.ok(logoColor.includes('"#ffffff"'));
});

test("logo: product palettes verbatim from the web background", () => {
  assert.ok(logoColor.includes('"#4f7ec2"'), "vigiles accent in palette");
  assert.ok(logoColor.includes('"#d92b2b"'), "ignis accent in palette");
  assert.ok(logoColor.includes('"#5da864"'), "medicus accent in palette");
  assert.ok(logoColor.includes("case .vigiles"));
  assert.ok(logoColor.includes("case .ignis"));
  assert.ok(logoColor.includes("case .medicus"));
});

test("logo: loop uses the web glyph set, animates by phase, still on reduced motion", () => {
  assert.ok(logoColor.includes('glyphs = " .,:;irsXA253hMHGS#9B&@"'));
  assert.ok(loopView.includes("TimelineView(.animation)"));
  assert.ok(loopView.includes("accessibilityReduceMotion"));
  assert.ok(loopView.includes("? 0"), "reduced motion pins phase to a still frame");
  assert.ok(loopView.includes(".accessibilityHidden(true)"));
  assert.ok(loopView.includes(".allowsHitTesting(false)"));
});

test("logo: custom color wins over product switches, reset returns product tint", () => {
  assert.ok(loopView.includes("isValidHex(customHex)"));
  assert.ok(loopView.includes("buildPalette(baseHex: customHex.lowercased())"));
  assert.ok(loopView.includes("productPalette(for: model.selectedProduct)"));
  assert.ok(panel.includes('Button("Reset to product color")'));
  assert.ok(panel.includes('customHex = ""'));
});

test("logo: panel has picker, value line, and follow-up note", () => {
  assert.ok(panel.includes('ColorPicker("Custom logo color"'));
  assert.ok(panel.includes('"Logo color: product color"'));
  assert.ok(panel.includes("Logo color: \\(customHex.uppercased())"));
  assert.ok(panel.includes("stay in the web studio for the follow-up slice"));
});

test("logo: console wires the loop behind the panels and the panel into the left column", () => {
  assert.ok(contentView.includes("LogoLoopView(model: model)"));
  assert.ok(contentView.includes("LogoColorPanel(model: model)"));
  assert.ok(contentView.includes("ZStack(alignment: .topLeading)"));
});
