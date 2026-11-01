// Node built-in test runner, no dependencies:  node --test tests/ui-wave-screenshots.test.mjs
// Covers HN-021 (screenshot pack): the sandbox has NO headless
// browser, so no captures are claimed. What is checked is that
// the shot list names all six changed surfaces, states the block
// honestly, and ships a capture script for the Mac run — and that
// no fake capture is present in the pack.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync, readdirSync } from "node:fs";

const pack = readFileSync(new URL("../docs/UI_SCREENSHOT_PACK.md", import.meta.url), "utf8");
const script = readFileSync(new URL("../scripts/capture-ui-screenshots.sh", import.meta.url), "utf8");

test("shot list names all six changed surfaces", () => {
  for (const surface of [
    "Command topbar + live ribbon",
    "Left rail: queue, cameras, loop feed",
    "Inspector + pin card",
    "Camera wall",
    "Console panels + help overlay",
    "Mobile 390 px stacked view",
  ]) {
    assert.ok(pack.includes(surface), `shot list must name ${surface}`);
  }
});

test("pack states the block honestly and pairs before/after", () => {
  assert.match(pack, /Status: BLOCKED — no captures exist yet/);
  assert.match(pack, /no `chromium`, `google-chrome`, or `firefox` binary/);
  assert.match(pack, /no capture is claimed/);
  assert.match(pack, /Before = `origin\/main` at capture time/);
  assert.match(pack, /after = this branch's tip/);
});

test("capture script exists and targets the real server", () => {
  assert.match(script, /google-chrome/);
  assert.match(script, /node server\/server\.mjs/);
  assert.match(script, /window-size=1440,900/);
  assert.match(script, /window-size=390,844/);
  assert.ok(existsSync(new URL("../scripts/capture-ui-screenshots.sh", import.meta.url)));
});

test("no fake captures are filed", () => {
  // If a screenshots dir ever appears, it must hold real files
  // made by the script (pngs) — and the pack must not claim a
  // capture that is not there. Today the dir does not exist.
  const dir = new URL("../docs/screenshots", import.meta.url);
  if (existsSync(dir)) {
    const pngs = readdirSync(dir).filter((f) => f.endsWith(".png"));
    assert.ok(pngs.length > 0, "a screenshots dir with no pngs is a fake pack");
  }
});
