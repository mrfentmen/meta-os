#!/usr/bin/env node
// Capture the Meta ASCII studio's rotating ribbon as a numbered frame set.
//
// Why: the OS wallpaper is the studio's loop, and the loop that shipped was 16
// frames at 16 fps — one revolution per second, with 22.5 degrees between
// frames, which reads as a stutter rather than a spin. The studio is the only
// renderer of this art, so the wallpaper has to come from it. Screen-recording
// the page samples whatever the compositor happens to show; this asks the page
// for frame N of M at an exact angle instead (window.MetaAsciiStudio.renderAt).
//
// Usage (Chrome must already be serving CDP with the studio open):
//   node loop_from_studio.mjs --port 9333 --frames 60 --out /tmp/studio-frames
// Then composite with loop_frames_to_wallpaper.py — this script only emits the
// studio's own pixels at its own canvas size.
import fs from "node:fs";
import path from "node:path";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf("--" + name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};
const PORT = Number(arg("port", "9333"));
const FRAMES = Number(arg("frames", "60"));
const OUT = arg("out", "/tmp/studio-frames");
const READY_MS = Number(arg("ready", "20000"));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function targetUrl() {
  const deadline = Date.now() + READY_MS;
  let last = "";
  while (Date.now() < deadline) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page" && /meta-ascii-logo-studio/.test(t.url));
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
      last = list.map((t) => t.url).join(", ");
    } catch (e) {
      last = String(e.message || e);
    }
    await sleep(400);
  }
  throw new Error(`no studio page on CDP :${PORT} (saw: ${last})`);
}

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      const p = this.pending.get(msg.id);
      if (!p) return;
      this.pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message));
      else p.resolve(msg.result);
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  async eval(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.exception?.description || "evaluate threw");
    }
    return res.result.value;
  }
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const url = await targetUrl();
  const ws = new WebSocket(url);
  await new Promise((res, rej) => {
    ws.addEventListener("open", res, { once: true });
    ws.addEventListener("error", () => rej(new Error("CDP socket failed")), { once: true });
  });
  const cdp = new Cdp(ws);
  await cdp.send("Runtime.enable");

  // Wait for the studio to have a canvas with a size — the hook only exists
  // after the page's own init ran.
  const deadline = Date.now() + READY_MS;
  let box = null;
  while (Date.now() < deadline) {
    box = await cdp.eval(`(() => {
      const s = window.MetaAsciiStudio;
      const c = document.getElementById('ascii-canvas');
      if (!s || !c || !c.width || !c.height) return null;
      return { w: c.width, h: c.height, hook: true };
    })()`);
    if (box) break;
    await sleep(300);
  }
  if (!box) throw new Error("studio never exposed MetaAsciiStudio with a sized canvas");

  // Canvas geometry: the studio's canvas is a responsive element (aspect 1.76,
  // capped at 58svh), so its captured size depends on the window it happened to
  // open in. A wallpaper needs a known size, and a recapture must not silently
  // change the framing. --canvas WxH pins the CSS box; the page's own
  // ResizeObserver then resizes the backing store, so renderAt draws at the
  // size we asked for.
  const CANVAS = arg("canvas", "1088x618");
  const [cw, ch] = CANVAS.split("x").map(Number);
  if (cw > 0 && ch > 0) {
    await cdp.eval(`(() => {
      const c = document.getElementById('ascii-canvas');
      c.style.aspectRatio = 'auto';
      c.style.maxHeight = 'none';
      c.style.width = '${cw}px';
      c.style.height = '${ch}px';
      return c.getBoundingClientRect().width + 'x' + c.getBoundingClientRect().height;
    })()`);
    await sleep(700);
    box = await cdp.eval(`(() => {
      const c = document.getElementById('ascii-canvas');
      return { w: c.width, h: c.height };
    })()`);
  }

  const written = [];
  for (let i = 0; i < FRAMES; i += 1) {
    const angle = (i / FRAMES) * Math.PI * 2;
    const dataUrl = await cdp.eval(`window.MetaAsciiStudio.renderAt(${angle})`);
    const b64 = String(dataUrl).split(",")[1];
    if (!b64) throw new Error(`frame ${i}: renderAt returned no image`);
    const file = path.join(OUT, `frame-${String(i).padStart(3, "0")}.png`);
    fs.writeFileSync(file, Buffer.from(b64, "base64"));
    written.push(file);
  }
  ws.close();
  console.log(
    `studio: ${written.length} frames at ${box.w}x${box.h} -> ${OUT}\n` +
      `studio: canvas is ${box.w}x${box.h}; composite onto the wallpaper size next`,
  );
}

main().catch((e) => {
  console.error("loop_from_studio:", e.message);
  process.exit(1);
});
