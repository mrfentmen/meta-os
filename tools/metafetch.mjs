#!/usr/bin/env node
// metafetch — the Meta OS system screen, neofetch-style, except the
// logo SPINS. It runs the actual ribbon renderer (js/logo-background.js,
// the same code that draws the website and face backgrounds) against a
// recording canvas shim, and prints each frame as terminal text with
// ANSI colour. Info lines are the machine's real record (source named
// in the footer); uptime is this process's own, live.
//
//   node tools/metafetch.mjs            animate until Ctrl-C
//   node tools/metafetch.mjs --once     one static frame
//   node tools/metafetch.mjs --frames N print N frames (tests/capture)
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const RENDERER = [
  process.env.METAFETCH_RENDERER,
  path.join(HERE, "..", "js", "logo-background.js"),
  path.join(HERE, "logo-background.js"),
].find((p) => p && fs.existsSync(p));
if (!RENDERER) { console.error("logo-background.js not found"); process.exit(1); }

const W = 110, H = 46, CELL = 10;
const PALETTE = ["#062258", "#07357f", "#0750bc", "#4f7ec2", "#6a96d8", "#8ab4e8", "#a8c8f0", "#c8ddf8", "#eaf2ff"];
const ANSI = [17, 19, 20, 26, 27, 33, 75, 111, 153];
const SPEC = "#eafcff";

/* ---- recording canvas + browser shims ---- */
let frameCells = new Map();
const ctx = {
  fillStyle: "#fff", shadowColor: "", shadowBlur: 0, font: "", textAlign: "", textBaseline: "",
  setTransform() {},
  clearRect() { frameCells = new Map(); },
  fillText(ch, x, y) {
    const col = Math.round(x / CELL - 0.5), row = Math.round(y / CELL - 0.5);
    if (col < 0 || row < 0 || col >= W || row >= H) return;
    const idx = this.fillStyle === SPEC ? 9 : PALETTE.indexOf(this.fillStyle);
    frameCells.set(row * W + col, { ch, idx: Math.max(0, idx) });
  },
};
const canvas = {
  width: 0, height: 0, style: {},
  getBoundingClientRect: () => ({ width: W * CELL, height: H * CELL }),
  getContext: () => ctx,
};
const rafQ = [];
const store = { "meta-trio-logo-speed": "100" };
globalThis.window = globalThis;
globalThis.document = {
  body: { dataset: { product: "vigiles" } },
  hidden: false,
  getElementById: () => canvas,
  addEventListener() {},
};
globalThis.localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
globalThis.matchMedia = () => ({ matches: false });
globalThis.requestAnimationFrame = (cb) => { rafQ.push(cb); return rafQ.length; };
globalThis.addEventListener = () => {};
globalThis.devicePixelRatio = 1;

eval(fs.readFileSync(RENDERER, "utf8"));

function step(n) { for (let i = 0; i < n; i++) { const cbs = rafQ.splice(0); for (const cb of cbs) cb(0); } }

/* ---- frame -> terminal lines (2x2 blocks, brightest wins) ---- */
function renderLines() {
  const lines = [];
  for (let r = 0; r < H; r += 2) {
    let line = "", last = -1;
    for (let c = 0; c < W; c += 2) {
      let best = null;
      for (let dr = 0; dr < 2; dr++) for (let dc = 0; dc < 2; dc++) {
        const cell = frameCells.get((r + dr) * W + (c + dc));
        if (cell && (!best || cell.idx > best.idx)) best = cell;
      }
      if (!best || best.ch === " ") { line += " "; last = -1; continue; }
      const code = best.idx >= 9 ? 195 : ANSI[Math.min(8, best.idx)];
      if (code !== last) { line += `\x1b[38;5;${code}m`; last = code; }
      line += best.ch;
    }
    lines.push(line + "\x1b[0m");
  }
  return lines;
}

function infoLines() {
  const up = Math.floor(process.uptime());
  const B = "\x1b[1m", R = "\x1b[0m", C = "\x1b[38;5;33m";
  return [
    `${B}Mrfentmen${R}${C}@${R}${B}metaos${R}`,
    "─".repeat(22),
    `${B}OS:${R}       Meta OS 0.1 (K6) x86_64`,
    `${B}Host:${R}     QEMU, bare-metal Rust kernel`,
    `${B}Kernel:${R}   META OS KERNEL - alive (K1)`,
    `${B}Uptime:${R}   ${Math.floor(up / 60)}m ${up % 60}s (this process, live)`,
    `${B}Programs:${R} hello · sleeper · crasher (ring 3)`,
    `${B}Tasks:${R}    7 (console is id 7)`,
    `${B}Heap:${R}     512K`,
    `${B}Shell:${R}    commands: status help uptime mem ps`,
    `${B}Gate:${R}     GATE GREEN 7/7, clean clone`,
    "",
    "record: os-build/logs/K7-boot.txt",
  ];
}

function fullFrame() {
  const logo = renderLines(), info = infoLines();
  const rows = Math.max(logo.length, info.length), out = [];
  for (let i = 0; i < rows; i++) out.push((logo[i] || "") + "  " + (info[i] || ""));
  return out.join("\n");
}

/* ---- modes ---- */
const args = process.argv.slice(2);
step(2); // first real frame (init + one render)
if (args.includes("--once")) {
  process.stdout.write(fullFrame() + "\n");
} else if (args.includes("--frames")) {
  const n = parseInt(args[args.indexOf("--frames") + 1] || "2", 10);
  for (let i = 0; i < n; i++) { process.stdout.write(fullFrame() + "\n---FRAME---\n"); step(24); }
} else {
  process.stdout.write("\x1b[?25l");
  const timer = setInterval(() => { process.stdout.write("\x1b[H" + fullFrame() + "\n"); step(3); }, 50);
  process.on("SIGINT", () => { clearInterval(timer); process.stdout.write("\x1b[?25h\n"); process.exit(0); });
}
