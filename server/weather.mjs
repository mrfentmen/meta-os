// Same-origin tile proxy for Iowa State IEM NEXRAD radar tiles.
//
// The Command view overlays precipitation reflectivity, but the tile
// host is a third party — so server.mjs serves tiles itself at
// GET /api/weather/radar/:z/:x/:y.png and the browser never leaves
// the app origin. IEM tiles are free with no key; x/y are bounded by
// the zoom level so no crafted path can make the server fetch an
// arbitrary URL.

import { validRadarTile } from "../js/command-layers.js";

const UPSTREAM_TILE = (z, x, y) =>
  `https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0r/${z}/${x}/${y}.png`;
const UPSTREAM_TIMEOUT_MS = 10000;
const MAX_BYTES = 2 * 1024 * 1024;

// fetchImpl is the test seam; production uses the global fetch.
// Returns { status, contentType, bytes }. Throws on bad tile coords.
export async function fetchRadarTile(fetchImpl = fetch, z, x, y) {
  const valid = validRadarTile(z, x, y);
  if (!valid) {
    const err = new Error(`refused tile ${z}/${x}/${y}: outside the ${12}-zoom tile pyramid`);
    err.code = "bad-tile";
    throw err;
  }
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const res = await fetchImpl(UPSTREAM_TILE(valid.z, valid.x, valid.y), { signal: ctrl.signal });
    if (!res.ok) {
      throw new Error(`radar tile upstream answered HTTP ${res.status}`);
    }
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length === 0 || buf.length > MAX_BYTES) {
      throw new Error(`radar tile upstream returned ${buf.length} bytes`);
    }
    if (buf.length < 8 || buf[0] !== 0x89 || buf[1] !== 0x50 || buf[2] !== 0x4e || buf[3] !== 0x47) {
      throw new Error("radar tile upstream did not return a PNG");
    }
    return { status: 200, contentType: "image/png", bytes: buf };
  } finally {
    clearTimeout(timer);
  }
}
