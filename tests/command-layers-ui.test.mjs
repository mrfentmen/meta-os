// Node built-in test runner, no dependencies:  node --test tests/command-layers-ui.test.mjs
// Covers the Phase-2 wiring at the text level (the suite's established
// pattern): the Layers group and both toggle buttons exist with the
// right defaults, command-map.js wires them to the layer code, the
// server exposes both proxy routes, and attributions name real sources.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const commandJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const layersJs = readFileSync(new URL("../js/command-layers.js", import.meta.url), "utf8");
const serverJs = readFileSync(new URL("../server/server.mjs", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

test("layers group has Fires and Radar toggles, off by default", () => {
  assert.ok(html.includes('role="group" aria-label="Map layers"'), "layers group missing");
  assert.ok(html.includes('id="cmd-layer-fires"'), "fires toggle missing");
  assert.ok(html.includes('id="cmd-layer-radar"'), "radar toggle missing");
  assert.ok(html.includes(">Fires<"), "Fires label missing");
  assert.ok(html.includes(">Radar<"), "Radar label missing");
});

test("map wires both toggles through a single toggleLayer", () => {
  assert.ok(commandJs.includes('els.layerFires.addEventListener("click", () => toggleLayer("fires"))'), "fires wiring missing");
  assert.ok(commandJs.includes('els.layerRadar.addEventListener("click", () => toggleLayer("radar"))'), "radar wiring missing");
  assert.ok(commandJs.includes("function toggleLayer(name)"), "toggleLayer missing");
});

test("map exposes layer entry points the UI calls", () => {
  for (const fn of ["setFiresLayer", "setRadarLayer", "refreshFires", "firstSymbolLayerId"]) {
    assert.ok(commandJs.includes(`function ${fn}`), `${fn} missing`);
  }
  assert.ok(commandJs.includes("cmd-fires-circles"), "fires circle layer missing");
  assert.ok(commandJs.includes('type: "raster"'), "raster layer missing");
});

test("honesty copy is present: hotspot disclaimer and no-key path", () => {
  assert.ok(commandJs.includes("not a confirmed fire"), "hotspot disclaimer missing");
  assert.ok(layersJs.includes("satellite detections, not confirmed fires"), "attribution disclaimer missing");
  assert.ok(commandJs.includes("no FIRMS key"), "no-key fallback copy missing");
});

test("server proxies both layers without leaking keys", () => {
  assert.ok(serverJs.includes("/api/fires"), "fires route missing");
  assert.ok(serverJs.includes("/api/weather/radar/"), "radar route missing");
  assert.ok(!serverJs.includes("firms.modaps.eosdis.nasa.gov/api/area/csv/${process.env"), "upstream URL must not inline env");
});
