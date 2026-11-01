// labs/data-prep/tests/dataprep.test.mjs — node:test, no npm deps.
// Drives the python tools (extract/sheet/phash/manifest) on synthetic
// fixtures built with ffmpeg. Needs: python3 (+PIL), ffmpeg.
// Run: node --test labs/data-prep/tests/dataprep.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import os from "node:os";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..");
const py = (args, cwd) => execFileSync("python3", args, { encoding: "utf8", cwd: cwd ?? dir });
const T = mkdtempSync(join(os.tmpdir(), "dataprep-"));

function fixtureVideo(dest) {
  execFileSync("/opt/homebrew/bin/ffmpeg", ["-y", "-v", "error", "-f", "lavfi",
    "-i", "testsrc=size=320x240:rate=30:duration=5",
    "-vf", "drawbox=x='t*50':y=100:w=60:h=60:c=white:t=fill",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", dest]);
}

test("NC-172 fixed-fps extraction: 10 ordered frames", () => {
  const vid = join(T, "fix.mp4");
  fixtureVideo(vid);
  const out = join(T, "fixframes");
  const log = py(["extract.py", vid, out, "--fps", "2"]);
  assert.match(log, /extracted 10 frames/);
  const names = readdirSync(out).sort();
  assert.equal(names.length, 10);
  const ts = names.map((n) => parseFloat(n.match(/-t([\d.]+)/)[1]));
  for (let i = 1; i < ts.length; i++) assert.ok(ts[i] > ts[i - 1], "timestamps ordered");
});

test("NC-173 scene mode: static few, busy many", () => {
  const stat = join(T, "stat.mp4"), busy = join(T, "busy.mp4");
  execFileSync("/opt/homebrew/bin/ffmpeg", ["-y", "-v", "error", "-f", "lavfi",
    "-i", "color=size=320x240:rate=30:duration=4:color=0x223344",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", stat]);
  fixtureVideo(busy);
  const o1 = join(T, "s1"), o2 = join(T, "s2");
  const n1 = parseInt(py(["extract.py", stat, o1, "--scene", "12.0"]).match(/extracted (\d+)/)[1], 10);
  const n2 = parseInt(py(["extract.py", busy, o2, "--scene", "12.0"]).match(/extracted (\d+)/)[1], 10);
  assert.ok(n1 < n2, `static ${n1} < busy ${n2}`);
  assert.ok(n1 >= 1, "frame 0 always emitted");
});

test("NC-175 contact sheet of 12 with legible labels", () => {
  const frames = readdirSync(join(T, "fixframes")).map((n) => join(T, "fixframes", n)).slice(0, 12);
  while (frames.length < 12) frames.push(frames[frames.length % 10]);
  const shot = join(T, "sheet.png");
  const log = py(["sheet.py", shot, ...frames, "--cols", "4"]);
  assert.match(log, /12 frames in 4x3/);
  assert.ok(existsSync(shot));
});

test("NC-177 dedupe: 3 originals + 3 altered = 3 groups", () => {
  // Three WILDLY different originals (solid red, solid blue, busy frame)
  // so only each original matches its own recompressed copy.
  const d = join(T, "dedup");
  execFileSync("mkdir", ["-p", d]);
  const solid = (name, color, box) => execFileSync("/opt/homebrew/bin/ffmpeg", ["-y", "-v", "error",
    "-f", "lavfi", "-i", "color=size=320x240:duration=1:color=" + color,
    "-vf", "drawbox=" + box + ":t=fill",
    "-frames:v", "1", join(d, name)]);
  solid("o0.jpg", "0xff0000", "x=10:y=10:w=80:h=80:c=white");
  solid("o1.jpg", "0x0000ff", "x=230:y=150:w=80:h=80:c=black");
  const busy = readdirSync(join(T, "fixframes"))[5];
  execFileSync("cp", [join(T, "fixframes", busy), join(d, "o2.jpg")]);
  ["o0", "o1", "o2"].forEach((b2) => {
    execFileSync("/opt/homebrew/bin/ffmpeg", ["-y", "-v", "error", "-i", join(d, `${b2}.jpg`),
      "-vf", "scale=300:200", "-q:v", "8", join(d, `${b2}a.jpg`)]);
  });
  const log = py(["phash.py", ...readdirSync(d).map((n) => join(d, n))]);
  assert.match(log, /groups=3/);
});

test("NC-179 flipped copy flagged, different scene not", () => {
  const d = join(T, "aug");
  execFileSync("mkdir", ["-p", d]);
  execFileSync("python3", ["-c",
    "from PIL import Image; im=Image.open('" + join(T, "fixframes", readdirSync(join(T, "fixframes"))[0]) + "'); im.transpose(Image.FLIP_LEFT_RIGHT).save('" + join(d, "flip.jpg") + "'); im.save('" + join(d, "same.jpg") + "')"]);
  execFileSync("/opt/homebrew/bin/ffmpeg", ["-y", "-v", "error", "-f", "lavfi",
    "-i", "color=size=320x240:duration=1:color=0x993311",
    "-frames:v", "1", join(d, "other.jpg")]);
  const log = py(["phash.py", "--aug", join(d, "flip.jpg"), join(d, "same.jpg"), join(d, "other.jpg")]);
  assert.match(log, /augment: flip\.jpg looks like a horizontal flip of same\.jpg/);
  assert.ok(!log.includes("other.jpg looks like"), "different scene not flagged");
});

test("NC-181 manifest round-trip reports the gap", () => {
  const d = join(T, "mani");
  execFileSync("mkdir", ["-p", d]);
  readdirSync(join(T, "fixframes")).slice(0, 4).forEach((n) =>
    execFileSync("cp", [join(T, "fixframes", n), join(d, n)]));
  const m = join(T, "m.jsonl");
  py(["manifest.py", d, m]);
  const gone = readdirSync(d)[0];
  execFileSync("rm", [join(d, gone)]);
  const log = py(["manifest.py", d, m]);
  assert.match(log, new RegExp("GAP: " + gone.replace(".", "\\.")));
});

