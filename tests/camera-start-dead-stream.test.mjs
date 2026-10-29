// Node built-in test runner, no dependencies:  node --test tests/camera-start-dead-stream.test.mjs
// Covers the web camera's start after a stream ended outside the app:
// a device unplugged, or the browser revoking the camera, ends the
// tracks without the app stopping anything, so the Camera still holds
// a non-null stream object whose tracks are all dead. The old start()
// returned early on any non-null stream, so a Start after such an
// outside end reported success while the camera stayed dead — and the
// app handler went on to show "Camera is live" for a black preview.
// The native camera checks its session is actually running after
// starting and reports failure instead of claiming live; the web
// start must likewise not treat a dead stream object as a live camera.
// The app handler's own post-start active check (index.html Start
// handler) is browser-DOM code and is verified by inspection, like the
// Swift changes; what is unit-tested here is the Camera half: a dead
// stream is discarded and a fresh stream is requested.

import { test } from "node:test";
import assert from "node:assert/strict";

import { Camera, facingConstraints } from "../js/camera.js";

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

test("camera: start after a stream ended outside the app discards it and requests a fresh stream", async () => {
  const { calls, streams } = installFakeCamera();
  const videoEl = fakeVideoEl();
  const camera = new Camera(videoEl);
  await camera.start();
  assert.equal(camera.active, true);
  assert.equal(videoEl.srcObject, streams[0]);

  // The outside end: the track dies without the app stopping anything,
  // so stop() is never called on the dead track by the app — only its
  // readyState flips, exactly as a revoked or unplugged device does.
  streams[0].track.readyState = "ended";
  assert.equal(camera.active, false);

  await camera.start();
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[1], facingConstraints("user"));
  // Discarding stops the dead track (harmless on an ended track) and
  // the fresh stream is the one attached and live.
  assert.equal(streams[0].stopped.length, 1);
  assert.equal(videoEl.srcObject, streams[1]);
  assert.equal(camera.active, true);
});

test("camera: start while live still returns without a second request", async () => {
  const { calls } = installFakeCamera();
  const camera = new Camera(fakeVideoEl());
  await camera.start();
  await camera.start();
  assert.equal(calls.length, 1);
  assert.equal(camera.active, true);
});
