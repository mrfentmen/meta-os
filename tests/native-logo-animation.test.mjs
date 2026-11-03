// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-animation.test.mjs
//
// LOGO-NATIVE-2 (Del direction, Oct 30): native parity for Hana's
// web LOGO-2 panel. The Mac Logo panel gained the studio's
// rotation speed slider and pause button, driving LogoLoopView
// live through the web panel's own storage keys.
//
// UPDATED 2026-11-01 (boss order): the LOGO-1 color section is
// removed everywhere, and with it the native Logo panel file
// (LogoColorPanel.swift carried the color controls, the slider,
// and the pause button in one view). The speed/pause behaviour
// itself survives where it lives now: LogoLoopView still reads
// the web panel's speed/paused storage keys and drives the loop
// from them, and the web console panel keeps the actual slider
// and pause button (index.html + js/logo-animation.js). These
// checks assert that split, plus the panel's absence, instead of
// the deleted panel's contents.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const loopView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoLoopView.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const webAnimation = readFileSync(
  new URL("../js/logo-animation.js", import.meta.url),
  "utf8",
);
const panelExists = existsSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
);

test("logo animation: the native Logo panel is removed with the color section", () => {
  assert.equal(panelExists, false, "LogoColorPanel.swift must stay deleted");
  assert.ok(!loopView.includes("LogoColor."), "loop view must not reference the deleted color model");
  assert.ok(!loopView.includes("meta-trio-logo-color"), "loop view must not read the color key");
});

test("logo animation: speed and pause still reach the loop through the web panel's storage keys", () => {
  assert.ok(loopView.includes('@AppStorage("meta-trio-logo-speed")'));
  assert.ok(loopView.includes('@AppStorage("meta-trio-logo-paused")'));
});

test("logo animation: speed scale matches web LOGO-2 (25 default, 0 still, 100 four times)", () => {
  assert.ok(loopView.includes('@AppStorage("meta-trio-logo-speed") private var speedPercent: Int = 25'));
  assert.ok(loopView.includes("min(100, max(0, speedPercent))"), "out-of-range stored speed clamped");
  assert.ok(loopView.includes("Double(clampedSpeed) / 25.0 * 2.0"), "25% is the usual 2 phases a second");
});

test("logo animation: pause holds the last frame, resume restarts from it", () => {
  assert.ok(loopView.includes("if paused { return anchorPhase }"), "paused frame is the frozen anchor");
  assert.ok(loopView.includes(".onChange(of: paused)"), "pause/resume re-bases the anchor");
  assert.ok(loopView.includes("anchorPhase = runningPhase(at: Date())"), "pausing captures the live frame");
});

test("logo animation: speed change re-bases without jumping, paused stays frozen", () => {
  assert.ok(loopView.includes(".onChange(of: speedPercent)"), "speed change re-bases the anchor");
  assert.ok(loopView.includes("if !paused {"), "a speed change while paused leaves the frozen frame alone");
});

test("logo animation: reduced motion still renders one still frame, loop stays untouchable", () => {
  assert.ok(loopView.includes("if reduceMotion { return 0 }"));
  assert.ok(loopView.includes(".accessibilityHidden(true)"));
  assert.ok(loopView.includes(".allowsHitTesting(false)"));
});

test("logo animation: the web panel carries the slider, speed value line, and pause button now", () => {
  assert.ok(web.includes('id="logo-speed"'), "speed slider present on the web panel");
  assert.ok(web.includes('min="0" max="100" value="25"'), "slider spans the web 0-100 range at the 25 default");
  assert.ok(web.includes('id="logo-speed-value"'), "speed value line present");
  assert.ok(web.includes('id="logo-pause"'), "pause button present");
  assert.ok(webAnimation.includes('pauseButton.setAttribute("aria-pressed", String(paused))'));
});

test("logo animation: only the large logo stays in the web studio now", () => {
  assert.ok(web.includes("Open the full logo studio"), "console still links to the studio for the large logo");
});
