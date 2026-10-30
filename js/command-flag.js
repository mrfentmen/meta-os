// Command view: pure pin-state, flag, watch-list, and camera-list
// logic for the map-first Command view (js/command-map.js). No DOM
// access: safe to import from the browser and from node tests, like
// the other pure modules in this directory.
//
// THE FLAG RULE (Del's Command-view direction, Oct 30): a watched
// camera's pin turns red when its latest assessment category falls
// OUTSIDE the product's baseline set. Red means exactly "the latest
// assessment flagged this camera for human review" — never that an
// incident or a crime was detected. A later baseline result clears
// the red state. The assessment contract already carries
// requires_human_review on every result; the flag here is purely the
// category rule below, so a steam-or-fog call (a look-alike the model
// correctly cleared) never paints a pin red.
//
// Baseline sets, per product, from the category lists in
// js/products.js:
// - vigiles: "normal activity", "indeterminate" — the product's
//   nothing-to-report class and its cannot-tell class.
// - medicus: "normal activity", "indeterminate" — same shape.
// - ignis: "no hazard visible", "indeterminate", plus the two
//   look-alike classes "steam or fog" and "flame-like lighting".
//   The Ignis look-alike scoreboard (index.html) groups those two as
//   LOOK-ALIKES, apart from the HAZARDS "visible smoke" / "visible
//   flame"; they are affirmative not-a-fire readings, so they belong
//   to the baseline. "obscured or distant hazard" is NOT baseline:
//   the assessment itself names a possible hazard, so it flags.

export const BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"];

export const MAX_WATCHED = 6;

export const BASELINE_CATEGORIES = {
  vigiles: ["normal activity", "indeterminate"],
  ignis: ["no hazard visible", "steam or fog", "flame-like lighting", "indeterminate"],
  medicus: ["normal activity", "indeterminate"],
};

const BASELINE_SETS = Object.fromEntries(
  Object.entries(BASELINE_CATEGORIES).map(([id, cats]) => [id, new Set(cats)]),
);

// Incident priority per flagged category, from the same category
// sets in js/products.js. HIGH = a person may be hurt or a hazard is
// affirmatively visible; MEDIUM = possible trouble that needs eyes
// soon; any other flagged category (none exist in the current sets
// beyond these) falls back to LOW in priorityForCategory.
export const CATEGORY_PRIORITY = {
  vigiles: {
    "person down": "high",
    "possible altercation": "high",
    "physical contact": "high",
    "energetic movement": "medium",
    "ambiguous gesture": "medium",
    "staged verbal dispute": "medium",
  },
  ignis: {
    "visible flame": "high",
    "visible smoke": "high",
    "obscured or distant hazard": "medium",
  },
  medicus: {
    "person on ground": "high",
    "person motionless": "high",
    "vehicle collision scene": "high",
    "crowd gathered around a person": "medium",
    "blocked crew access": "medium",
  },
};

// Priority of a flagged category, or null when the category does not
// flag at all (baseline or unknown), so a queue entry is only ever
// created for a real flag.
export function priorityForCategory(productId, category) {
  if (!isFlaggedCategory(productId, category)) return null;
  return CATEGORY_PRIORITY[productId]?.[category] ?? "low";
}

// How a flagged camera's pin should pulse, from its flag state and
// its open (not cleared) incidents:
// - "fast": an unseen HIGH incident — the new-alert signal.
// - "slow": an unseen MEDIUM/LOW incident — flagged, still unseen.
// - "steady": flagged, but every incident has been seen.
// - "none": not flagged.
// Pulse pattern, not just color, carries the priority (Del's
// Command-view direction, Oct 30).
export function pulseModeFor(flagged, openIncidents) {
  if (!flagged) return "none";
  const unseen = (openIncidents ?? []).filter((incident) => incident && !incident.seen);
  if (unseen.some((incident) => incident.priority === "high")) return "fast";
  if (unseen.length > 0) return "slow";
  return "steady";
}

// The incident queue: ONE system queue for all three divisions
// (Del's unification ruling, Oct 30 — one system, three divisions
// inside it). An incident belongs to the system, not to the
// division that raised it: it stays in the queue, on the map, and
// in the flagged count no matter which division is active. Each
// incident records its ORIGIN division (productId) so the UI can
// tag where it came from.
//
// One open incident per (camera, division). An incident is created
// on a flag's rising edge under its division (or when that
// division's flagged category changes under its open incident —
// the old one is superseded and a fresh unseen incident takes its
// place). A flag or a baseline result from a DIFFERENT division
// never supersedes or clears this division's incident: two
// divisions can hold open incidents on the same camera at once,
// and only a baseline result from the SAME division clears its
// own. Selecting an incident marks it seen, which is what slows
// the pin's pulse. All state is session-local and derived from
// real assessment results only.
export class IncidentQueue {
  constructor() {
    this._items = [];
    this._seq = 0;
  }

  // All incidents this session, newest first.
  list() {
    return [...this._items].sort((a, b) => b.seq - a.seq);
  }

  // The open incident (not cleared, not superseded) for a camera.
  // With a productId, only that division's open incident matches;
  // without one, the newest open incident for the camera (kept for
  // callers that only need "is anything open here").
  openForCamera(cameraId, productId = null) {
    const open = this._items.filter(
      (incident) =>
        incident.cameraId === cameraId &&
        incident.open &&
        (productId === null || incident.productId === productId),
    );
    return open.sort((a, b) => b.seq - a.seq)[0] ?? null;
  }

  // Every open incident for a camera, newest first — one per
  // division that currently flags it.
  openIncidentsForCamera(cameraId) {
    return this._items
      .filter((incident) => incident.cameraId === cameraId && incident.open)
      .sort((a, b) => b.seq - a.seq);
  }

  // Record a flagged result. Returns { incident, created } — created
  // is false when the same category is already open for the camera
  // under the same division (the existing incident is refreshed,
  // not duplicated). An open incident from another division is
  // left untouched.
  add({ cameraId, productId, category, timestamp, thumbnail = null }) {
    const priority = priorityForCategory(productId, category);
    if (priority === null) return { incident: null, created: false };
    const open = this.openForCamera(cameraId, productId);
    if (open && open.category === category) {
      open.timestamp = timestamp;
      if (thumbnail) open.thumbnail = thumbnail;
      return { incident: open, created: false };
    }
    if (open) {
      open.open = false;
      open.cleared = true;
      open.clearedReason = "superseded";
    }
    this._seq += 1;
    const incident = {
      id: `incident-${this._seq}`,
      seq: this._seq,
      cameraId,
      productId,
      category,
      priority,
      timestamp,
      thumbnail,
      seen: false,
      open: true,
      cleared: false,
      clearedReason: null,
    };
    this._items.push(incident);
    return { incident, created: true };
  }

  // A baseline (non-flag) result: clears the open incident OF THE
  // SAME DIVISION that produced the result. A baseline result from
  // another division clears nothing here — that division's
  // incident stays open. Called without a productId, clears the
  // camera's newest open incident (legacy single-division form).
  // Returns the cleared incident or null.
  clearForCamera(cameraId, productId = null) {
    const open = this.openForCamera(cameraId, productId);
    if (!open) return null;
    open.open = false;
    open.cleared = true;
    open.clearedReason = "baseline result";
    return open;
  }

  // Mark one incident seen (operator selected it). Returns it, or
  // null for an unknown id.
  markSeen(id) {
    const incident = this._items.find((item) => item.id === id);
    if (!incident) return null;
    incident.seen = true;
    return incident;
  }
}

export function isBaselineCategory(productId, category) {
  const set = BASELINE_SETS[productId];
  if (!set) return false;
  return typeof category === "string" && set.has(category);
}

// True when this assessment category should paint the camera's pin
// red: a real category string, for a known product, outside the
// product's baseline set. Anything else (no category, unknown
// product) never flags — the view shows only what the rule covers.
export function isFlaggedCategory(productId, category) {
  if (typeof category !== "string" || category.length === 0) return false;
  if (!Object.hasOwn(BASELINE_SETS, productId)) return false;
  return !BASELINE_SETS[productId].has(category);
}

// Pin visual state from the camera's watch/flag state. Flagged wins
// over watched; a camera that is neither is a plain idle dot.
export function pinStateFor({ watched = false, flagged = false } = {}) {
  if (flagged) return "flagged";
  if (watched) return "watched";
  return "idle";
}

// Fold one assessment result into a camera's flag state. Returns the
// new state plus whether the flag flipped, so the caller can raise
// an alert card exactly on the rising edge (baseline -> flagged) and
// clear the pin on the falling edge (flagged -> baseline).
export function applyAssessmentToFlag(currentFlagged, productId, category) {
  const flagged = isFlaggedCategory(productId, category);
  return { flagged, changed: flagged !== Boolean(currentFlagged) };
}

// The watch list: an ordered, capped set of camera ids. Only watched
// cameras are ever sampled for assessment. The cap is part of the
// honesty contract — the UI states it ("Watch list full (max 6)").
export class WatchList {
  constructor(max = MAX_WATCHED) {
    if (!(max > 0)) throw new RangeError("WatchList max must be > 0");
    this.max = max;
    this._ids = [];
  }

  get size() {
    return this._ids.length;
  }

  get full() {
    return this._ids.length >= this.max;
  }

  has(id) {
    return this._ids.includes(id);
  }

  list() {
    return [...this._ids];
  }

  // Returns { ok: true } or { ok: false, reason: "full" | "duplicate" }.
  add(id) {
    if (this.has(id)) return { ok: false, reason: "duplicate" };
    if (this.full) return { ok: false, reason: "full" };
    this._ids.push(id);
    return { ok: true };
  }

  // Returns true when the id was present and removed.
  remove(id) {
    const i = this._ids.indexOf(id);
    if (i === -1) return false;
    this._ids.splice(i, 1);
    return true;
  }

  // Returns { ok, watched } — watched is the state after the toggle.
  toggle(id) {
    if (this.has(id)) {
      this.remove(id);
      return { ok: true, watched: false };
    }
    const added = this.add(id);
    return { ok: added.ok, watched: added.ok, reason: added.reason ?? null };
  }

  clear() {
    this._ids = [];
  }
}

// Round-robin over the watch list: the id after lastSampledId, or the
// first id when the last one is unknown or no longer watched. Null
// when nothing is watched (nothing may be sampled).
export function nextWatchedId(watchedIds, lastSampledId) {
  if (!Array.isArray(watchedIds) || watchedIds.length === 0) return null;
  const i = watchedIds.indexOf(lastSampledId);
  if (i === -1) return watchedIds[0];
  return watchedIds[(i + 1) % watchedIds.length];
}

// Great-circle distance in meters between two {latitude, longitude}
// points (haversine). Used for real proximity answers only — e.g.
// the building popup's nearest cameras, computed from the loaded
// camera list. Nothing about a camera's position is ever guessed:
// the NYCTMC API publishes no heading, so the view draws no
// direction cones, only this distance math and a ground ring.
export function distanceMeters(a, b) {
  const R = 6371000;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);
  const h =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

// Cameras within radiusMeters of a point, nearest first, each with
// its real distance attached. Powers the building popup's "nearest
// cameras" list — computed from the loaded list, never invented.
export function nearestCameras(cameras, point, radiusMeters, limit = 3) {
  if (!Array.isArray(cameras) || !point) return [];
  return cameras
    .map((camera) => ({ camera, distance: distanceMeters(camera, point) }))
    .filter((entry) => Number.isFinite(entry.distance) && entry.distance <= radiusMeters)
    .sort((a, b) => a.distance - b.distance)
    .slice(0, limit);
}

// A GeoJSON polygon ring approximating a ground circle (for the
// selected camera's radius ring on the 3D map). Returns [lng, lat]
// pairs, closed (first == last). Pure destination-point math on a
// spherical earth; the ring marks a radius, never a viewing
// direction — the API publishes no camera heading.
export function circlePolygon(latitude, longitude, radiusMeters, points = 64) {
  const R = 6371000;
  const angular = radiusMeters / R;
  const lat1 = (latitude * Math.PI) / 180;
  const lng1 = (longitude * Math.PI) / 180;
  const ring = [];
  for (let i = 0; i <= points; i += 1) {
    const bearing = (i / points) * 2 * Math.PI;
    const lat2 = Math.asin(
      Math.sin(lat1) * Math.cos(angular) +
        Math.cos(lat1) * Math.sin(angular) * Math.cos(bearing),
    );
    const lng2 =
      lng1 +
      Math.atan2(
        Math.sin(bearing) * Math.sin(angular) * Math.cos(lat1),
        Math.cos(angular) - Math.sin(lat1) * Math.sin(lat2),
      );
    ring.push([(lng2 * 180) / Math.PI, (lat2 * 180) / Math.PI]);
  }
  return ring;
}

// Validate one raw camera record (NYCTMC API shape) into the fields
// the view uses, or null when the record cannot support a pin: the
// view never plots a camera whose coordinates or image URL it does
// not actually have.
export function normalizeCamera(raw) {
  if (!raw || typeof raw !== "object") return null;
  const { id, name, latitude, longitude, area, isOnline, imageUrl } = raw;
  if (typeof id !== "string" || id.length === 0) return null;
  if (typeof name !== "string" || name.length === 0) return null;
  if (typeof area !== "string" || area.length === 0) return null;
  if (typeof imageUrl !== "string" || imageUrl.length === 0) return null;
  if (typeof latitude !== "number" || !Number.isFinite(latitude)) return null;
  if (typeof longitude !== "number" || !Number.isFinite(longitude)) return null;
  return { id, name, latitude, longitude, area, isOnline, imageUrl };
}

export function isCameraOnline(camera) {
  return Boolean(camera) && (camera.isOnline === "true" || camera.isOnline === true);
}

// Group cameras by borough for the list rail: the five boroughs in
// fixed order, any other area after them, empty groups omitted.
// Camera order inside a group follows the input order.
export function groupCamerasByBorough(cameras) {
  const groups = new Map();
  for (const camera of cameras ?? []) {
    if (!camera || typeof camera.area !== "string") continue;
    if (!groups.has(camera.area)) groups.set(camera.area, []);
    groups.get(camera.area).push(camera);
  }
  const ordered = [];
  for (const area of BOROUGHS) {
    if (groups.has(area)) {
      ordered.push({ area, cameras: groups.get(area) });
      groups.delete(area);
    }
  }
  for (const [area, list] of groups) {
    ordered.push({ area, cameras: list });
  }
  return ordered;
}

// The list rail's search filter: case-insensitive substring match on
// camera name or borough. An empty or blank query returns everything.
export function filterCameras(cameras, query) {
  const list = Array.isArray(cameras) ? cameras : [];
  const q = typeof query === "string" ? query.trim().toLowerCase() : "";
  if (q.length === 0) return [...list];
  return list.filter(
    (camera) =>
      camera &&
      ((typeof camera.name === "string" && camera.name.toLowerCase().includes(q)) ||
        (typeof camera.area === "string" && camera.area.toLowerCase().includes(q))),
  );
}
