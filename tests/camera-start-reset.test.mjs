// Node built-in test runner, no dependencies:
//   node --test tests/camera-start-reset.test.mjs
//
// Web + native camera start vs Stop/Reset parity. Starting the camera
// awaits the permission prompt, so a Stop or Reset could land while no
// stream existed yet to stop — and the settling start then attached
// its stream and repainted the stopped view as live. Both frontends
// now carry a start generation: stop bumps it, a start captures it,
// and a stale settle stands down (the web Camera class discards the
// stream; the native service skips the permission callback, the queued
// session start, and a queued facing restart). app.js cannot run in
// node (it needs a DOM), so the web-handler and Swift guards are
// asserted from source, while the Camera class itself is covered by
// behavioural tests in tests/camera.test.mjs.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const service = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/CameraService.swift", import.meta.url),
  "utf8",
);

const webStart = web.slice(
  web.indexOf('els.btnCameraStart.addEventListener("click"'),
  web.indexOf('els.btnCameraStop.addEventListener("click"'),
);
const webStop = web.slice(
  web.indexOf('els.btnCameraStop.addEventListener("click"'),
  web.indexOf('els.cameraFacing.addEventListener("change"'),
);
const webFacing = web.slice(
  web.indexOf('els.cameraFacing.addEventListener("change"'),
  web.indexOf('els.btnAnalysisStart.addEventListener("click"'),
);
const webReset = web.slice(
  web.indexOf('els.btnReset.addEventListener("click"'),
  web.indexOf('els.intervalSeconds.addEventListener("change"'),
);
const nativeStart = service.slice(
  service.indexOf("func start() {"),
  service.indexOf("func stop() {"),
);
const nativeStop = service.slice(
  service.indexOf("func stop() {"),
  service.indexOf("func setFacing("),
);
const nativeFacing = service.slice(
  service.indexOf("func setFacing("),
  service.indexOf("private func device("),
);
const nativeConfigure = service.slice(
  service.indexOf("private func configureAndStart()"),
  service.indexOf("private func setState("),
);

test("web: Stop and Reset both bump the camera-start generation", () => {
  assert.match(webStop, /cameraStartGeneration \+= 1;/);
  assert.match(webReset, /cameraStartGeneration \+= 1;/);
});

test("web: Start captures the generation and stands down stale on success and on failure", () => {
  assert.match(webStart, /const startGeneration = cameraStartGeneration;/);
  const guards = webStart.match(
    /if \(startGeneration !== cameraStartGeneration\) return;/g,
  );
  assert.ok(
    guards && guards.length >= 2,
    `expected a stale guard after the start await and in its catch; found ${guards ? guards.length : 0}`,
  );
});

test("web: facing restart captures the generation and stands down stale", () => {
  assert.match(webFacing, /const switchGeneration = cameraStartGeneration;/);
  const guards = webFacing.match(
    /if \(switchGeneration !== cameraStartGeneration\) return;/g,
  );
  assert.ok(
    guards && guards.length >= 2,
    `expected a stale guard after the switch await and in its catch; found ${guards ? guards.length : 0}`,
  );
});

test("native: stop bumps the start generation", () => {
  assert.match(nativeStop, /startGeneration \+= 1/);
});

test("native: start captures the generation and its permission callback stands down stale", () => {
  assert.match(nativeStart, /let generation = startGeneration/);
  assert.match(nativeStart, /guard generation == self\.startGeneration else \{ return \}/);
});

test("native: a queued session start stands down when its generation is stale", () => {
  assert.match(nativeConfigure, /let generation = startGeneration/);
  assert.match(nativeConfigure, /guard generation == self\.startGeneration else \{ return \}/);
});

test("native: a queued facing restart stands down when its generation is stale", () => {
  assert.match(nativeFacing, /let generation = startGeneration/);
  assert.match(nativeFacing, /guard generation == self\.startGeneration else \{ return \}/);
});
