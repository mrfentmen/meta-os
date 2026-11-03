// Same-origin proxy source for the NYC DOT / NYCTMC camera list.
//
// The Command view needs the live camera list, but the NYCTMC API
// sends no Access-Control-Allow-Origin header, so a browser fetch
// from the app's origin is blocked by CORS and the view fell back to
// the built-in 60-camera subset (js/camera-fallback.js) even on a
// healthy network. server.mjs therefore serves the list itself at
// GET /api/cameras: this module fetches it server-side (CORS does not
// apply server-to-server) and returns the upstream JSON untouched —
// the exact array shape the app already normalizes. Any upstream
// failure throws, so the route answers 502 and the app falls through
// to the direct URL and then the offline subset, labeled as such.

import { CAMERA_API_URL } from "../js/camera-fallback.js";

const UPSTREAM_TIMEOUT_MS = 8000;

// fetchImpl is the test seam; production uses the global fetch.
export async function fetchCameraList(fetchImpl = fetch) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const res = await fetchImpl(CAMERA_API_URL, {
      signal: ctrl.signal,
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`NYCTMC camera API answered HTTP ${res.status}`);
    }
    const raw = await res.json();
    if (!Array.isArray(raw)) {
      throw new Error("NYCTMC camera API did not return a JSON array");
    }
    return raw;
  } finally {
    clearTimeout(timer);
  }
}
