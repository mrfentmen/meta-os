// Node built-in test runner, no dependencies:  node --test tests/pwa-manifest.test.mjs
// Covers the installable-app surface (UI fix list item 4c): the web
// manifest and the 180px touch icon exist at the repo root, the
// manifest parses and names this app with the icon as its 180x180
// entry, index.html links both files, and the app server's static
// MIME table serves both extensions — otherwise the links would
// still 404 when served, exactly the failure this item fixes.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const serverJs = readFileSync(new URL("../server/server.mjs", import.meta.url), "utf8");
const manifestRaw = readFileSync(new URL("../manifest.webmanifest", import.meta.url), "utf8");
const manifest = JSON.parse(manifestRaw);
const icon = readFileSync(new URL("../icon-180.png", import.meta.url));

test("manifest names the app and points at the 180px icon", () => {
  assert.equal(manifest.name, "MetaOS");
  assert.equal(manifest.short_name, "MetaOS");
  assert.equal(manifest.start_url, "/");
  assert.equal(manifest.display, "standalone");
  const entry = (manifest.icons ?? []).find((i) => i.src === "/icon-180.png");
  assert.ok(entry, "manifest lists /icon-180.png");
  assert.equal(entry.sizes, "180x180");
  assert.equal(entry.type, "image/png");
});

test("icon-180.png is a real 180x180 PNG", () => {
  assert.deepEqual([...icon.subarray(0, 8)], [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a], "PNG magic");
  const width = icon.readUInt32BE(16);
  const height = icon.readUInt32BE(20);
  assert.equal(width, 180);
  assert.equal(height, 180);
});

test("index.html links the manifest and the touch icon", () => {
  assert.ok(html.includes('<link rel="manifest" href="./manifest.webmanifest">'));
  assert.ok(html.includes('<link rel="apple-touch-icon" href="./icon-180.png">'));
});

test("app server serves .webmanifest and .png instead of 404", () => {
  assert.ok(serverJs.includes('".webmanifest": "application/manifest+json"'));
  assert.ok(serverJs.includes('".png": "image/png"'));
});
