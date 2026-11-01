// HN-057 Hortus run viewer: parser + chart + champion card.
// The fixtures below are FORMAT fixtures only — they prove the parser
// and chart code, and are never presented as real Hortus runs. No real
// Hortus run JSONLs exist in this repo today, so the live board shows
// its honest empty state (BLOCKED-WITH-PLAN on the real-data proof).
// Run: node --test tests/surfaces-hortus.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { parseHortusJsonl, hortusChart, hortusChampion } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

const FORMAT_FIXTURE = [
  '{"generation": 2, "best": 90, "mean": 70}',
  '{"generation": 1, "best": 80, "mean": 60}',
  '{"generation": 2, "best": 95, "mean": 72}',
  'not json',
  '{"generation": 3, "best": "high", "mean": 75}',
  '',
].join("\n");

test("parser groups by generation, sorts, takes max best and mean average, skips malformed", () => {
  const { series, skipped } = parseHortusJsonl(FORMAT_FIXTURE);
  assert.equal(series.length, 2);
  assert.equal(series[0].generation, 1);
  assert.equal(series[0].best, 80);
  assert.equal(series[0].mean, 60);
  assert.equal(series[1].generation, 2);
  assert.equal(series[1].best, 95);
  assert.equal(series[1].mean, 71);
  assert.equal(skipped, 2);
});

test("chart draws best solid and mean dashed with generation labels", () => {
  const { series } = parseHortusJsonl(FORMAT_FIXTURE);
  const html = hortusChart(series);
  assert.match(html, /<svg[^>]*hortus-chart/);
  assert.match(html, /class="hortus-best"/);
  assert.match(html, /class="hortus-mean"/);
  assert.match(html, />G1</);
  assert.match(html, />G2</);
});

test("chart with no series is an honest empty state, not a drawn line", () => {
  const html = hortusChart([]);
  assert.match(html, /No Hortus runs in this repo yet/);
  assert.doesNotMatch(html, /<svg/);
});

test("champion card shows rung label and params, nothing filled in", () => {
  const html = hortusChampion({
    champion: { organism: "9086", rung: "rung-1", params: { fins: 40 } },
  });
  assert.match(html, /9086/);
  assert.match(html, /rung-1/);
  assert.match(html, /40/);
  assert.match(hortusChampion(null), /No champion recorded yet/);
  assert.match(hortusChampion({}), /No champion recorded yet/);
});

test("boards page has a hortus section wired to the empty state", () => {
  assert.match(surfacesHtml, /id="board-hortus"/);
  assert.match(surfacesHtml, /id="hortus-content"/);
  assert.match(surfacesHtml, /os\/hortus\/runs\/\*\.jsonl/);
});
