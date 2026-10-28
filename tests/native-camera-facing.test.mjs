// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-facing.test.mjs
//
// Web <-> native camera-facing parity. The web frontend (index.html
// select + js/camera.js) offers front vs rear as a preference, never an
// exact requirement, records the choice while off, and restarts the
// stream while live. The native Mac app must do the same, and this test
// reads the Swift sources (it cannot run Swift in this sandbox) to
// assert it: a Facing enum with front/rear mapping to .front/.back, a
// default of front, a fallback to the default camera when no device sits
// at the chosen position, a setFacing that restarts a live capture, and
// a picker in ContentView carrying the web picker's labels plus the
// plain-words note that a facing is a preference.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const service = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/CameraService.swift", import.meta.url),
  "utf8",
);
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const webPage = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("native: facing enum has front and rear, mapping to .front and .back", () => {
  assert.match(service, /enum Facing: String, CaseIterable \{\s*case front\s*case rear/);
  assert.match(service, /case \.front: return \.front/);
  assert.match(service, /case \.rear: return \.back/);
});

test("native: facing defaults to front", () => {
  assert.match(service, /@Published private\(set\) var facing: Facing = \.front/);
});

test("native: device lookup prefers the chosen position, falls back to the default camera", () => {
  assert.match(service, /private func device\(for facing: Facing\)/);
  assert.match(service, /position: facing\.avPosition/);
  assert.match(service, /discovery\.devices\.first \?\? AVCaptureDevice\.default\(for: \.video\)/);
});

test("native: start uses the chosen facing, not the bare default camera", () => {
  assert.match(service, /guard let device = self\.device\(for: self\.facing\)/);
  assert.doesNotMatch(service, /guard let device = AVCaptureDevice\.default\(for: \.video\)/);
});

test("native: setFacing records the choice and restarts a live capture", () => {
  const start = service.indexOf("func setFacing(_ newFacing: Facing)");
  assert.notEqual(start, -1, "CameraService is missing setFacing");
  const block = service.slice(start, service.indexOf("\n    /// The device at", start));
  assert.match(block, /facing = newFacing/);
  assert.match(block, /guard isRunning else \{ return \}/);
  assert.match(block, /self\.session\.stopRunning\(\)/);
  assert.match(block, /self\.session\.removeInput\(input\)/);
  assert.match(block, /self\.configured = false/);
  assert.match(block, /self\?\.start\(\)/);
});

test("native: picker offers both facings with the web picker's labels", () => {
  assert.match(service, /case \.front: return "Front-facing \(selfie view\)"/);
  assert.match(service, /case \.rear: return "Rear-facing \(point the phone at the scene\)"/);
  assert.match(contentView, /Picker\("Camera facing"/);
  assert.match(contentView, /camera\.setFacing\(\$0\)/);
  assert.match(contentView, /Text\(facing\.label\)\.tag\(facing\)/);
  // The web page carries the same two labels, word for word.
  assert.match(webPage, /Front-facing \(selfie view\)/);
  assert.match(webPage, /Rear-facing \(point the phone at the scene\)/);
});

test("native: picker says plainly that a facing is a preference, not a requirement", () => {
  assert.match(
    contentView,
    /A facing is a preference, not a requirement: a Mac with only one camera uses that camera whichever facing is chosen\./,
  );
});
