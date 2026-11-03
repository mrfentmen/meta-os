// CB2-425 — window manager rules, tested against face/logic.mjs.
//
// face.js imports these functions for focus and close, so the z-order a test
// pins is the z-order the desktop draws. There is no fixture model here: the
// window-state module is real, and the file header says so.
import test from "node:test";
import assert from "node:assert/strict";
import {
  closeWindow,
  focusWindow,
  focusedWindow,
  initialWindowState,
  openOrFocus,
  openWindow,
} from "../face/logic.mjs";

test("CB2-425 open, focus order and close", () => {
  let state = initialWindowState();
  assert.deepEqual(state, { order: [], z: 20 });
  assert.equal(focusedWindow(state), null);

  // Opening raises the window: each open takes the next z.
  let r = openWindow(state, "terminal");
  state = r.state;
  assert.equal(r.opened, true);
  assert.deepEqual(state.order, ["terminal"]);
  assert.equal(focusedWindow(state), "terminal");

  state = openWindow(state, "dashboard").state;
  state = openWindow(state, "files").state;
  assert.deepEqual(state.order, ["terminal", "dashboard", "files"]);
  assert.equal(focusedWindow(state), "files", "the newest window is focused");

  // Focusing reorders without duplicating: the focused window goes last.
  state = focusWindow(state, "terminal");
  assert.deepEqual(state.order, ["dashboard", "files", "terminal"]);
  assert.equal(state.z, 24, "each focus takes a new z");
  assert.equal(focusedWindow(state), "terminal");

  // Opening an open window focuses it and opens nothing new.
  const again = openWindow(state, "files");
  assert.equal(again.opened, false);
  assert.equal(again.focused, "files");
  state = openOrFocus(state, "files");
  assert.deepEqual(state.order, ["dashboard", "terminal", "files"], "no duplicate entry");
  assert.equal(state.order.filter((id) => id === "files").length, 1);

  // Closing removes it; the remaining order is untouched and z does not jump.
  const before = state.z;
  state = closeWindow(state, "terminal");
  assert.deepEqual(state.order, ["dashboard", "files"]);
  assert.equal(state.z, before);
  assert.equal(focusedWindow(state), "files");

  // Closing the last window leaves nothing focused.
  state = closeWindow(closeWindow(state, "dashboard"), "files");
  assert.deepEqual(state.order, []);
  assert.equal(focusedWindow(state), null);

  // Focusing a window that is not open is a caller bug, said so by name.
  assert.throws(() => focusWindow(state, "terminal"), /window: not open: terminal/);

  // Re-opening after a close starts a fresh entry at the end.
  state = openWindow(state, "terminal").state;
  assert.deepEqual(state.order, ["terminal"]);
  assert.equal(state.z, before + 1);
});
