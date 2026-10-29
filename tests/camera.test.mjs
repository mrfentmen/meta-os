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
  MAX_FRAME_DIMENSION,
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

function fakeCanvas() {
  const draws = [];
  const dataUrlCalls = [];
  return {
    draws,
    dataUrlCalls,
    width: 0,
    height: 0,
    getContext: () => ({
      drawImage: (...args) => {
        draws.push(args);
      },
    }),
    toDataURL: (...args) => {
      dataUrlCalls.push(args);
      return "data:image/jpeg;base64,fake";
    },
  };
}

async function liveCamera(videoWidth, videoHeight) {
  installFakeCamera();
  const videoEl = { ...fakeVideoEl(), videoWidth, videoHeight };
  const camera = new Camera(videoEl);
  await camera.start();
  return { camera, videoEl };
}

test("camera: captureFrame downscales an oversize frame to a 1280px longest side, matching the native camera", async () => {
  assert.equal(MAX_FRAME_DIMENSION, 1280);
  const { camera, videoEl } = await liveCamera(4000, 3000);
  const canvas = fakeCanvas();
  const url = camera.captureFrame(canvas);
  assert.equal(url, "data:image/jpeg;base64,fake");
  assert.equal(canvas.width, 1280);
  assert.equal(canvas.height, 960);
  assert.equal(canvas.draws.length, 1);
  assert.deepEqual(canvas.draws[0], [videoEl, 0, 0, 1280, 960]);
  assert.deepEqual(canvas.dataUrlCalls, [["image/jpeg", 0.8]]);
});

test("camera: captureFrame leaves a frame already under the cap at its own size", async () => {
  const { camera, videoEl } = await liveCamera(640, 480);
  const canvas = fakeCanvas();
  camera.captureFrame(canvas);
  assert.equal(canvas.width, 640);
  assert.equal(canvas.height, 480);
  assert.deepEqual(canvas.draws[0], [videoEl, 0, 0, 640, 480]);
});

test("camera: captureFrame throws when the camera is off or the frame has no dimensions yet", async () => {
  installFakeCamera();
  const off = new Camera(fakeVideoEl());
  assert.throws(() => off.captureFrame(fakeCanvas()), /Camera is not active/);
  const { camera } = await liveCamera(0, 0);
  assert.throws(() => camera.captureFrame(fakeCanvas()), /not ready yet/);
});

// A start still awaiting permission when Stop lands: the permission
// prompt is a real await in Camera.start, and Reset/Stop used to be a
// no-op against it (no stream existed yet to stop), so the settling
// start attached its stream and left the camera live after a stop that
// said it was stopped. The start now carries a generation that stop()
// bumps, and a stale settle discards its stream instead of attaching
// it. These tests drive that window with a deferred getUserMedia.
function installDeferredCamera() {
  const streams = [];
  // One resolver per pending getUserMedia call, in call order: a
  // second start overwrites a single "next" slot, so resolving must
  // drain the queue oldest-first or the first start never settles.
  const pending = [];
  Object.defineProperty(globalThis, "navigator", {
    value: {
      mediaDevices: {
        getUserMedia: () =>
          new Promise((resolve) => {
            pending.push(() => {
              const stream = fakeStream();
              streams.push(stream);
              resolve(stream);
            });
          }),
      },
    },
    configurable: true,
    writable: true,
  });
  return {
    streams,
    resolveNext: () => {
      const fn = pending.shift();
      fn();
    },
  };
}

test("camera: a start outstanding across Stop never attaches its stream when it settles", async () => {
  const deferred = installDeferredCamera();
  const videoEl = fakeVideoEl();
  const camera = new Camera(videoEl);
  const started = camera.start();
  camera.stop();
  deferred.resolveNext();
  await started;
  assert.equal(camera.active, false);
  assert.equal(videoEl.srcObject, null);
  assert.equal(deferred.streams.length, 1);
  assert.equal(deferred.streams[0].stopped.length, 1);
});

test("camera: of two overlapping starts, only the newer one's stream attaches", async () => {
  const deferred = installDeferredCamera();
  const videoEl = fakeVideoEl();
  const camera = new Camera(videoEl);
  const first = camera.start();
  const second = camera.start();
  deferred.resolveNext();
  await first;
  assert.equal(camera.active, false);
  assert.equal(deferred.streams[0].stopped.length, 1);
  deferred.resolveNext();
  await second;
  assert.equal(camera.active, true);
  assert.equal(videoEl.srcObject, deferred.streams[1]);
  assert.equal(deferred.streams[1].stopped.length, 0);
});
