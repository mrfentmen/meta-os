// Command view data layers: wildfire hotspots (NASA FIRMS) and
// weather radar (Iowa State IEM NEXRAD tiles).
//
// Pure helpers only — no DOM, no map, no fetch here. The map wiring
// lives in js/command-map.js, the fetching in server/fires.mjs and
// server/weather.mjs. Everything below is unit-testable with node:test.
//
// Honesty rules for these layers (same bar as the camera list):
// - A FIRMS hotspot is a satellite heat detection, never a confirmed
//   fire. Labels say "hotspot", never "fire".
// - Radar tiles are precipitation reflectivity, not current weather at
//   street level. No claim beyond what the tile shows.

export const FIRMS_REFRESH_MS = 15 * 60 * 1000;

// Which FIRMS source the server queries. VIIRS_SNPP_NRT is the
// daytime+night global 375 m product — the best free fire signal
// without authentication beyond the (free) MAP_KEY itself.
export const FIRMS_SOURCE = "VIIRS_SNPP_NRT";
export const FIRMS_DAY_RANGE = 1;

export const RADAR_OPACITY = 0.55;
export const RADAR_REFRESH_MS = 10 * 60 * 1000;

// Same-origin tile template handed to maplibre, which substitutes
// {z}/{x}/{y} itself. Served by our own /api/weather/radar proxy so
// the browser never hits a third party directly.
export const RADAR_TILE_TEMPLATE = "/api/weather/radar/{z}/{x}/{y}.png";export const RADAR_MAX_ZOOM = 12;

// Attributes, verbatim, so the footer/markup never invents them.
export const RADAR_ATTRIBUTION = "Radar: Iowa State IEM NEXRAD";
export const FIRMS_ATTRIBUTION = "Hotspots: NASA FIRMS (satellite detections, not confirmed fires)";

// Normalize one FIRMS CSV row (already split, header stripped) into
// the app's fire object. FIRMS area-CSV columns:
// latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,
// satellite,instrument,confidence,version,bright_ti5,frp,daynight.
// Returns null for rows that do not parse — the caller drops them and
// counts dropped rows, never inventing coordinates for a bad row.
export function normalizeFireRow(cells) {
  if (!Array.isArray(cells) || cells.length < 14) return null;
  const latitude = Number(cells[0]);
  const longitude = Number(cells[1]);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;
  const brightness = Number(cells[2]);
  const frp = cells[12] !== "" ? Number(cells[12]) : null;
  const confidence = typeof cells[9] === "string" && cells[9].length > 0 ? cells[9] : "?";
  const daynight = cells[13] === "D" || cells[13] === "N" ? cells[13] : "?";
  return {
    id: `firms-${latitude.toFixed(3)}-${longitude.toFixed(3)}-${cells[5] ?? ""}${cells[6] ?? ""}`,
    latitude,
    longitude,
    brightness: Number.isFinite(brightness) ? brightness : null,
    frp: frp !== null && Number.isFinite(frp) ? frp : null,
    confidence,
    daynight,
    satellite: typeof cells[7] === "string" ? cells[7] : "",
    acquired: `${cells[5] ?? ""} ${cells[6] ?? ""}`.trim(),
  };
}

// Minimal CSV split honoring double-quoted fields (FIRMS values are
// numbers and short codes, but never trust an upstream format).
export function splitCsvLine(line) {
  const out = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out.map((cell) => cell.trim());
}

// Parse a FIRMS area CSV payload into { fires, dropped }. The first
// non-empty line is the header and is skipped, not parsed.
export function parseFirmsCsv(text) {
  const fires = [];
  let dropped = 0;
  if (typeof text !== "string" || text.length === 0) return { fires, dropped };
  const lines = text.split(/\r?\n/);
  let headerSeen = false;
  for (const line of lines) {
    if (line.trim() === "") continue;
    if (!headerSeen) {
      headerSeen = true;
      continue;
    }
    const fire = normalizeFireRow(splitCsvLine(line));
    if (fire) fires.push(fire);
    else dropped += 1;
  }
  return { fires, dropped };
}

// GeoJSON for one map source update. Coordinates are the data's own
// [longitude, latitude] — never projected or snapped here.
export function firesToGeoJson(fires) {
  return {
    type: "FeatureCollection",
    features: fires.map((fire) => ({
      type: "Feature",
      id: fire.id,
      geometry: { type: "Point", coordinates: [fire.longitude, fire.latitude] },
      properties: {
        brightness: fire.brightness,
        frp: fire.frp,
        confidence: fire.confidence,
        daynight: fire.daynight,
        satellite: fire.satellite,
        acquired: fire.acquired,
      },
    })),
  };
}

// Circle radius in pixels from fire radiative power. Square-root
// scaling keeps monster fires from swallowing the map; the 4..14 px
// clamp keeps single-pixel detections tappable.
export function fireRadiusPixels(frp) {
  if (typeof frp !== "number" || !Number.isFinite(frp) || frp <= 0) return 4;
  return Math.min(14, Math.max(4, 2 + Math.sqrt(frp) / 2));
}

// Circle color from FIRMS confidence code. Unknown codes fall back to
// the same orange as "nominal" rather than disappearing.
export function fireColorFor(confidence, daynight) {
  const dim = daynight === "N";
  switch (confidence) {
    case "h":
      return dim ? "#ff5a2a" : "#ff3b1f";
    case "n":
      return dim ? "#ff9a3c" : "#ff7b1c";
    default:
      return dim ? "#ffb35c" : "#ffa63d";
  }
}

// Same-origin tile template the map hands to maplibre. The server
// proxies IEM so no browser ever hits a third party directly.
export function radarTileUrl(z, x, y) {
  return `/api/weather/radar/${z}/${x}/${y}.png`;
}

// Tile-coordinate validation shared by client (never request junk)
// and server (never fetch junk). Returns null when invalid.
export function validRadarTile(z, x, y) {
  const zi = typeof z === "string" ? Number(z) : z;
  const xi = typeof x === "string" ? Number(x) : x;
  const yi = typeof y === "string" ? Number(y) : y;
  if (!Number.isInteger(zi) || !Number.isInteger(xi) || !Number.isInteger(yi)) return null;
  if (zi < 0 || zi > RADAR_MAX_ZOOM) return null;
  const n = 2 ** zi;
  if (xi < 0 || xi >= n || yi < 0 || yi >= n) return null;
  return { z: zi, x: xi, y: yi };
}
