// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-accessibility.test.mjs
//
// LOGO-NATIVE-4 (Del direction, Oct 30): VoiceOver state parity
// for the web LOGO-1/LOGO-2 aria-pressed states, for the native
// Logo panel: the chosen preset carried the isSelected trait and
// the pause button a Paused/Playing value, so the spoken state
// followed the stored state exactly.
//
// UPDATED 2026-11-01 (boss order): the LOGO-1 color section is
// removed everywhere. The web swatches and their aria-pressed
// toggles are gone with js/logo-color.js, and the native Logo
// panel file (LogoColorPanel.swift) is deleted. What survives:
// the web pause button still toggles aria-pressed (LOGO-2), and
// LogoLoopView still speaks no state of its own (hidden from
// accessibility, as before). These checks pin that split.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const web = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const webAnimation = readFileSync(
  new URL("../js/logo-animation.js", import.meta.url),
  "utf8",
);
const loopView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoLoopView.swift", import.meta.url),
  "utf8",
);
const panelExists = existsSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
);
const colorControlsExist = existsSync(
  new URL("../js/logo-color.js", import.meta.url),
);

test("logo accessibility: the web swatch states are gone with the color controls", () => {
  assert.equal(colorControlsExist, false, "js/logo-color.js must stay deleted");
  assert.ok(!web.includes("logo-swatch"), "no swatches remain in the web panel");
  assert.ok(!web.includes("data-logo-color"), "no swatch color data remains");
});

test("logo accessibility: the web pause button still toggles aria-pressed", () => {
  assert.ok(webAnimation.includes('pauseButton.setAttribute("aria-pressed", String(paused))'));
  assert.ok(web.includes('id="logo-pause"'), "pause button untouched");
});

test("logo accessibility: the native Logo panel is removed with the color section", () => {
  assert.equal(panelExists, false, "LogoColorPanel.swift must stay deleted");
  assert.ok(!loopView.includes("accessibilityAddTraits"), "no preset trait remains in the loop view");
});

test("logo accessibility: the loop view stays hidden from accessibility, as before", () => {
  assert.ok(loopView.includes(".accessibilityHidden(true)"));
  assert.ok(loopView.includes(".allowsHitTesting(false)"));
});
