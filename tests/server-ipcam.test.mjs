// Node built-in test runner, no dependencies:  node --test tests/server-ipcam.test.mjs
// Covers the RTSP snapshot proxy (server/ipcam.mjs) and its two routes in
// server/server.mjs: config validation, ${ENV} credential expansion, ffmpeg
// argument shape, JPEG framing, timeouts, error redaction, the per-camera TTL
// cache, and the merged /api/cameras list. No network, no real ffmpeg, no
// camera: every child process is a stub.

import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import {
  clearCache,
  ffmpegArgs,
  grabFrame,
  ipCamList,
  isRtsp,
  loadIpCams,
  redact,
  snapshot,
} from "../server/ipcam.mjs";
import { createAssessServer } from "../server/server.mjs";

const JPEG = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46]);

async function configFile(doc) {
  const dir = await mkdtemp(path.join(tmpdir(), "ipcam-"));
  const file = path.join(dir, "cams.json");
  await writeFile(file, JSON.stringify(doc));
  return file;
}

function stubSpawn({ code = 0, stderr = "", bytes = JPEG, hang = false } = {}) {
  const calls = [];
  const fn = (bin, args) => {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.killed = false;
    child.kill = () => {
      child.killed = true;
      child.emit("close", null);
    };
    calls.push({ bin, args, child });
    if (!hang) {
      setImmediate(() => {
        child.stdout.emit("data", bytes);
        if (stderr) child.stderr.emit("data", Buffer.from(stderr));
        child.emit("close", code);
      });
    }
    return child;
  };
  fn.calls = calls;
  return fn;
}

test("loadIpCams treats a missing file as no cameras, not an error", async () => {
  const out = await loadIpCams("/nonexistent/cams.json", {});
  assert.deepEqual(out.cameras, []);
  assert.equal(out.error, null);
  assert.equal(out.missing, true);
});

test("loadIpCams expands credentials from the environment and defaults labels", async () => {
  const file = await configFile({
    cameras: [
      { id: "lobby", input: "rtsp://admin:${CAM_PASSWORD}@10.0.0.5/s1", latitude: 40.7 },
      { id: "dock", name: "  Dock  ", area: "Brooklyn", input: "rtsp://10.0.0.6/s2", enabled: false },
    ],
  });
  const out = await loadIpCams(file, { CAM_PASSWORD: "hunter2" });
  assert.equal(out.error, null);
  assert.equal(out.cameras.length, 2);
  assert.equal(out.cameras[0].input, "rtsp://admin:hunter2@10.0.0.5/s1");
  assert.equal(out.cameras[0].name, "lobby");
  assert.equal(out.cameras[0].area, "IP camera");
  assert.equal(out.cameras[0].latitude, 40.7);
  assert.equal(out.cameras[0].longitude, null);
  assert.equal(out.cameras[1].name, "Dock");
  assert.equal(out.cameras[1].area, "Brooklyn");
  assert.equal(out.cameras[1].enabled, false);
});

test("loadIpCams keeps an unexpanded placeholder instead of blank credentials", async () => {
  const file = await configFile([{ id: "cam", input: "rtsp://u:${CAM_PASSWORD}@h/s" }]);
  const out = await loadIpCams(file, {});
  assert.equal(out.cameras[0].input, "rtsp://u:${CAM_PASSWORD}@h/s");
});

test("loadIpCams rejects bad ids, duplicates and missing input, naming each", async () => {
  const file = await configFile([
    { id: "Lobby Cam", input: "rtsp://h/1" },
    { id: "a", input: "rtsp://h/2" },
    { id: "a", input: "rtsp://h/3" },
    { id: "b" },
    "not-an-object",
  ]);
  const out = await loadIpCams(file, {});
  assert.equal(out.cameras.length, 1);
  assert.match(out.error, /"Lobby Cam" must be lowercase/);
  assert.match(out.error, /duplicate id a/);
  assert.match(out.error, /b: input is required/);
  assert.match(out.error, /entry is not an object/);
});

test("loadIpCams reports malformed JSON as an error, not a crash", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "ipcam-"));
  const file = path.join(dir, "cams.json");
  await writeFile(file, "{ cameras: ");
  const out = await loadIpCams(file, {});
  assert.deepEqual(out.cameras, []);
  assert.match(out.error, /not valid JSON/);
});

test("ffmpegArgs asks for one frame over TCP for an RTSP input", () => {
  const args = ffmpegArgs({ input: "rtsp://h/s" });
  assert.deepEqual(args.slice(0, 4), ["-hide_banner", "-loglevel", "error", "-rtsp_transport"]);
  assert.ok(args.includes("tcp"));
  assert.equal(args[args.indexOf("-i") + 1], "rtsp://h/s");
  assert.equal(args[args.indexOf("-frames:v") + 1], "1");
  assert.equal(args.at(-1), "pipe:1");
});

test("ffmpegArgs leaves the RTSP transport flag off every other input", () => {
  // ffmpeg exits 8 ("Option rtsp_transport not found") when the flag reaches a
  // file or HTTP demuxer, so a URL that is not RTSP must not carry it.
  for (const input of ["/tmp/clip.mjpeg", "http://h/s.mjpg", "https://h/s.mjpg", "filesrc"]) {
    const args = ffmpegArgs({ input });
    assert.equal(args.includes("-rtsp_transport"), false, `no transport flag for ${input}`);
    assert.equal(args[args.indexOf("-i") + 1], input);
  }
  assert.equal(ffmpegArgs({ input: "rtsps://h/s" }).includes("-rtsp_transport"), true);
});

test("isRtsp matches only the RTSP schemes", () => {
  assert.equal(isRtsp("rtsp://h/s"), true);
  assert.equal(isRtsp("RTSPS://h/s"), true);
  assert.equal(isRtsp("http://h/s"), false);
  assert.equal(isRtsp("/tmp/x.mp4"), false);
});

test("grabFrame resolves the JPEG bytes and passes the input through", async () => {
  const spawn = stubSpawn();
  const bytes = await grabFrame({ input: "rtsp://h/s" }, { spawn, ffmpeg: "ffmpeg" });
  assert.equal(bytes.length, JPEG.length);
  assert.equal(bytes[0], 0xff);
  assert.equal(spawn.calls.length, 1);
  assert.equal(spawn.calls[0].bin, "ffmpeg");
});

test("grabFrame rejects a non-zero exit and redacts the URL credentials", async () => {
  const spawn = stubSpawn({ code: 1, stderr: "rtsp://admin:pw@10.0.0.5/s1: 401 Unauthorized" });
  await assert.rejects(
    grabFrame({ input: "rtsp://admin:pw@10.0.0.5/s1" }, { spawn }),
    (err) => {
      assert.match(err.message, /exited 1/);
      assert.match(err.message, /401 Unauthorized/);
      assert.doesNotMatch(err.message, /pw@/);
      return true;
    },
  );
});

test("grabFrame rejects output that is not a JPEG", async () => {
  const spawn = stubSpawn({ bytes: Buffer.from("not a jpeg") });
  await assert.rejects(grabFrame({ input: "rtsp://h/s" }, { spawn }), /no JPEG frame/);
});

test("grabFrame names a missing ffmpeg binary", async () => {
  const spawn = () => {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.kill = () => {};
    setImmediate(() => {
      const err = new Error("spawn ffmpeg ENOENT");
      err.code = "ENOENT";
      child.emit("error", err);
    });
    return child;
  };
  await assert.rejects(grabFrame({ input: "rtsp://h/s" }, { spawn }), /ffmpeg is not installed/);
});

test("grabFrame kills a hanging ffmpeg on timeout", async () => {
  const spawn = stubSpawn({ hang: true });
  await assert.rejects(
    grabFrame({ input: "rtsp://h/s" }, { spawn, timeoutMs: 20 }),
    /timed out after 20 ms/,
  );
  assert.equal(spawn.calls[0].child.killed, true);
});

test("snapshot refuses unknown and disabled cameras", async () => {
  const file = await configFile([
    { id: "off", input: "rtsp://h/1", enabled: false },
  ]);
  const deps = { configPath: file, env: {}, spawn: stubSpawn() };
  assert.equal((await snapshot("nope", deps)).status, 404);
  const disabled = await snapshot("off", deps);
  assert.equal(disabled.status, 409);
  assert.match(disabled.body.error, /disabled/);
});

test("snapshot serves one frame per camera per TTL", async () => {
  clearCache();
  const file = await configFile([{ id: "lobby", input: "rtsp://h/1" }]);
  const spawn = stubSpawn();
  const deps = { configPath: file, env: {}, spawn, ttlMs: 60_000 };

  const first = await snapshot("lobby", deps);
  assert.equal(first.status, 200);
  assert.equal(first.contentType, "image/jpeg");
  assert.equal(spawn.calls.length, 1);

  const second = await snapshot("lobby", deps);
  assert.equal(second.status, 200);
  assert.equal(spawn.calls.length, 1, "cached frame must not start a second ffmpeg");

  const chosen = await snapshot("lobby", { ...deps, ttlMs: 0 });
  assert.equal(chosen.status, 200);
  assert.equal(spawn.calls.length, 2, "a zero TTL must grab again");
  clearCache();
});

test("snapshot shares one ffmpeg run between concurrent callers", async () => {
  clearCache();
  const file = await configFile([{ id: "lobby", input: "rtsp://h/1" }]);
  const spawn = stubSpawn();
  const deps = { configPath: file, env: {}, spawn, ttlMs: 60_000 };
  const [a, b] = await Promise.all([snapshot("lobby", deps), snapshot("lobby", deps)]);
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.equal(spawn.calls.length, 1);
  clearCache();
});

test("snapshot reports an ffmpeg failure as 502 with the credentials redacted", async () => {
  clearCache();
  const file = await configFile([{ id: "lobby", input: "rtsp://u:pw@h/1" }]);
  const spawn = stubSpawn({ code: 1, stderr: "rtsp://u:pw@h/1 refused" });
  const out = await snapshot("lobby", { configPath: file, env: {}, spawn });
  assert.equal(out.status, 502);
  assert.match(out.body.error, /refused/);
  assert.doesNotMatch(out.body.error, /pw@/);
  clearCache();
});

test("ipCamList emits the shape the pages already normalize", async () => {
  const file = await configFile([
    { id: "lobby", name: "Lobby east", area: "Midtown", input: "rtsp://h/1", latitude: 40.75, longitude: -73.98 },
  ]);
  const out = await ipCamList({ configPath: file, env: {} });
  assert.equal(out.cameras.length, 1);
  const cam = out.cameras[0];
  assert.equal(cam.id, "ipcam-lobby");
  assert.equal(cam.name, "Lobby east");
  assert.equal(cam.area, "Midtown");
  assert.equal(cam.imageUrl, "/api/ipcam/lobby/snapshot");
  assert.equal(cam.isOnline, "true");
  assert.equal(cam.source, "ipcam");
});

test("redact strips URL userinfo and password query values only", () => {
  assert.equal(redact("rtsp://admin:pw@h/s failed"), "rtsp://***@h/s failed");
  assert.equal(redact("rtsp://h/s?password=abc&x=1"), "rtsp://h/s?password=***&x=1");
  assert.equal(redact("plain text"), "plain text");
  assert.equal(redact(undefined), "");
});

// ---- routes -------------------------------------------------------------

async function withServer(deps, fn) {
  const server = createAssessServer(deps);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    await fn(base);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("GET /api/ipcam lists cameras and names the config it read", async () => {
  clearCache();
  const file = await configFile([{ id: "lobby", input: "rtsp://h/1" }]);
  await withServer({ ipcam: { configPath: file, env: {} } }, async (base) => {
    const res = await fetch(`${base}/api/ipcam`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.cameras.length, 1);
    assert.equal(body.config, file);
    assert.equal(body.error, null);
    assert.ok(body.ffmpeg);
  });
});

test("GET /api/cameras appends positioned IP cameras to the upstream list", async () => {
  clearCache();
  const file = await configFile([
    { id: "lobby", input: "rtsp://h/1", latitude: 40.7, longitude: -73.9 },
    { id: "unplaced", input: "rtsp://h/2" },
  ]);
  const upstream = [{ id: "nyc-1", name: "1 Ave @ 84 St", latitude: 40.77, longitude: -73.95 }];
  await withServer(
    { cameraList: async () => upstream, ipcam: { configPath: file, env: {} } },
    async (base) => {
      const res = await fetch(`${base}/api/cameras`);
      assert.equal(res.status, 200);
      const body = await res.json();
      assert.equal(body.length, 2);
      assert.equal(body[0].id, "nyc-1");
      assert.equal(body[1].id, "ipcam-lobby");
      assert.equal(
        body.some((c) => c.id === "ipcam-unplaced"),
        false,
        "a camera with no position must stay off the map list",
      );
    },
  );
});

test("GET /api/cameras still answers 200 when NYCTMC is down but IP cams exist", async () => {
  clearCache();
  const file = await configFile([{ id: "lobby", input: "rtsp://h/1", latitude: 40.7, longitude: -73.9 }]);
  await withServer(
    {
      cameraList: async () => {
        throw new Error("NYCTMC camera API answered HTTP 503");
      },
      ipcam: { configPath: file, env: {} },
    },
    async (base) => {
      const res = await fetch(`${base}/api/cameras`);
      assert.equal(res.status, 200);
      const body = await res.json();
      assert.equal(body.length, 1);
      assert.equal(body[0].id, "ipcam-lobby");
    },
  );
});

test("GET /api/cameras keeps the 502 when both sources are empty", async () => {
  await withServer(
    {
      cameraList: async () => {
        throw new Error("NYCTMC camera API answered HTTP 503");
      },
      ipcam: { configPath: "/nonexistent/cams.json", env: {} },
    },
    async (base) => {
      const res = await fetch(`${base}/api/cameras`);
      assert.equal(res.status, 502);
      const body = await res.json();
      assert.match(body.error, /HTTP 503/);
    },
  );
});

test("GET /api/ipcam/:id/snapshot returns image/jpeg with no-store", async () => {
  clearCache();
  const file = await configFile([{ id: "lobby", input: "rtsp://h/1" }]);
  await withServer(
    { ipcam: { configPath: file, env: {}, spawn: stubSpawn() } },
    async (base) => {
      const res = await fetch(`${base}/api/ipcam/lobby/snapshot`);
      assert.equal(res.status, 200);
      assert.equal(res.headers.get("content-type"), "image/jpeg");
      assert.equal(res.headers.get("cache-control"), "no-store");
      const bytes = Buffer.from(await res.arrayBuffer());
      assert.deepEqual([...bytes.subarray(0, 4)], [0xff, 0xd8, 0xff, 0xe0]);
    },
  );
  clearCache();
});

test("GET /api/ipcam/:id/snapshot names an unknown camera and a bad id", async () => {
  clearCache();
  const file = await configFile([]);
  await withServer({ ipcam: { configPath: file, env: {} } }, async (base) => {
    const unknown = await fetch(`${base}/api/ipcam/ghost/snapshot`);
    assert.equal(unknown.status, 404);
    assert.match((await unknown.json()).error, /no IP camera named ghost/);

    const bad = await fetch(`${base}/api/ipcam/BAD%20ID/snapshot`);
    assert.equal(bad.status, 404);
  });
});

test("POST /api/ipcam is refused with a named method", async () => {
  await withServer({ ipcam: { configPath: "/nonexistent/cams.json", env: {} } }, async (base) => {
    const res = await fetch(`${base}/api/ipcam`, { method: "POST", body: "{}" });
    assert.equal(res.status, 405);
    assert.match((await res.json()).error, /use GET/);
  });
});
