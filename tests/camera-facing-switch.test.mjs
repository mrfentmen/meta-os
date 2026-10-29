// Node built-in test runner, no dependencies:
//   node --test tests/camera-facing-switch.test.mjs
//
// Web facing picker during a live facing switch. A live switch stops
// the stream, then awaits a start fixed to the facing chosen when the
// switch began — and a second change landing in that window only
// records, because switchFacing takes its record-only path while the
// camera is not active (its stream is stopped): the picker would say
// the new facing while the stream that attaches shows the old one,
// and nothing would ever correct the mismatch. One helper now owns
// the picker for this window too: refreshButtons() disables it while
// a switch is pending, the switch's own settle clears the flag in
// finally (so a stale settle after Stop or Reset brings it back),
// and Stop and Reset clear it directly so the picker comes back at
// once. app.js cannot run in node (it needs a DOM), so these are
// static checks on the shipped wiring, in the same style as the other
// Agent 1 tests. Native needs no change: its queued facing restart
// reads the facing when it configures (configureAndStart calls
// device(for: self.facing)), so a pick landing mid-restart is
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
const facingHandler = app.slice(
  app.indexOf('els.cameraFacing.addEventListener("change"'),
  app.indexOf('els.btnAnalysisStart.addEventListener("click"'),
);
const stopHandler = app.slice(
  app.indexOf('els.btnCameraStop.addEventListener("click"'),
  app.indexOf('els.cameraFacing.addEventListener("change"'),
);
const resetHandler = app.slice(
  app.indexOf('els.btnReset.addEventListener("click"'),
  app.indexOf('els.intervalSeconds.addEventListener("change"'),
);

test("web: refreshButtons disables the facing picker while a switch is pending", () => {
  assert.match(
    refreshButtons,
    /els\.cameraFacing\.disabled = cameraStartPending \|\| facingSwitchPending;/,
  );
});

test("web: no direct facing-picker disable outside refreshButtons", () => {
  const withoutRefresh = app.replace(refreshButtons, "");
  assert.doesNotMatch(withoutRefresh, /cameraFacing\.disabled\s*=/);
});

test("web: the facing handler sets the switch flag before awaiting and clears it in finally", () => {
  const setAt = facingHandler.indexOf("facingSwitchPending = true;");
  const awaitAt = facingHandler.indexOf("await camera.switchFacing");
  const finallyAt = facingHandler.indexOf("finally {");
  const clearAt = facingHandler.indexOf("facingSwitchPending = false;", finallyAt);
  const refreshAt = facingHandler.indexOf("refreshButtons();", clearAt);
  assert.notEqual(setAt, -1, "facing handler is missing its switch-flag set");
  assert.ok(setAt < awaitAt, "the flag must be set before the switch await");
  assert.notEqual(finallyAt, -1, "facing handler is missing its finally block");
  assert.notEqual(clearAt, -1, "the switch flag must clear in finally, so a stale settle brings the picker back");
  assert.notEqual(refreshAt, -1, "the switch settle must refresh the buttons after clearing the flag");
});

test("web: Stop and Reset clear the switch flag and refresh the buttons, so the picker comes back at once", () => {
  for (const [name, handler] of [
    ["Stop", stopHandler],
    ["Reset", resetHandler],
  ]) {
    const clearAt = handler.indexOf("facingSwitchPending = false;");
    const refreshAt = handler.indexOf("refreshButtons();");
    assert.notEqual(clearAt, -1, `${name} handler is missing its switch-flag clear`);
    assert.ok(clearAt < refreshAt, `${name} must refresh the buttons after clearing the flag`);
  }
});

test("native: the queued facing restart reads the facing when it configures, so a mid-restart pick applies", () => {
  const setFacing = cameraService.slice(
    cameraService.indexOf("func setFacing("),
    cameraService.indexOf("private func device("),
  );
  assert.match(setFacing, /facing = newFacing/);
  const configure = cameraService.slice(
    cameraService.indexOf("private func configureAndStart() {"),
  );
  assert.match(configure, /device\(for: self\.facing\)/);
});
