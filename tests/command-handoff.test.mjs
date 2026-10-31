// Node built-in test runner, no dependencies:  node --test tests/command-handoff.test.mjs
// Covers the nearest-camera handoff decision (js/command-flag.js):
// nearest-other-camera excludes the flagged camera itself, honors
// radius and limit, skips offline cameras by default, and returns
// [] for bad input; resolveHandoff only acts on the rising edge,
// auto-shows when the operator is idle, suggests when busy, and
// reports a stable reason otherwise.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  HANDOFF_IDLE_MS,
  HANDOFF_RADIUS_METERS,
  nearestOtherCamera,
  resolveHandoff,
} from "../js/command-flag.js";

const midtown = { id: "a", name: "A", latitude: 40.75, longitude: -73.99, isOnline: "true" };
// ~111 m north of midtown (0.001 deg latitude).
const north = { id: "b", name: "B", latitude: 40.751, longitude: -73.99, isOnline: "true" };
// ~890 m north — outside the default 600 m radius.
const far = { id: "c", name: "C", latitude: 40.758, longitude: -73.99, isOnline: "true" };
const offline = { id: "d", name: "D", latitude: 40.7505, longitude: -73.99, isOnline: "false" };

test("nearestOtherCamera excludes the flagged camera itself", () => {
  const got = nearestOtherCamera([midtown, north], "a");
  assert.equal(got.length, 1);
  assert.equal(got[0].camera.id, "b");
  assert.ok(got[0].distance > 100 && got[0].distance < 120);
});

test("nearestOtherCamera enforces radius and sorts nearest first", () => {
  const got = nearestOtherCamera([midtown, far, north], "a", { radiusMeters: 600, limit: 5 });
  assert.deepEqual(
    got.map((entry) => entry.camera.id),
    ["b"],
  );
});

test("nearestOtherCamera skips offline cameras by default", () => {
  const got = nearestOtherCamera([midtown, offline], "a");
  assert.deepEqual(got, []);
});

test("nearestOtherCamera can include offline cameras when asked", () => {
  const got = nearestOtherCamera([midtown, offline], "a", { onlineOnly: false });
  assert.equal(got.length, 1);
  assert.equal(got[0].camera.id, "d");
});

test("nearestOtherCamera respects limit", () => {
  const got = nearestOtherCamera([midtown, north, far], "a", { radiusMeters: 2000, limit: 1 });
  assert.equal(got.length, 1);
  assert.equal(got[0].camera.id, "b");
});

test("nearestOtherCamera returns [] for bad input", () => {
  assert.deepEqual(nearestOtherCamera(null, "a"), []);
  assert.deepEqual(nearestOtherCamera([midtown], null), []);
  assert.deepEqual(nearestOtherCamera([midtown], "missing"), []);
  assert.deepEqual(nearestOtherCamera([{ id: "x", name: "X" }], "x"), []);
  assert.deepEqual(nearestOtherCamera([midtown], "a", { radiusMeters: 0 }), []);
});

test("resolveHandoff auto-shows when idle on the rising edge", () => {
  const out = resolveHandoff({
    cameras: [midtown, north],
    flaggedCameraId: "a",
    risingEdge: true,
    userInteracting: false,
  });
  assert.equal(out.action, "show");
  assert.equal(out.camera.id, "b");
  assert.ok(out.distanceMeters > 100 && out.distanceMeters < 120);
});

test("resolveHandoff suggests instead of moving while the operator is busy", () => {
  const out = resolveHandoff({
    cameras: [midtown, north],
    flaggedCameraId: "a",
    risingEdge: true,
    userInteracting: true,
  });
  assert.equal(out.action, "suggest");
  assert.equal(out.camera.id, "b");
});

test("resolveHandoff reports a stable reason when it does nothing", () => {
  assert.deepEqual(
    resolveHandoff({ cameras: [midtown, north], flaggedCameraId: "a", risingEdge: false, userInteracting: false }),
    { action: "none", reason: "not-rising-edge" },
  );
  assert.deepEqual(
    resolveHandoff({ cameras: [midtown], flaggedCameraId: "a", risingEdge: true, userInteracting: false }),
    { action: "none", reason: "no-candidate" },
  );
  assert.deepEqual(resolveHandoff(), { action: "none", reason: "not-rising-edge" });
});

test("handoff constants are sane", () => {
  assert.equal(HANDOFF_RADIUS_METERS, 600);
  assert.ok(HANDOFF_IDLE_MS >= 1000);
});
