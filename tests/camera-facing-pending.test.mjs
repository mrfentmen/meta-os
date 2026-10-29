// Node built-in test runner, no dependencies:
//   node --test tests/camera-facing-pending.test.mjs
//
// Web facing picker during the permission wait. The Start call fixes
// its getUserMedia constraints when it is made, so a facing change
// landing while the permission prompt was up only recorded a choice
// the stream being requested did not use: the picker said rear while
// the camera that attached showed the front view, and nothing ever
// corrected the mismatch. One helper now owns the picker too:
// refreshButtons() disables it while a start is pending, and every
// path that clears the pending flag (the Start settle, Stop, Reset)
// refreshes the buttons, so the picker comes back the moment the wait
// ends. app.js cannot run in node (it needs a DOM), so these are
// static checks on the shipped wiring, in the same style as the other
// Agent 1 tests. Native needs no change: configureAndStart reads the
// facing when permission is granted, so a mid-wait pick there is
// honestly the camera that opens.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const cameraService = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Services/CameraService.swift",
    import.meta.url,
  ),
  "utf8",
);

const refreshButtons = app.slice(
  app.indexOf("function refreshButtons() {"),
  app.indexOf("function describeCameraError"),
);
const startHandler = app.slice(
  app.indexOf('els.btnCameraStart.addEventListener("click"'),
  app.indexOf('els.btnCameraStop.addEventListener("click"'),
);
const stopHandler = app.slice(
  app.indexOf('els.btnCameraStop.addEventListener("click"'),
  app.indexOf('els.cameraFacing.addEventListener("change"'),
);
const resetHandler = app.slice(
  app.indexOf('els.btnReset.addEventListener("click"'),
  app.indexOf('els.intervalSeconds.addEventListener("change"'),
);

test("web: refreshButtons disables the facing picker while a start is pending", () => {
  assert.match(
    refreshButtons,
    /els\.cameraFacing\.disabled = cameraStartPending;/,
  );
});

test("web: no direct facing-picker disable outside refreshButtons", () => {
  const withoutRefresh = app.replace(refreshButtons, "");
  assert.doesNotMatch(withoutRefresh, /cameraFacing\.disabled\s*=/);
});

test("web: Stop and Reset clear the pending flag and refresh the buttons, so the picker comes back", () => {
  for (const [name, handler] of [
    ["Stop", stopHandler],
    ["Reset", resetHandler],
  ]) {
    const clearAt = handler.indexOf("cameraStartPending = false;");
    const refreshAt = handler.indexOf("refreshButtons();");
    assert.notEqual(clearAt, -1, `${name} handler is missing its pending-flag clear`);
    assert.ok(clearAt < refreshAt, `${name} must refresh the buttons after clearing the flag`);
  }
});

test("web: the Start settle clears the pending flag and refreshes the buttons", () => {
  const clearAt = startHandler.indexOf("cameraStartPending = false;");
  const refreshAt = startHandler.indexOf("refreshButtons();", clearAt);
  assert.notEqual(clearAt, -1, "Start handler is missing its pending-flag clear");
  assert.notEqual(refreshAt, -1, "Start settle must refresh the buttons after clearing the flag");
});

test("native: configureAndStart reads the facing when permission is granted, so a mid-wait pick applies", () => {
  const configure = cameraService.slice(
    cameraService.indexOf("private func configureAndStart() {"),
  );
  assert.match(configure, /device\(for: self\.facing\)/);
});
