// Node built-in test runner, no dependencies:  node --test tests/camera.test.mjs
// Covers the web camera's facing selection: front vs rear constraints,
// recording a choice while off, and restarting the stream while live.
// The browser UI (index.html select + app.js handler) is not exercised
// here — it only calls the Camera methods tested below.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  CAMERA_FACINGS,
  Camera,
  facingConstraints,
  isFacingMode,
} from "../js/camera.js";

function fakeStream() {
  const stopped = [];
  const track = {
    readyState: "live",
    stop() {
      stopped.push(true);
      this.readyState = "ended";
    },
  };
  return {
    track,
    stopped,
    getTracks: () => [track],
    getVideoTracks: () => [track],
  };
}

function installFakeCamera() {
  const calls = [];
  const streams = [];
  // Node's global navigator is a getter-only property, so define it
  // rather than assigning it.
  Object.defineProperty(globalThis, "navigator", {
    value: {
      mediaDevices: {
        getUserMedia: async (constraints) => {
          calls.push(constraints);
          const stream = fakeStream();
          streams.push(stream);
          return stream;
        },
      },
    },
    configurable: true,
    writable: true,
  });
  return { calls, streams };
}

function fakeVideoEl() {
  return { srcObject: null, play: async () => {} };
}

test("camera: exactly the front and rear facings", () => {
  assert.deepEqual(CAMERA_FACINGS, ["user", "environment"]);
  assert.equal(isFacingMode("user"), true);
  assert.equal(isFacingMode("environment"), true);
  assert.equal(isFacingMode("left"), false);
  assert.equal(isFacingMode(""), false);
});

test("camera: facing constraints are a preference, never an exact requirement", () => {
  assert.deepEqual(facingConstraints("user"), {
    video: { facingMode: "user" },
    audio: false,
  });
  assert.deepEqual(facingConstraints("environment"), {
    video: { facingMode: "environment" },
    audio: false,
  });
  assert.throws(() => facingConstraints("left"), /Unknown camera facing/);
});

test("camera: start defaults to the front camera", async () => {
  const { calls } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await camera.start();
  assert.equal(camera.facingMode, "user");
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0], facingConstraints("user"));
  assert.equal(camera.active, true);
});

test("camera: start accepts an explicit rear facing", async () => {
  const { calls } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await camera.start("environment");
  assert.equal(camera.facingMode, "environment");
  assert.deepEqual(calls[0], facingConstraints("environment"));
});

test("camera: start rejects an unknown facing without touching getUserMedia", async () => {
  const { calls } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await assert.rejects(() => camera.start("left"), /Unknown camera facing/);
  assert.equal(calls.length, 0);
  assert.equal(camera.active, false);
});

test("camera: switchFacing while off only records the choice", async () => {
  const { calls } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await camera.switchFacing("environment");
  assert.equal(camera.facingMode, "environment");
  assert.equal(calls.length, 0);
  await camera.start();
  assert.deepEqual(calls[0], facingConstraints("environment"));
});

test("camera: switchFacing while live stops the old stream and starts the new facing", async () => {
  const { calls, streams } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await camera.start("user");
  await camera.switchFacing("environment");
  assert.equal(camera.facingMode, "environment");
  assert.equal(streams[0].stopped.length, 1);
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[1], facingConstraints("environment"));
  assert.equal(camera.active, true);
});

test("camera: switchFacing rejects an unknown facing and leaves the stream alone", async () => {
  const { calls, streams } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await camera.start("user");
  await assert.rejects(() => camera.switchFacing("left"), /Unknown camera facing/);
  assert.equal(camera.facingMode, "user");
  assert.equal(streams[0].stopped.length, 0);
  assert.equal(calls.length, 1);
});
