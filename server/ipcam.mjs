// IP cameras: RTSP in, JPEG out, through ffmpeg.
//
// The NYCTMC cameras publish a JPEG URL each, so the pages can load them
// directly. An IP camera speaks RTSP or ONVIF, which no browser plays, so the
// server takes one frame with ffmpeg and hands the browser a JPEG. That keeps
// every page on the same contract: a camera is a name, a position and an image
// URL.
//
// Config: server/cams.json (override with METAOS_IPCAMS). Shape:
//
//   {
//     "cameras": [
//       {
//         "id": "lobby",                       // stable, used in the URL
//         "name": "Lobby east",                // what the board shows
//         "area": "Midtown",                   // borough or site name
//         "input": "rtsp://user:pass@10.0.0.5/stream1",
//         "latitude": 40.7580,                 // optional; without it the
//         "longitude": -73.9855,               // camera stays off the map
//         "enabled": true
//       }
//     ]
//   }
//
// Credentials: put ${CAM_PASSWORD} in the input and set CAM_PASSWORD in the
// service environment. The value is substituted at load time and never
// logged; error text is redacted before it leaves this module.

import { readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

export const DEFAULT_CONFIG = path.join(HERE, "cams.json");
export const FFMPEG = process.env.FFMPEG || "ffmpeg";
export const SNAPSHOT_TTL_MS = Number(process.env.IPCAM_SNAPSHOT_TTL_MS || 5000);
const GRAB_TIMEOUT_MS = Number(process.env.IPCAM_GRAB_TIMEOUT_MS || 8000);
const MAX_BYTES = 4 * 1024 * 1024;
const MAX_CONCURRENT = Math.max(1, Number(process.env.IPCAM_MAX_CONCURRENT || 2));

const cache = new Map(); // id -> { at, bytes, contentType }
const inflight = new Map(); // id -> Promise
let active = 0;
const waiting = [];

function withSlot(fn) {
  return new Promise((resolve, reject) => {
    const run = () => {
      active += 1;
      Promise.resolve()
        .then(fn)
        .then(resolve, reject)
        .finally(() => {
          active -= 1;
          const next = waiting.shift();
          if (next) next();
        });
    };
    if (active < MAX_CONCURRENT) run();
    else waiting.push(run);
  });
}

export function redact(text) {
  if (typeof text !== "string") return "";
  return text
    .replace(/(\b[a-z][a-z0-9+.-]*:\/\/)[^/\s@]+@/gi, "$1***@")
    .replace(/(password|passwd|pass|pwd)=([^&\s]+)/gi, "$1=***");
}

function expand(value, env) {
  return String(value).replace(/\$\{([A-Z0-9_]+)\}/g, (whole, name) => {
    const v = env[name];
    return typeof v === "string" && v.length > 0 ? v : whole;
  });
}

function slugOk(id) {
  return typeof id === "string" && /^[a-z0-9][a-z0-9_-]{0,40}$/.test(id);
}

function num(v) {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export async function loadIpCams(file = process.env.METAOS_IPCAMS || DEFAULT_CONFIG, env = process.env) {
  let raw;
  try {
    raw = await readFile(file, "utf8");
  } catch (err) {
    if (err && err.code === "ENOENT") return { cameras: [], error: null, path: file, missing: true };
    return { cameras: [], error: `cams.json unreadable: ${redact(err.message)}`, path: file };
  }
  let doc;
  try {
    doc = JSON.parse(raw);
  } catch {
    return { cameras: [], error: "cams.json is not valid JSON", path: file };
  }
  const list = Array.isArray(doc) ? doc : Array.isArray(doc.cameras) ? doc.cameras : null;
  if (!list) return { cameras: [], error: 'cams.json must be an array or {"cameras": [...]}', path: file };

  const cameras = [];
  const problems = [];
  const seen = new Set();
  for (const entry of list) {
    if (!entry || typeof entry !== "object") {
      problems.push("entry is not an object");
      continue;
    }
    if (!slugOk(entry.id)) {
      problems.push(`id ${JSON.stringify(entry.id)} must be lowercase letters, digits, - or _`);
      continue;
    }
    if (seen.has(entry.id)) {
      problems.push(`duplicate id ${entry.id}`);
      continue;
    }
    if (typeof entry.input !== "string" || !entry.input.trim()) {
      problems.push(`${entry.id}: input is required`);
      continue;
    }
    seen.add(entry.id);
    cameras.push({
      id: entry.id,
      name: typeof entry.name === "string" && entry.name.trim() ? entry.name.trim() : entry.id,
      area: typeof entry.area === "string" && entry.area.trim() ? entry.area.trim() : "IP camera",
      input: expand(entry.input.trim(), env),
      latitude: num(entry.latitude),
      longitude: num(entry.longitude),
      enabled: entry.enabled !== false,
    });
  }
  return { cameras, error: problems.length ? problems.join("; ") : null, path: file };
}

export function isRtsp(input) {
  return /^rtsps?:/i.test(String(input));
}

export function ffmpegArgs(cam) {
  // Transport flags belong to the RTSP demuxer alone. ffmpeg 9 exits with
  // "Option rtsp_transport not found" for a file or HTTP input, so they are
  // added only when the URL is actually RTSP. TCP keeps a lossy Wi-Fi link
  // from tearing the frame.
  const transport = isRtsp(cam.input) ? ["-rtsp_transport", "tcp"] : [];
  return [
    "-hide_banner",
    "-loglevel", "error",
    ...transport,
    "-i", cam.input,
    "-frames:v", "1",
    "-f", "image2pipe",
    "-vcodec", "mjpeg",
    "-q:v", "4",
    "pipe:1",
  ];
}

export function grabFrame(cam, deps = {}) {
  const bin = deps.ffmpeg || FFMPEG;
  const timeoutMs = deps.timeoutMs || GRAB_TIMEOUT_MS;
  const spawnFn = deps.spawn || spawn;
  return new Promise((resolve, reject) => {
    let settled = false;
    let out = [];
    let size = 0;
    let errText = "";
    let child;
    try {
      child = spawnFn(bin, ffmpegArgs(cam), { stdio: ["ignore", "pipe", "pipe"] });
    } catch (err) {
      reject(new Error(`ffmpeg could not start: ${redact(err.message)}`));
      return;
    }
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { child.kill("SIGKILL"); } catch {}
      reject(new Error(`ffmpeg timed out after ${timeoutMs} ms`));
    }, timeoutMs);

    child.on("error", (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      const msg = err && err.code === "ENOENT"
        ? `ffmpeg is not installed (looked for ${bin})`
        : `ffmpeg failed: ${redact(err.message)}`;
      reject(new Error(msg));
    });
    child.stdout.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BYTES) {
        try { child.kill("SIGKILL"); } catch {}
        return;
      }
      out.push(chunk);
    });
    child.stderr.on("data", (chunk) => {
      if (errText.length < 2000) errText += chunk.toString("utf8");
    });
    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      const bytes = Buffer.concat(out);
      if (code !== 0) {
        reject(new Error(`ffmpeg exited ${code}: ${redact(errText.trim().slice(-300))}`));
        return;
      }
      if (bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) {
        reject(new Error("ffmpeg produced no JPEG frame"));
        return;
      }
      resolve(bytes);
    });
  });
}

// One frame per camera per TTL. Concurrent callers share one ffmpeg run, so a
// page that reloads twice does not start two decoders on the same stream.
export async function snapshot(id, deps = {}) {
  const loaded = await loadIpCams(deps.configPath, deps.env);
  const cam = loaded.cameras.find((c) => c.id === id);
  if (!cam) return { status: 404, body: { error: `no IP camera named ${id}` } };
  if (!cam.enabled) return { status: 409, body: { error: `IP camera ${id} is disabled in cams.json` } };

  const ttl = deps.ttlMs ?? SNAPSHOT_TTL_MS;
  const hit = cache.get(id);
  if (hit && Date.now() - hit.at < ttl) {
    return { status: 200, bytes: hit.bytes, contentType: "image/jpeg", ageMs: Date.now() - hit.at };
  }
  if (inflight.has(id)) {
    try {
      const bytes = await inflight.get(id);
      return { status: 200, bytes, contentType: "image/jpeg", ageMs: 0 };
    } catch (err) {
      return { status: 502, body: { error: redact(err.message) } };
    }
  }
  const run = withSlot(() => grabFrame(cam, deps));
  inflight.set(id, run);
  try {
    const bytes = await run;
    cache.set(id, { at: Date.now(), bytes, contentType: "image/jpeg" });
    return { status: 200, bytes, contentType: "image/jpeg", ageMs: 0 };
  } catch (err) {
    return { status: 502, body: { error: redact(err.message) } };
  } finally {
    inflight.delete(id);
  }
}

// The shape the pages already understand (js/camera-*.js normalizes it), so an
// IP camera appears in the camera list and on the map beside the NYCTMC ones.
export async function ipCamList(deps = {}) {
  const loaded = await loadIpCams(deps.configPath, deps.env);
  const cams = loaded.cameras.map((cam) => ({
    id: `ipcam-${cam.id}`,
    name: cam.name,
    area: cam.area,
    latitude: cam.latitude,
    longitude: cam.longitude,
    isOnline: "true",
    imageUrl: `/api/ipcam/${cam.id}/snapshot`,
    source: "ipcam",
    enabled: cam.enabled,
  }));
  return { cameras: cams, error: loaded.error, path: loaded.path, missing: loaded.missing === true };
}

export function clearCache() {
  cache.clear();
}
