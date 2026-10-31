// Same-origin proxy source for NASA FIRMS active-fire detections.
//
// The Command view wants live fire hotspots, but the FIRMS area API
// needs a MAP_KEY that must never ship to the browser — so
// server.mjs serves the normalized list itself at GET /api/fires.
// Without FIRMS_MAP_KEY in the server environment the route answers
// 503 and the app shows "no key" instead of inventing detections.
//
// Upstream docs: https://firms.modaps.eosdis.nasa.gov/api/ — the key
// itself is free at https://firms.modaps.eosdis.nasa.gov/api/map_key/.
// CSV columns: latitude,longitude,bright_ti4,scan,track,acq_date,
// acq_time,satellite,instrument,confidence,version,bright_ti5,frp,
// daynight. Daily composites, global `world` area, trailing 24 h.

import { FIRMS_DAY_RANGE, FIRMS_SOURCE, parseFirmsCsv } from "../js/command-layers.js";

const FIRMS_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv";
const UPSTREAM_TIMEOUT_MS = 15000;
const CACHE_TTL_MS = 15 * 60 * 1000;
const MAX_FIRES = 5000;

let cached = null; // { at: number, body: object }

// fetchImpl is the test seam; production uses the global fetch.
export async function fetchFires(fetchImpl = fetch, { mapKey = process.env.FIRMS_MAP_KEY, source = FIRMS_SOURCE, dayRange = FIRMS_DAY_RANGE } = {}) {
  if (!mapKey) {
    const err = new Error("FIRMS map key is not configured on the server. Set FIRMS_MAP_KEY in the server environment (free at https://firms.modaps.eosdis.nasa.gov/api/map_key/).");
    err.code = "no-key";
    throw err;
  }
  const url = `${FIRMS_API}/2.0/${encodeURIComponent(mapKey)}/${encodeURIComponent(source)}/world/${encodeURIComponent(String(dayRange))}`;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const res = await fetchImpl(url, { signal: ctrl.signal, cache: "no-store" });
    if (!res.ok) {
      throw new Error(`FIRMS API answered HTTP ${res.status}`);
    }
    const text = await res.text();
    const { fires, dropped } = parseFirmsCsv(text);
    return {
      fetchedAt: new Date().toISOString(),
      source,
      count: fires.length,
      dropped,
      fires: fires.slice(0, MAX_FIRES),
    };
  } finally {
    clearTimeout(timer);
  }
}

// Cached read with no-key passthrough: a 503 upstream is the caller's
// signal to show "fire data unavailable", never an empty map.
export async function readFiresCached(fetchImpl = fetch, options = {}, now = Date.now()) {
  if (cached && now - cached.at < CACHE_TTL_MS) return { ...cached.body, stale: true };
  const body = await fetchFires(fetchImpl, options);
  cached = { at: now, body };
  return { ...body, stale: false };
}

export function clearFiresCache() {
  cached = null;
}
