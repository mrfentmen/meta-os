// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-animation.test.mjs
//
// LOGO-NATIVE-2 (Del direction, Oct 30): native parity for Hana's
// web LOGO-2 panel. The Mac Logo panel gains the studio's rotation
// speed slider and pause button, driving LogoLoopView live through
// the web panel's own storage keys. Static checks on the shipped
// Swift only: no Swift toolchain exists in this sandbox, so no Mac
// build run is claimed. Only the large logo stays in the web
// studio now.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const loopView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoLoopView.swift", import.meta.url),
  "utf8",
);
const panel = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
  "utf8",
);

test("logo animation: speed and pause share the web panel's storage keys", () => {
  assert.ok(loopView.includes('@AppStorage("meta-trio-logo-speed")'));
  assert.ok(loopView.includes('@AppStorage("meta-trio-logo-paused")'));
  assert.ok(panel.includes('@AppStorage("meta-trio-logo-speed")'));
  assert.ok(panel.includes('@AppStorage("meta-trio-logo-paused")'));
});

test("logo animation: speed scale matches web LOGO-2 (25 default, 0 still, 100 four times)", () => {
  assert.ok(panel.includes('@AppStorage("meta-trio-logo-speed") private var speedPercent: Int = 25'));
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

test("logo animation: panel has slider, speed value line, and pause/resume button", () => {
  assert.ok(panel.includes("Slider("), "speed slider present");
  assert.ok(panel.includes("in: 0...100"), "slider spans the web 0-100 range");
  assert.ok(panel.includes("step: 1"), "slider steps by whole percents");
  assert.ok(panel.includes('"Rotation speed: \\(min(100, max(0, speedPercent)))%"'));
  assert.ok(panel.includes('paused ? "Resume logo" : "Pause logo"'));
  assert.ok(panel.includes("paused.toggle()"));
});

test("logo animation: only the large logo stays in the web studio now", () => {
  assert.ok(panel.includes('"Large logo stays in the web studio."'));
  assert.ok(!panel.includes("rotation speed, and pause controls stay in the web studio"));
});
