// Node built-in test runner, no dependencies:  node --test tests/command-layers-fire-weather.test.mjs
// Covers the pure data-layer helpers (js/command-layers.js): FIRMS CSV
// parsing and normalization, GeoJSON conversion, circle sizing and
// coloring, and radar tile validation. No network, no DOM, no map.

import test from "node:test";
import assert from "node:assert/strict";

import {
  FIRMS_ATTRIBUTION,
  FIRMS_DAY_RANGE,
  FIRMS_REFRESH_MS,
  FIRMS_SOURCE,
  RADAR_ATTRIBUTION,
  RADAR_MAX_ZOOM,
  RADAR_OPACITY,
  RADAR_TILE_TEMPLATE,
  fireColorFor,
  fireRadiusPixels,
  firesToGeoJson,
  normalizeFireRow,
  parseFirmsCsv,
  radarTileUrl,
  splitCsvLine,
  validRadarTile,
} from "../js/command-layers.js";

const ROW = ["40.12", "-74.01", "310.5", "1.0", "1.0", "2024-05-01", "1200", "N", "VIIRS", "n", "5", "400.1", "12.5", "D"];

test("CSV split honors quoted fields", () => {
  assert.deepEqual(splitCsvLine('a,"b,c",d'), ["a", "b,c", "d"]);
  assert.deepEqual(splitCsvLine('a,"b""c",d'), ["a", 'b"c', "d"]);
  assert.deepEqual(splitCsvLine("a, b ,c"), ["a", "b", "c"]);
});

test("normalizeFireRow keeps real detections, drops junk", () => {
  const fire = normalizeFireRow(ROW);
  assert.equal(fire.latitude, 40.12);
  assert.equal(fire.longitude, -74.01);
  assert.equal(fire.brightness, 310.5);
  assert.equal(fire.frp, 12.5);
  assert.equal(fire.confidence, "n");
  assert.equal(fire.daynight, "D");
  assert.equal(fire.satellite, "N");
  assert.ok(fire.id.startsWith("firms-"));
  assert.equal(normalizeFireRow(["x", "y"]), null);
  assert.equal(normalizeFireRow(["91", "0", "1", "1", "1", "d", "t", "s", "i", "h", "5", "1", "1", "D"]), null);
  assert.equal(normalizeFireRow(["40", "200", "1", "1", "1", "d", "t", "s", "i", "h", "5", "1", "1", "D"]), null);
  assert.equal(normalizeFireRow(null), null);
});

test("parseFirmsCsv skips the header and counts dropped rows", () => {
  const csv = [
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight",
    ROW.join(","),
    "bad,row",
    "",
    ["40.5", "-73.9", "300", "1", "1", "2024-05-01", "1300", "N", "VIIRS", "h", "5", "390", "", "N"].join(","),
  ].join("\n");
  const { fires, dropped } = parseFirmsCsv(csv);
  assert.equal(fires.length, 2);
  assert.equal(dropped, 1);
  assert.equal(fires[1].frp, null);
  assert.equal(fires[1].daynight, "N");
  assert.deepEqual(parseFirmsCsv(""), { fires: [], dropped: 0 });
});

test("firesToGeoJson emits data-owned coordinates", () => {
  const { fires } = parseFirmsCsv(`latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n${ROW.join(",")}`);
  const geo = firesToGeoJson(fires);
  assert.equal(geo.type, "FeatureCollection");
  assert.deepEqual(geo.features[0].geometry, { type: "Point", coordinates: [-74.01, 40.12] });
  assert.equal(geo.features[0].properties.confidence, "n");
});

test("fire radius stays tappable and bounded", () => {
  assert.equal(fireRadiusPixels(null), 4);
  assert.equal(fireRadiusPixels(0), 4);
  assert.equal(fireRadiusPixels(-3), 4);
  const small = fireRadiusPixels(1);
  const big = fireRadiusPixels(10000);
  assert.ok(small >= 4 && small < big);
  assert.equal(fireRadiusPixels(1e12), 14);
});

test("fire colors distinguish confidence and dim at night", () => {
  assert.equal(fireColorFor("h", "D"), "#ff3b1f");
  assert.equal(fireColorFor("n", "D"), "#ff7b1c");
  assert.equal(fireColorFor("l", "N"), "#ffb35c");
  assert.equal(fireColorFor("?", "D"), "#ffa63d");
});

test("radar tile template and validation agree", () => {
  assert.equal(radarTileUrl(6, 19, 24), "/api/weather/radar/6/19/24.png");
  assert.deepEqual(validRadarTile(6, 19, 24), { z: 6, x: 19, y: 24 });
  assert.deepEqual(validRadarTile("6", "19", "24"), { z: 6, x: 19, y: 24 });
  assert.equal(validRadarTile(13, 0, 0), null);
  assert.equal(validRadarTile(6, 64, 0), null);
  assert.equal(validRadarTile(6, 0, -1), null);
  assert.equal(validRadarTile(6.5, 0, 0), null);
  assert.ok(RADAR_TILE_TEMPLATE.includes("{z}") && RADAR_TILE_TEMPLATE.includes("{x}") && RADAR_TILE_TEMPLATE.includes("{y}"));
});

test("layer constants are sane", () => {
  assert.equal(FIRMS_SOURCE, "VIIRS_SNPP_NRT");
  assert.equal(FIRMS_DAY_RANGE, 1);
  assert.equal(FIRMS_REFRESH_MS, 15 * 60 * 1000);
  assert.ok(RADAR_OPACITY > 0 && RADAR_OPACITY <= 1);
  assert.ok(RADAR_MAX_ZOOM >= 6);
  assert.match(FIRMS_ATTRIBUTION, /FIRMS/);
  assert.match(RADAR_ATTRIBUTION, /IEM/);
});
