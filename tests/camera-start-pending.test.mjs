// Node built-in test runner, no dependencies:
//   node --test tests/camera-start-pending.test.mjs
//
// Web Start button ownership during the permission wait. The Start
// handler used to disable the button directly while the permission
// prompt was up, but refreshButtons() recomputed the button from the
// camera state alone — and any other path that refreshed the buttons
// mid-wait undid that disable. Changing the facing selector while the
// prompt was up re-enabled Start, and a second tap fired a second
// permission request, which the handler's own comment promised could
// not happen. The same one-owner hole sat in the init path: a browser
// with no camera API got Start disabled directly, and the init
// refreshButtons() right after it re-enabled it, offering a Start tap
// that could only fail. One helper now owns the button: disabled when
// the camera is live, while a start is pending, or when no camera API
// exists at all. app.js cannot run in node (it needs a DOM), so these
// are static checks on the shipped wiring, in the same style as the
// other Agent 1 tests. Native needs no change: its Start button is
// disabled from the camera state itself, which already includes the
// requesting-permission state, so no other UI action can re-enable it
// mid-wait.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const view = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
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
const initSection = app.slice(app.indexOf("// Initial state."));

test("web: refreshButtons owns Start disabled from live, pending, and unsupported", () => {
  assert.match(
    refreshButtons,
    /els\.btnCameraStart\.disabled = camActive \|\| cameraStartPending \|\| cameraUnsupported;/,
  );
});

test("web: no direct Start disable outside refreshButtons", () => {
  const withoutRefresh = app.replace(refreshButtons, "");
  assert.doesNotMatch(withoutRefresh, /btnCameraStart\.disabled\s*=/);
});

test("web: Start handler sets the pending flag and refreshes before awaiting", () => {
  const flagAt = startHandler.indexOf("cameraStartPending = true;");
  const refreshAt = startHandler.indexOf("refreshButtons();");
  const awaitAt = startHandler.indexOf("await camera.start();");
  assert.notEqual(flagAt, -1, "Start handler is missing its pending-flag set");
  assert.ok(flagAt < refreshAt, "the flag must set before the button refreshes");
  assert.ok(refreshAt < awaitAt, "the button must refresh before the permission await");
});

test("web: Start settle paths clear the pending flag exactly once, after the try/catch", () => {
  // Both non-stale settle paths (success and failure) fall through to
  // the same trailing lines; the stale early-returns skip them, since
  // Stop/Reset already cleared the flag.
  const clears = [...startHandler.matchAll(/cameraStartPending = false;/g)];
  assert.equal(clears.length, 1, "the flag must clear in exactly one settle place");
  const describeAt = startHandler.indexOf("setCameraState(describeCameraError(err));");
  assert.ok(
    clears[0].index > describeAt,
    "the clear must sit after the catch, not on a stale path",
  );
  assert.match(
    startHandler.slice(clears[0].index),
    /^cameraStartPending = false;\s*refreshButtons\(\);/,
  );
});

test("web: Stop and Reset clear the pending flag before refreshing", () => {
  for (const [name, handler] of [["Stop", stopHandler], ["Reset", resetHandler]]) {
    const flagAt = handler.indexOf("cameraStartPending = false;");
    const refreshAt = handler.indexOf("refreshButtons();");
    assert.notEqual(flagAt, -1, `${name} handler is missing its pending-flag clear`);
    assert.ok(flagAt < refreshAt, `${name} must clear the flag before refreshing`);
  }
});

test("web: init leaves Start to refreshButtons on a camera-less browser", () => {
  assert.match(initSection, /if \(cameraUnsupported\) \{/);
  assert.doesNotMatch(initSection, /btnCameraStart\.disabled\s*=/);
  assert.match(app, /const cameraUnsupported = !cameraSupported\(\);/);
});

test("native: Start stays disabled while permission is requested, from state alone", () => {
  assert.match(
    view,
    /\.disabled\(camera\.state == \.running \|\| camera\.state == \.requestingPermission\)/,
  );
});
