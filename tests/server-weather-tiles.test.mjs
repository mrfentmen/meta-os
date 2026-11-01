// Node built-in test runner, no dependencies:  node --test tests/server-weather-tiles.test.mjs
// Covers the IEM radar tile proxy (server/weather.mjs): coordinate
// validation, upstream URL shape, PNG validation, and failure modes —
// all through an injected stub fetch. No network.

import test from "node:test";
import assert from "node:assert/strict";

import { fetchRadarTile } from "../server/weather.mjs";

const PNG = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  Buffer.alloc(100, 0),
]);

function stubPng(seen) {
  return async (url) => {
    seen.url = String(url);
    return {
      ok: true,
      status: 200,
      arrayBuffer: async () => PNG,
    };
  };
}

test("fetchRadarTile proxies the IEM tile for valid NYC coordinates", async () => {
  const seen = {};
  const out = await fetchRadarTile(stubPng(seen), 6, 19, 24);
  assert.equal(out.status, 200);
  assert.equal(out.contentType, "image/png");
  assert.ok(Buffer.isBuffer(out.bytes));
  assert.ok(String(seen.url).includes("/nexrad-n0r/6/19/24.png"));
});

test("fetchRadarTile string coordinates are normalized", async () => {
  const seen = {};
  const out = await fetchRadarTile(stubPng(seen), "6", "19", "24");
  assert.equal(out.status, 200);
});

test("fetchRadarTile rejects out-of-range tiles without fetching", async () => {
  let hits = 0;
  const counting = async () => {
    hits += 1;
    throw new Error("must not fetch");
  };
  await assert.rejects(fetchRadarTile(counting, 13, 0, 0), /refused tile/);
  await assert.rejects(fetchRadarTile(counting, 6, 64, 0), /refused tile/);
  await assert.rejects(fetchRadarTile(counting, 6, 0, -1), /refused tile/);
  await assert.rejects(fetchRadarTile(counting, "z", "x", "y"), /refused tile/);
  assert.equal(hits, 0);
});

test("fetchRadarTile rejects non-PNG upstreams", async () => {
  const html = async () => ({ ok: true, status: 200, arrayBuffer: async () => Buffer.from("<html>") });
  await assert.rejects(fetchRadarTile(html, 6, 19, 24), /did not return a PNG/);
});

test("fetchRadarTile surfaces upstream HTTP failures", async () => {
  const gone = async () => ({ ok: false, status: 404, arrayBuffer: async () => Buffer.alloc(0) });
  await assert.rejects(fetchRadarTile(gone, 6, 19, 24), /HTTP 404/);
});
