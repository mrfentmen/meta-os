// Node built-in test runner, no dependencies:  node --test tests/ui-wave-restore.test.mjs
// Covers HN-023 (session restore from records): a reload
// restores the incident view from the freshly loaded camera list
// and crew incidents, never from stale saved memory. The saved
// record is only a pointer; the crew record wins, an unknown
// camera restores nothing, and torn storage restores nothing.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { saveSelection, loadSelection, resolveSelection, RESTORE_KEY } from "../js/restore.js";

const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");

function memStorage(seed = null) {
  const store = seed !== null ? { [RESTORE_KEY]: seed } : {};
  return {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = v; },
  };
}

test("save/load round-trips a selection pointer", () => {
  const storage = memStorage();
  assert.equal(saveSelection(storage, { cameraId: "cam-a", category: "person down", priority: "high", at: 123 }), true);
  assert.deepEqual(loadSelection(storage), { cameraId: "cam-a", category: "person down", priority: "high", at: 123 });
});

test("torn or wrong-shaped storage restores nothing", () => {
  assert.equal(loadSelection(memStorage("{torn")), null);
  assert.equal(loadSelection(memStorage(JSON.stringify({ cameraId: "" }))), null);
  assert.equal(loadSelection(memStorage(JSON.stringify({ category: "x" }))), null);
  assert.equal(loadSelection(memStorage(JSON.stringify({ cameraId: "cam-a", priority: 5 }))), null);
  assert.equal(loadSelection(memStorage()), null);
  assert.equal(saveSelection(memStorage(), { cameraId: "" }), false);
});

test("resolve prefers the newest crew record for the camera", () => {
  const incidents = [
    { id: "i-new", camera_id: "cam-a", status: "dispatched-simulated", category: "person down", priority: "high" },
    { id: "i-old", camera_id: "cam-a", status: "cleared-by-review", category: "energetic movement", priority: "low" },
    { id: "i-other", camera_id: "cam-b", status: "dispatched-simulated", category: "fire", priority: "high" },
  ];
  const resolved = resolveSelection({ cameraId: "cam-a" }, ["cam-a", "cam-b"], incidents);
  assert.equal(resolved.cameraId, "cam-a");
  assert.equal(resolved.incident.id, "i-new");
});

test("resolve falls back to the camera alone, never a guessed camera", () => {
  const bare = resolveSelection({ cameraId: "cam-b" }, ["cam-a", "cam-b"], []);
  assert.equal(bare.cameraId, "cam-b");
  assert.equal(bare.incident, null);
  assert.equal(resolveSelection({ cameraId: "cam-gone" }, ["cam-a", "cam-b"], []), null);
  assert.equal(resolveSelection(null, ["cam-a"], []), null);
});

test("wiring: select saves, loop feed restores once per load", () => {
  assert.ok(mapJs.includes('import { saveSelection, loadSelection, resolveSelection } from "./restore.js";'));
  assert.ok(mapJs.includes("saveSelection(localStorage, {"));
  assert.ok(mapJs.includes("function maybeRestore(payload) {"));
  assert.ok(mapJs.includes("maybeRestore(payload);"));
  assert.ok(mapJs.includes("restored: false,"));
  assert.ok(mapJs.includes("if (state.focusedId) {\n    state.restored = true;"));
});
