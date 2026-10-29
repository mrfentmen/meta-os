// Node built-in test runner, no dependencies:
//   node --test tests/camera-stop-pending.test.mjs
//
// Stop button during the camera-permission wait. The Stop handler on
// both frontends already knew how to cancel a pending start — the web
// handler clears the pending flag and bumps the start generation, and
// the native stopCamera bumps CameraService's start generation so the
// permission callback stands down — but the Stop button itself was
// disabled exactly during that wait: on the web it was disabled
// whenever the camera was not live, and on native whenever the camera
// state was not running, and a start still awaiting the permission
// prompt is neither live nor running. So the cancel path was dead,
// and the only way to abandon the wait was Reset (web) or Reset
// Session (native), which also clears the latest assessment and the
// history/timeline. Stop now stays enabled while a start is pending
// (web) or permission is requested (native), so cancelling the wait
// leaves the view alone: the stale start settle touches nothing, and
// the camera class discards the stream if permission is granted after
// the stop. app.js cannot run in node (it needs a DOM) and Swift
// cannot run in this sandbox, so these are static checks on the
// shipped wiring, in the same style as the other Agent 1 tests.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const camera = readFileSync(new URL("../js/camera.js", import.meta.url), "utf8");
const view = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
    import.meta.url,
  ),
  "utf8",
);
const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const cameraService = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/CameraService.swift", import.meta.url),
  "utf8",
);

const refreshButtons = app.slice(
  app.indexOf("function refreshButtons() {"),
  app.indexOf("function describeCameraError"),
);
const stopHandler = app.slice(
  app.indexOf('els.btnCameraStop.addEventListener("click"'),
  app.indexOf('els.cameraFacing.addEventListener("change"'),
);
const stopCameraBody = model.slice(
  model.indexOf("func stopCamera() {"),
  model.indexOf("// MARK: - Analysis controls"),
);

test("web: refreshButtons enables Stop while a start is pending, not only while live", () => {
  assert.match(
    refreshButtons,
    /els\.btnCameraStop\.disabled = !camActive && !cameraStartPending;/,
  );
});

test("web: no direct Stop disable outside refreshButtons", () => {
  const withoutRefresh = app.replace(refreshButtons, "");
  assert.doesNotMatch(withoutRefresh, /btnCameraStop\.disabled\s*=/);
});

test("web: Stop is still disabled with no camera live and no start pending", () => {
  // The new condition disables Stop only when both are false, so a
  // camera-less browser (pending false, live false) still offers no
  // Stop tap that could do anything.
  assert.match(
    refreshButtons,
    /els\.btnCameraStop\.disabled = !camActive && !cameraStartPending;/,
  );
  assert.match(
    refreshButtons,
    /els\.btnCameraStart\.disabled = camActive \|\| cameraStartPending \|\| cameraUnsupported;/,
  );
});

test("web: the Stop handler cancels a pending start before refreshing", () => {
  const generationAt = stopHandler.indexOf("cameraStartGeneration += 1;");
  const flagAt = stopHandler.indexOf("cameraStartPending = false;");
  const refreshAt = stopHandler.indexOf("refreshButtons();");
  assert.notEqual(generationAt, -1, "Stop handler is missing its generation bump");
  assert.notEqual(flagAt, -1, "Stop handler is missing its pending-flag clear");
  assert.ok(generationAt < refreshAt, "the generation must bump before the button refreshes");
  assert.ok(flagAt < refreshAt, "the flag must clear before the button refreshes");
});

test("web: Camera.stop invalidates a start still awaiting permission", () => {
  const stopBody = camera.slice(
    camera.indexOf("  stop() {"),
    camera.indexOf("  // Draws the current video frame"),
  );
  assert.match(stopBody, /this\._startGeneration \+= 1;/);
});

test("native: Stop stays enabled while permission is requested, not only while running", () => {
  assert.match(
    view,
    /\.disabled\(camera\.state != \.running && camera\.state != \.requestingPermission\)/,
  );
});

test("native: stopCamera stops the camera, whose stop bumps the start generation", () => {
  assert.match(stopCameraBody, /camera\.stop\(\)/);
  const cameraStopBody = cameraService.slice(
    cameraService.indexOf("    func stop() {"),
    cameraService.indexOf("    /// Records a new facing."),
  );
  assert.match(cameraStopBody, /startGeneration \+= 1/);
  // The permission callback stands down on a bumped generation, so a
  // grant after this Stop starts nothing.
  assert.match(
    cameraService,
    /guard generation == self\.startGeneration else \{ return \}/,
  );
});
