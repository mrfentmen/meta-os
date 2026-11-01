// HN-063 Camera wall source labels: every feed card shows its source
// + LIVE/TEST state in the UI itself, not just in data.
// Run: node --test tests/surfaces-camera-labels.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { cameraFeedState } from "../js/camera-fallback.js";

const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("live list maps to NYCTMC live + LIVE; fallback maps to Offline subset + TEST", () => {
  assert.deepEqual(cameraFeedState(false), { source: "NYCTMC live", state: "LIVE" });
  assert.deepEqual(cameraFeedState(true), { source: "Offline subset", state: "TEST" });
});

test("wall rows render source + state spans from the feed state", () => {
  assert.match(mapJs, /cameraFeedState\(state\.usingFallback\)/);
  assert.match(mapJs, /cmd-row-source/);
  assert.match(mapJs, /cmd-row-state--\$\{feed\.state\.toLowerCase\(\)\}/);
});

test("pin card meta shows the true source + state, not a hardcoded test feed", () => {
  assert.match(mapJs, /feed\.source.*feed\.state/);
  assert.doesNotMatch(mapJs, /NYC DOT test feed/);
});

test("CSS rules exist for source and both state badges", () => {
  assert.match(css, /\.cmd-row-source\s*\{/);
  assert.match(css, /\.cmd-row-state--live\s*\{/);
  assert.match(css, /\.cmd-row-state--test\s*\{/);
});

test("boards page notes the wall labels", () => {
  assert.match(surfacesHtml, /id="board-cameras"/);
});
