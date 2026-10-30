// Node built-in test runner, no dependencies:  node --test tests/command-view.test.mjs
// Covers the Command view's wiring at the text level (the suite's
// established pattern for UI structure): the section and its control
// ids exist in index.html, Leaflet is vendored and loaded, the view
// switch is in the header, the offline fallback camera subset is
// complete and well-formed (60 NYCTMC cameras, 12 per borough, exact
// API shape), the LA wall feeds are separate from the NYC map data,
// the app.js bridge routes through the existing submitAssessment,
// the command layer in styles.css sits before the pinned
// OPS-CONSOLE blocks, and the honesty labels are present verbatim.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { FALLBACK_CAMERAS, WALL_FEEDS } from "../js/camera-fallback.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const appJs = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const commandJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const maplibreJs = readFileSync(new URL("../vendor/maplibre/maplibre-gl.js", import.meta.url), "utf8");

test("command view section and header view switch exist", () => {
  assert.ok(html.includes('<section id="command-view" class="command-view"'));
  assert.ok(html.includes('id="btn-view-command"'));
  assert.ok(html.includes('id="btn-view-console"'));
  assert.ok(html.includes("IMPERIUM COMMAND"));
});

test("command view carries every control id the glue queries", () => {
  const ids = [
    "cmd-map", "cmd-map-note", "cmd-list-source", "cmd-search", "cmd-camera-list",
    "cmd-alerts", "cmd-alerts-empty", "cmd-wall", "cmd-count-online",
    "cmd-count-watching", "cmd-count-flagged", "cmd-insp-name", "cmd-insp-meta",
    "cmd-viewer-img", "cmd-viewer-updated", "cmd-watch-toggle", "cmd-assess-now",
    "cmd-sample-toggle", "cmd-mark-reviewed", "cmd-viewer-status", "cmd-assessment",
    "cmd-stepper", "cmd-stepper-note", "cmd-pin-card", "cmd-pin-card-img",
    "cmd-pin-card-name", "cmd-pin-card-meta", "cmd-pin-card-chip", "cmd-pin-card-div",
    "cmd-pin-card-watch", "cmd-pin-card-focus", "cmd-pin-card-close",
    "cmd-activity-text", "cmd-activity-count", "cmd-search-overlay",
    "cmd-ksearch", "cmd-kresults", "cmd-capture-canvas", "cmd-sys-backend",
    "cmd-sys-endpoint", "cmd-sys-product", "cmd-sys-sampler", "cmd-sys-model",
    "cmd-sys-latency", "cmd-sys-log", "cmd-sys-watched", "cmd-sys-flagged",
    "cmd-sys-samples", "cmd-sys-errors", "cmd-bar-watched", "cmd-bar-flagged",
    "cmd-ai-focus",
  ];
  for (const id of ids) {
    assert.ok(html.includes(`id="${id}"`), `index.html has #${id}`);
    assert.ok(commandJs.includes(`$("${id}")`) || commandJs.includes(`"${id}"`), `command-map.js uses #${id}`);
  }
  for (const product of ["vigiles", "ignis", "medicus"]) {
    assert.ok(html.includes(`data-cmd-product="${product}"`), `product chip for ${product}`);
  }
});

test("maplibre is vendored locally and loaded before the command module", () => {
  assert.ok(maplibreJs.includes("MapLibre GL JS"));
  assert.ok(maplibreJs.includes("v4.7.1"), "vendored build is MapLibre GL JS v4.7.1");
  const maplibreCss = html.indexOf('<link rel="stylesheet" href="vendor/maplibre/maplibre-gl.css">');
  const appCss = html.indexOf('<link rel="stylesheet" href="styles.css">');
  assert.ok(maplibreCss !== -1 && appCss !== -1 && maplibreCss < appCss, "maplibre css loads first so app overrides win");
  const maplibreTag = html.indexOf('<script src="vendor/maplibre/maplibre-gl.js"></script>');
  const commandTag = html.indexOf('<script type="module" src="js/command-map.js"></script>');
  assert.ok(maplibreTag !== -1 && commandTag !== -1 && maplibreTag < commandTag);
  assert.ok(!html.toLowerCase().includes("leaflet"), "no leaflet in the page");
  assert.ok(!commandJs.toLowerCase().includes("leaflet"), "no leaflet in the glue");
  assert.ok(commandJs.includes("https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"));
});

test("3d buildings, selection ring, modes, and AI focus are wired to real data only", () => {
  assert.ok(commandJs.includes('"fill-extrusion"'), "buildings are extruded");
  assert.ok(commandJs.includes("cmd-buildings-3d"));
  assert.ok(commandJs.includes('"source-layer": "buildings"'));
  assert.ok(commandJs.includes('["coalesce", ["get", "height"], 10]'), "extrusion height comes from the tile data");
  assert.ok(commandJs.includes("nearestCameras("), "building popup computes nearest cameras from the loaded list");
  assert.ok(commandJs.includes("circlePolygon("), "selection ring is a ground-radius polygon");
  assert.ok(commandJs.includes("cmd-selection-fill"), "selection ring layer exists");
  assert.ok(!commandJs.includes("unit") || !commandJs.includes("patrol"), "no simulated unit markers");
  for (const mode of ["city", "tactical", "incident"]) {
    assert.ok(html.includes(`data-cmd-mode="${mode}"`), `mode button ${mode}`);
    assert.ok(commandJs.includes(`mode === "${mode}"`), `mode preset ${mode} implemented`);
  }
  assert.ok(html.includes('id="cmd-ai-focus"'));
  assert.ok(commandJs.includes("function aiFocus()"));
  assert.ok(commandJs.includes("newestFlaggedCamera()"), "AI focus targets the newest real flag");
});

test("fallback subset: 60 cameras, 12 per borough, exact API shape", () => {
  assert.equal(FALLBACK_CAMERAS.length, 60);
  const byBorough = new Map();
  const ids = new Set();
  for (const cam of FALLBACK_CAMERAS) {
    byBorough.set(cam.area, (byBorough.get(cam.area) ?? 0) + 1);
    assert.ok(!ids.has(cam.id), `duplicate id ${cam.id}`);
    ids.add(cam.id);
    assert.equal(typeof cam.name, "string");
    assert.ok(cam.name.length > 0);
    assert.equal(typeof cam.latitude, "number");
    assert.equal(typeof cam.longitude, "number");
    assert.ok(cam.latitude > 40.4 && cam.latitude < 41.0, `${cam.name} latitude is NYC-range`);
    assert.ok(cam.longitude > -74.3 && cam.longitude < -73.6, `${cam.name} longitude is NYC-range`);
    assert.equal(cam.isOnline, "true");
    assert.equal(cam.imageUrl, `https://webcams.nyctmc.org/api/cameras/${cam.id}/image`);
  }
  assert.deepEqual(
    [...byBorough.entries()].sort(),
    [["Bronx", 12], ["Brooklyn", 12], ["Manhattan", 12], ["Queens", 12], ["Staten Island", 12]],
  );
});

test("wall feeds are the three verified Caltrans feeds, labeled Los Angeles, off the map data", () => {
  assert.equal(WALL_FEEDS.length, 3);
  for (const feed of WALL_FEEDS) {
    assert.ok(feed.imageUrl.startsWith("https://cwwp2.dot.ca.gov/"), feed.imageUrl);
    assert.ok(feed.area.includes("Los Angeles"), feed.area);
    assert.ok(!("latitude" in feed) && !("longitude" in feed), "wall feeds carry no map coordinates");
  }
});

test("app.js bridge exposes the existing pipeline, unchanged signature", () => {
  assert.ok(appJs.includes("window.MetaTrioCommand = {"));
  assert.ok(appJs.includes("submitAssessment: (product, timestamp, image, scenarioLabel, source) =>"));
  assert.ok(appJs.includes("currentProductId: () => currentProductId"));
  assert.ok(commandJs.includes("bridge.submitAssessment("));
  assert.ok(commandJs.includes('"live-test-feed"'), "command samples carry the honest source label");
  assert.ok(commandJs.includes("NYC DOT public traffic camera (test feed)"));
});

test("honesty labels are present in the command markup", () => {
  assert.ok(html.includes("Public NYC DOT traffic cameras used as TEST feeds"));
  assert.ok(html.includes("Only watched cameras are ever sampled"));
  assert.ok(html.includes("it is not an incident detection"));
  assert.ok(html.includes("Watch list max 6"));
  assert.ok(commandJs.includes("Offline camera list"), "offline state is named in the UI");
  assert.ok(commandJs.includes("Flagged for human review"), "flag language stays review, not detection");
});

test("command CSS layer is additive and sits before the pinned OPS-CONSOLE blocks", () => {
  const layerIdx = css.indexOf("/* COMMAND VIEW v2");
  const pinnedIdx = css.indexOf("/* OPS-CONSOLE-1");
  assert.ok(layerIdx !== -1, "command layer banner present");
  assert.ok(pinnedIdx !== -1, "pinned block still present");
  assert.ok(layerIdx < pinnedIdx, "command layer ends before the pinned blocks");
  const layer = css.slice(layerIdx, pinnedIdx);
  assert.ok(layer.includes("body[data-view=\"command\"] > main"), "console hides in command view");
  assert.ok(layer.includes(".cmd-pin--fast") && layer.includes(".cmd-pin--slow") && layer.includes(".cmd-pin--steady"));
  assert.ok(layer.includes("@keyframes cmd-pulse"));
  assert.ok(layer.includes('body[data-product="ignis"] .command-view'), "product tint hooks exist");
  assert.ok(layer.includes("#ff7a3c"), "ignis accent is orange-red, distinct from flag red");
});

test("stepper steps are the five real pipeline states, in order", () => {
  const idx = ["detected", "investigating", "analyzed", "awaiting-review", "reviewed"].map((key) =>
    commandJs.indexOf(`["${key}"`),
  );
  assert.ok(idx.every((i) => i !== -1));
  assert.deepEqual([...idx].sort((a, b) => a - b), idx, "steps appear in pipeline order");
});

test("the system is named Meta Imperium in display text only", () => {
  assert.ok(html.includes("<title>Meta Imperium — Visual Event Assessment Prototype</title>"));
  assert.ok(html.includes("<h1>Meta Imperium</h1>"), "header brand renamed");
  assert.ok(html.includes("IMPERIUM COMMAND"), "command wordmark renamed");
  assert.ok(html.includes("Meta Imperium · New York City"), "wordmark sub renamed");
  assert.ok(!html.includes("Meta Trio"), "no old brand left in the page");
  assert.ok(!html.includes("TRIO COMMAND"), "no old wordmark left in the page");
  // Identifiers are NOT renamed: the app.js bridge keeps its name.
  assert.ok(appJs.includes("window.MetaTrioCommand = {"), "bridge identifier unchanged");
});

test("one system: the queue is global across divisions, tagged by origin", () => {
  assert.ok(html.includes("One queue for all three divisions"), "queue copy reads as one system");
  assert.ok(commandJs.includes("clearForCamera(id, product)"), "clearing is scoped to the same division");
  assert.ok(commandJs.includes("flagByProduct"), "flag state is tracked per division");
  assert.ok(commandJs.includes("openIncidentsForCamera("), "pin pulse aggregates every division's incidents");
  assert.ok(commandJs.includes("makeDivisionTag("), "incidents render an origin division tag");
  assert.ok(commandJs.includes("thumbnail: cam.imageUrl"), "incidents record the camera thumbnail");
  const layer = css.slice(css.indexOf("/* COMMAND VIEW v2"), css.indexOf("/* OPS-CONSOLE-1"));
  for (const [cls, hex] of [
    [".cmd-div-tag--vigiles", "#53c8ff"],
    [".cmd-div-tag--ignis", "#ff7a3c"],
    [".cmd-div-tag--medicus", "#35e0a1"],
  ]) {
    assert.ok(layer.includes(cls), `division tag style ${cls}`);
    assert.ok(layer.includes(hex), `division accent ${hex}`);
  }
});
