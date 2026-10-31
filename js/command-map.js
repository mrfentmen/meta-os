// Command view (map-first) for Meta Trio — browser glue.
//
// TRIO COMMAND: a full-bleed 3D New York City map (MapLibre GL,
// CARTO dark-matter vector style, buildings extruded from the tile
// data's own height values) with glass panels floating over it: an incident queue
// and camera list on the left, an inspector + system readouts on the
// right, a camera wall along the bottom, and a session activity
// strip. All state logic (flag rule, priorities, watch list,
// incident queue, list filtering) lives in the pure module
// js/command-flag.js; all camera data comes from the live NYCTMC
// API or the verbatim offline subset in js/camera-fallback.js.
//
// Honesty contract, enforced here:
// - These are public NYC DOT traffic cameras used as TEST feeds.
//   The three Los Angeles Caltrans tiles in the wall are display
//   only: never plotted on the map, never assessed.
// - ONLY watched cameras are ever sampled, through the existing
//   app.js pipeline (window.MetaTrioCommand bridge → the same
//   submitAssessment the webcam/still/video paths use, source
//   "live-test-feed"). Nothing implies citywide automated
//   monitoring.
// - A red pin means "the latest assessment flagged this camera for
//   human review" (category outside the product's baseline set in
//   js/command-flag.js) — never an incident or crime detection.
// - If the live camera list cannot be fetched, the UI says so
//   ("Offline camera list") and plots the built-in subset.
//
// The stepper in the inspector reflects real transitions only: a
// step lights when the thing it names actually happened for the
// selected camera (snapshot captured, request returned, result
// recorded, operator marked reviewed in this session).

import { CAMERA_API_URL, CAMERA_PROXY_URL, FALLBACK_CAMERAS, WALL_FEEDS } from "./camera-fallback.js";
import {
  MAX_WATCHED,
  WatchList,
  IncidentQueue,
  applyAssessmentToFlag,
  circlePolygon,
  distanceMeters,
  filterCameras,
  groupCamerasByBorough,
  isCameraOnline,
  nearestCameras,
  nextWatchedId,
  normalizeCamera,
  pulseModeFor,
} from "./command-flag.js";
import { PRODUCT_BY_ID } from "./products.js";
import { loopFeedItems, loopStatusText } from "./command-loop.js";
import { FrameSampler } from "./sampler.js";
import { downscaleImageToDataURL } from "./image_input.js";

const $ = (id) => document.getElementById(id);

const els = {
  view: $("command-view"),
  map: $("cmd-map"),
  listSource: $("cmd-list-source"),
  search: $("cmd-search"),
  cameraList: $("cmd-camera-list"),
  alerts: $("cmd-alerts"),
  alertsEmpty: $("cmd-alerts-empty"),
  wall: $("cmd-wall"),
  countOnline: $("cmd-count-online"),
  countWatching: $("cmd-count-watching"),
  countFlagged: $("cmd-count-flagged"),
  inspName: $("cmd-insp-name"),
  inspMeta: $("cmd-insp-meta"),
  viewerImg: $("cmd-viewer-img"),
  viewerUpdated: $("cmd-viewer-updated"),
  watchToggle: $("cmd-watch-toggle"),
  assessNow: $("cmd-assess-now"),
  sampleToggle: $("cmd-sample-toggle"),
  markReviewed: $("cmd-mark-reviewed"),
  viewerStatus: $("cmd-viewer-status"),
  assessment: $("cmd-assessment"),
  stepper: $("cmd-stepper"),
  stepperNote: $("cmd-stepper-note"),
  pinCard: $("cmd-pin-card"),
  pinCardImg: $("cmd-pin-card-img"),
  pinCardName: $("cmd-pin-card-name"),
  pinCardMeta: $("cmd-pin-card-meta"),
  pinCardChip: $("cmd-pin-card-chip"),
  pinCardDiv: $("cmd-pin-card-div"),
  pinCardWatch: $("cmd-pin-card-watch"),
  pinCardFocus: $("cmd-pin-card-focus"),
  pinCardClose: $("cmd-pin-card-close"),
  aiFocus: $("cmd-ai-focus"),
  activityText: $("cmd-activity-text"),
  activityCount: $("cmd-activity-count"),
  loopStatus: $("cmd-loop-status"),
  loopFeed: $("cmd-loop-feed"),
  overlay: $("cmd-search-overlay"),
  ksearch: $("cmd-ksearch"),
  kresults: $("cmd-kresults"),
  captureCanvas: $("cmd-capture-canvas"),
  sysBackend: $("cmd-sys-backend"),
  sysEndpoint: $("cmd-sys-endpoint"),
  sysProduct: $("cmd-sys-product"),
  sysSampler: $("cmd-sys-sampler"),
  sysModel: $("cmd-sys-model"),
  sysLatency: $("cmd-sys-latency"),
  sysLog: $("cmd-sys-log"),
  sysWatched: $("cmd-sys-watched"),
  sysFlagged: $("cmd-sys-flagged"),
  sysSamples: $("cmd-sys-samples"),
  sysErrors: $("cmd-sys-errors"),
  barWatched: $("cmd-bar-watched"),
  barFlagged: $("cmd-bar-flagged"),
  mapNote: $("cmd-map-note"),
};

const CAMERA_GLYPH =
  '<svg class="cmd-pin-glyph" viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 8.5h11v7h-11z M13.5 10.8 21 6.8v10.4l-7.5-4z" fill="currentColor"/></svg>';

const MAP_STYLE_URL = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
// Source id inside that style (verified against the live style
// JSON); its "buildings" layer carries height / min_height / name.
const BUILDINGS_SOURCE = "protomaps";
const PRODUCT_ACCENT_HEX = { vigiles: "#53c8ff", ignis: "#ff7a3c", medicus: "#35e0a1" };
const NYC_CENTER = [-73.9712, 40.7115];
const MANHATTAN_CENTER = [-73.9855, 40.758];

const state = {
  cameras: [],
  byId: new Map(),
  usingFallback: false,
  onlineCount: 0,
  query: "",
  focusedId: null,
  watch: new WatchList(MAX_WATCHED),
  queue: new IncidentQueue(),
  camState: new Map(), // id -> { flagged, flagByProduct, lastCategory, lastProduct, lastFlagged, lastAt, lastResult, phase, reviewed, errorNote }
  lastSampledId: null,
  sampler: null,
  counters: { samples: 0, assessed: 0, errors: 0 },
  lastModel: null,
  lastLatencyMs: null,
  activity: [], // command-local events, newest first { text, at }
  activityIdx: 0,
  map: null,
  mapLoaded: false,
  mode: "city",
  ringProduct: null,
  popup: null,
  markers: new Map(),
  gridDots: new Map(),
  wallTiles: [], // { img, base, label }
  bridge: null,
};

function cacheBust(url) {
  return `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`;
}

function fmtTime(value) {
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return typeof value === "string" ? value : "";
  return d.toLocaleTimeString([], { hour12: false });
}

// Division (product) display helpers. One system, three divisions:
// incidents carry their origin division, and the UI tags them with
// the division's short name in its accent color (the pin itself
// stays signal red — red means flagged, the tag says who flagged).
function divisionShortName(productId) {
  const name = PRODUCT_BY_ID[productId]?.displayName ?? productId ?? "";
  return name.replace(/^Meta /, "");
}

function makeDivisionTag(productId) {
  const tag = document.createElement("span");
  tag.className = `cmd-div-tag cmd-div-tag--${productId ?? "unknown"}`;
  tag.textContent = divisionShortName(productId);
  return tag;
}

function setStatus(message) {
  els.viewerStatus.textContent = message;
}

function pushActivity(text) {
  state.activity.unshift({ text, at: new Date() });
  if (state.activity.length > 40) state.activity.length = 40;
  state.activityIdx = 0;
  renderActivity();
}

// ---------------------------------------------------------------- bridge

async function getBridge() {
  if (state.bridge) return state.bridge;
  for (let i = 0; i < 20; i += 1) {
    if (window.MetaTrioCommand) {
      state.bridge = window.MetaTrioCommand;
      return state.bridge;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return null;
}

// ---------------------------------------------------------------- cameras

async function loadCameras() {
  let list = null;
  let live = false;
  // The NYCTMC API sends no Access-Control-Allow-Origin header, so a
  // direct browser fetch is blocked by CORS: try the app server's
  // same-origin proxy first, then the direct API (still useful where
  // CORS is not enforced), and only then the offline subset below.
  for (const source of [CAMERA_PROXY_URL, CAMERA_API_URL]) {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 8000);
      const res = await fetch(source, { signal: ctrl.signal, cache: "no-store" });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = await res.json();
      if (Array.isArray(raw)) {
        list = raw.map(normalizeCamera).filter(Boolean).filter(isCameraOnline);
      }
      live = Array.isArray(list) && list.length > 0;
    } catch {
      live = false;
    }
    if (live) break;
    list = null;
  }
  if (!live) {
    list = FALLBACK_CAMERAS.map(normalizeCamera).filter(Boolean);
    state.usingFallback = true;
  }
  state.cameras = list;
  state.byId = new Map(list.map((cam) => [cam.id, cam]));
  state.onlineCount = list.length;
  els.listSource.textContent = live
    ? `Live camera list — NYC DOT (NYCTMC) · ${list.length} cameras online`
    : `Offline camera list — built-in subset of ${list.length} NYC DOT cameras (live list unreachable from this network)`;
  pushActivity(
    live
      ? `Camera list loaded — ${list.length} online (live NYCTMC)`
      : `Offline camera list in use — ${list.length} cameras`,
  );
  renderPins();
  renderList();
  renderReadouts();
}

// ---------------------------------------------------------------- map + pins

function pinClassFor(id) {
  const entry = state.camState.get(id);
  if (entry?.flagged) {
    // Pulse from every division's open incident on this camera —
    // the fastest unseen signal wins (pulseModeFor's own rule).
    const mode = pulseModeFor(true, state.queue.openIncidentsForCamera(id));
    return `cmd-pin cmd-pin--flagged cmd-pin--${mode}`;
  }
  if (id === state.focusedId) return "cmd-pin cmd-pin--focused";
  if (state.watch.has(id)) return "cmd-pin cmd-pin--watched";
  return "cmd-pin cmd-pin--idle";
}

function createMarkerElement(cam) {
  const el = document.createElement("div");
  el.className = "cmd-marker";
  const span = document.createElement("span");
  span.className = pinClassFor(cam.id);
  span.innerHTML = CAMERA_GLYPH;
  el.appendChild(span);
  el.setAttribute("role", "button");
  el.setAttribute("aria-label", `View camera ${cam.name}, ${cam.area}`);
  el.addEventListener("click", () => selectCamera(cam.id, { openCard: true }));
  return { el, span };
}

function refreshPin(id) {
  const entry = state.markers.get(id);
  if (entry) entry.span.className = pinClassFor(id);
  const dot = state.gridDots.get(id);
  if (dot) dot.className = `cmd-grid-dot ${pinClassFor(id)}`;
}

function refreshAllPins() {
  for (const cam of state.cameras) refreshPin(cam.id);
}

function updateZoomClass() {
  if (!state.map) return;
  els.map.classList.toggle("cmd-zoom-near", state.map.getZoom() >= 14);
}

function initMap() {
  if (!window.maplibregl) return false;
  try {
    state.map = new window.maplibregl.Map({
      container: els.map,
      style: MAP_STYLE_URL,
      center: NYC_CENTER,
      zoom: 10.9,
      pitch: 40,
      bearing: 0,
      maxPitch: 70,
      attributionControl: { compact: true },
    });
  } catch {
    state.map = null;
    return false;
  }
  state.map.addControl(
    new window.maplibregl.NavigationControl({ visualizePitch: true }),
    "bottom-right",
  );
  state.map.on("zoom", () => {
    updateZoomClass();
    positionPinCard();
  });
  state.map.on("move", positionPinCard);
  state.map.on("load", () => {
    state.mapLoaded = true;
    addBuildings();
    addSelectionRing();
    updateSelectionRing();
    syncRingColor(document.body.dataset.product ?? "vigiles", true);
  });
  // If the style JSON never arrives (blocked network), the map still
  // projects pins correctly over the dark backdrop — say so plainly
  // instead of leaving a silent blank.
  setTimeout(() => {
    if (!state.mapLoaded && state.map) {
      els.mapNote.hidden = false;
      els.mapNote.textContent =
        "3D basemap style unreachable from this network — camera pins are plotted at their real locations without the basemap.";
    }
  }, 9000);
  updateZoomClass();
  return true;
}

// Extruded buildings from the style's own vector source. Heights
// are the tile data's values: the CARTO streets tiles carry height
// and min_height on the buildings layer (verified on a real Midtown
// tile, 2026-10-30: 254 of 288 buildings had height — the Empire
// State Building at 381 m). The coalesce fallback only covers
// footprints the data leaves unmeasured; footprints are always the
// data's own.
function addBuildings() {
  const map = state.map;
  if (!map || map.getLayer("cmd-buildings-3d")) return;
  const layers = map.getStyle()?.layers ?? [];
  const before = layers.find((layer) => layer.type === "symbol")?.id;
  map.addLayer(
    {
      id: "cmd-buildings-3d",
      type: "fill-extrusion",
      source: BUILDINGS_SOURCE,
      "source-layer": "buildings",
      minzoom: 13,
      paint: {
        "fill-extrusion-color": "#31435f",
        "fill-extrusion-height": ["coalesce", ["get", "height"], 10],
        "fill-extrusion-base": ["coalesce", ["get", "min_height"], 0],
        "fill-extrusion-opacity": 0.6,
        "fill-extrusion-vertical-gradient": true,
      },
    },
    before,
  );
  map.addLayer(
    {
      id: "cmd-buildings-edge",
      type: "line",
      source: BUILDINGS_SOURCE,
      "source-layer": "buildings",
      minzoom: 14,
      paint: { "line-color": "rgba(150, 190, 225, 0.32)", "line-width": 0.6 },
    },
    before,
  );
  map.on("click", "cmd-buildings-3d", onBuildingClick);
  map.on("mouseenter", "cmd-buildings-3d", () => {
    map.getCanvas().style.cursor = "pointer";
  });
  map.on("mouseleave", "cmd-buildings-3d", () => {
    map.getCanvas().style.cursor = "";
  });
}

// Building click: only what the tile data and this session actually
// know — the feature's name if the data carries one, its height if
// present, the nearest cameras computed from the loaded camera
// list, and any session incidents whose camera is nearby. Nothing
// is invented to fill the card.
function onBuildingClick(event) {
  const feature = event.features?.[0];
  if (!feature) return;
  const props = feature.properties ?? {};
  const point = { latitude: event.lngLat.lat, longitude: event.lngLat.lng };
  const box = document.createElement("div");
  box.className = "cmd-building-popup";
  const title = document.createElement("h4");
  title.textContent =
    typeof props.name === "string" && props.name.length > 0
      ? props.name
      : "Building — no name in map data";
  box.appendChild(title);
  if (typeof props.height === "number") {
    const height = document.createElement("p");
    height.className = "mono";
    height.textContent = `Height ${props.height} m — from map tile data`;
    box.appendChild(height);
  }
  const near = nearestCameras(state.cameras, point, 600, 3);
  const nearHead = document.createElement("p");
  nearHead.className = "cmd-building-head";
  nearHead.textContent = "Nearest cameras";
  box.appendChild(nearHead);
  if (near.length === 0) {
    const none = document.createElement("p");
    none.textContent = "No cameras within 600 m in the loaded list.";
    box.appendChild(none);
  }
  for (const { camera, distance } of near) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = `${camera.name} — ${Math.round(distance)} m`;
    btn.addEventListener("click", () => {
      state.popup?.remove();
      selectCamera(camera.id, { openCard: true });
    });
    box.appendChild(btn);
  }
  const nearbyIncidents = state.queue
    .list()
    .filter((incident) => {
      const cam = state.byId.get(incident.cameraId);
      return cam && distanceMeters(cam, point) <= 600;
    })
    .slice(0, 3);
  if (nearbyIncidents.length > 0) {
    const incHead = document.createElement("p");
    incHead.className = "cmd-building-head";
    incHead.textContent = "Session incidents near here";
    box.appendChild(incHead);
    for (const incident of nearbyIncidents) {
      const cam = state.byId.get(incident.cameraId);
      const line = document.createElement("p");
      line.textContent = `${cam?.name ?? incident.cameraId} — ${divisionShortName(incident.productId)} · ${incident.category} (${incident.priority})`;
      box.appendChild(line);
    }
  }
  state.popup?.remove();
  state.popup = new window.maplibregl.Popup({ closeOnClick: true, maxWidth: "300px" })
    .setLngLat(event.lngLat)
    .setDOMContent(box)
    .addTo(state.map);
}

// The selected camera gets a soft ground ring: a radius around its
// real location. The NYCTMC API publishes no camera heading, so the
// ring deliberately has NO direction — a viewing cone would be
// invented data.
function addSelectionRing() {
  const map = state.map;
  if (!map || map.getSource("cmd-selection")) return;
  map.addSource("cmd-selection", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });
  map.addLayer({
    id: "cmd-selection-fill",
    type: "fill",
    source: "cmd-selection",
    paint: { "fill-color": "#53c8ff", "fill-opacity": 0.13 },
  });
  map.addLayer({
    id: "cmd-selection-line",
    type: "line",
    source: "cmd-selection",
    paint: { "line-color": "#53c8ff", "line-width": 1.6 },
  });
}

function updateSelectionRing() {
  const src = state.map?.getSource("cmd-selection");
  if (!src) return;
  const cam = state.focusedId ? state.byId.get(state.focusedId) : null;
  if (!cam) {
    src.setData({ type: "FeatureCollection", features: [] });
    return;
  }
  src.setData({
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [circlePolygon(cam.latitude, cam.longitude, 120)],
    },
    properties: {},
  });
}

function syncRingColor(productId, force = false) {
  if (!state.map || (!force && state.ringProduct === productId)) return;
  if (!state.map.getLayer("cmd-selection-fill")) return;
  const color = PRODUCT_ACCENT_HEX[productId] ?? "#53c8ff";
  state.map.setPaintProperty("cmd-selection-fill", "fill-color", color);
  state.map.setPaintProperty("cmd-selection-line", "line-color", color);
  state.ringProduct = productId;
}

function renderPins() {
  if (state.map && window.maplibregl) {
    for (const cam of state.cameras) {
      const { el, span } = createMarkerElement(cam);
      const marker = new window.maplibregl.Marker({ element: el, anchor: "center" })
        .setLngLat([cam.longitude, cam.latitude])
        .addTo(state.map);
      state.markers.set(cam.id, { marker, span });
    }
    return;
  }
  // Schematic grid fallback: no 3D map — plot the dots on the
  // cameras' own lat/lng bounding box so the layout still reads.
  els.map.classList.add("cmd-map--grid");
  els.mapNote.hidden = false;
  els.mapNote.textContent =
    "Map library unavailable — schematic pin grid from camera coordinates.";
  if (state.cameras.length === 0) return;
  const lats = state.cameras.map((c) => c.latitude);
  const lngs = state.cameras.map((c) => c.longitude);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  for (const cam of state.cameras) {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = `cmd-grid-dot ${pinClassFor(cam.id)}`;
    dot.style.left = `${(((cam.longitude - minLng) / (maxLng - minLng || 1)) * 94 + 3).toFixed(2)}%`;
    dot.style.top = `${(((maxLat - cam.latitude) / (maxLat - minLat || 1)) * 92 + 4).toFixed(2)}%`;
    dot.title = `${cam.name} — ${cam.area}`;
    dot.setAttribute("aria-label", `View camera ${cam.name}, ${cam.area}`);
    dot.addEventListener("click", () => selectCamera(cam.id, { openCard: true }));
    els.map.appendChild(dot);
    state.gridDots.set(cam.id, dot);
  }
}

// ---------------------------------------------------------------- camera list rail

function rowStateClass(id) {
  const entry = state.camState.get(id);
  if (entry?.flagged) return "cmd-cam-row--flagged";
  if (id === state.focusedId) return "cmd-cam-row--focused";
  if (state.watch.has(id)) return "cmd-cam-row--watched";
  return "";
}

function renderList() {
  const filtered = filterCameras(state.cameras, state.query);
  const groups = groupCamerasByBorough(filtered);
  els.cameraList.textContent = "";
  let rendered = 0;
  const CAP = 150;
  for (const group of groups) {
    if (rendered >= CAP) break;
    const head = document.createElement("h4");
    head.className = "cmd-borough";
    head.textContent = `${group.area} · ${group.cameras.length}`;
    els.cameraList.appendChild(head);
    const ul = document.createElement("ul");
    ul.className = "cmd-cam-rows";
    for (const cam of group.cameras) {
      if (rendered >= CAP) break;
      rendered += 1;
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `cmd-cam-row ${rowStateClass(cam.id)}`;
      const dot = document.createElement("span");
      dot.className = `cmd-row-dot ${pinClassFor(cam.id)}`;
      const name = document.createElement("span");
      name.className = "cmd-row-name";
      name.textContent = cam.name;
      btn.append(dot, name);
      const entry = state.camState.get(cam.id);
      if (entry?.flagged) {
        const tag = document.createElement("span");
        tag.className = "cmd-row-tag cmd-row-tag--flagged";
        tag.textContent = "FLAGGED";
        btn.appendChild(tag);
      } else if (state.watch.has(cam.id)) {
        const tag = document.createElement("span");
        tag.className = "cmd-row-tag";
        tag.textContent = "WATCHING";
        btn.appendChild(tag);
      }
      btn.addEventListener("click", () => selectCamera(cam.id, { openCard: true }));
      li.appendChild(btn);
      ul.appendChild(li);
    }
    els.cameraList.appendChild(ul);
  }
  if (filtered.length > rendered) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = `Showing ${rendered} of ${filtered.length} matches — refine the filter to narrow the list.`;
    els.cameraList.appendChild(note);
  }
  if (filtered.length === 0) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = "No cameras match the filter.";
    els.cameraList.appendChild(note);
  }
}

// ---------------------------------------------------------------- readouts

function flaggedCount() {
  let n = 0;
  for (const entry of state.camState.values()) if (entry.flagged) n += 1;
  return n;
}

function renderReadouts() {
  els.countOnline.textContent = String(state.onlineCount || "–");
  els.countWatching.textContent = String(state.watch.size);
  els.countFlagged.textContent = String(flaggedCount());
}

// ---------------------------------------------------------------- selection + inspector

function selectCamera(id, { pan = false, openCard = false } = {}) {
  const cam = state.byId.get(id);
  if (!cam) return;
  const previous = state.focusedId;
  state.focusedId = id;
  els.inspName.textContent = cam.name;
  els.inspMeta.textContent = `${cam.area} · ${cam.latitude.toFixed(5)}, ${cam.longitude.toFixed(5)} · NYC DOT test feed`;
  els.viewerImg.hidden = false;
  els.viewerImg.src = cacheBust(cam.imageUrl);
  els.viewerUpdated.textContent = `Snapshot ${fmtTime(new Date())} — refreshes automatically`;
  els.watchToggle.disabled = false;
  els.assessNow.disabled = false;
  updateWatchButtons();
  renderAssessmentCard(id);
  renderStepper(id);
  if (previous && previous !== id) refreshPin(previous);
  refreshPin(id);
  renderList();
  updateSelectionRing();
  if (state.map && pan) {
    state.map.easeTo({ center: [cam.longitude, cam.latitude], duration: 600 });
  }
  if (openCard) openPinCard(id);
  else positionPinCard();
}

function updateWatchButtons() {
  const id = state.focusedId;
  const watched = id !== null && state.watch.has(id);
  els.watchToggle.textContent = watched ? "Stop watching" : "Watch this camera";
  if (id !== null) {
    const cam = state.byId.get(id);
    els.pinCardWatch.textContent = watched ? "Stop watching" : "Watch";
    if (cam) els.pinCardWatch.setAttribute("aria-label", `${watched ? "Stop watching" : "Watch"} ${cam.name}`);
  }
  els.sampleToggle.disabled = state.watch.size === 0 && !(state.sampler?.running ?? false);
}

function toggleWatch(id) {
  const cam = state.byId.get(id);
  if (!cam) return;
  const result = state.watch.toggle(id);
  if (!result.ok && result.reason === "full") {
    setStatus(`Watch list is full (max ${MAX_WATCHED}). Remove a camera to add another.`);
    return;
  }
  pushActivity(result.watched ? `Watching — ${cam.name}` : `Stopped watching — ${cam.name}`);
  if (!result.watched) {
    // Unwatching a flagged camera does not clear its flag history,
    // but sampling stops for it; the pin returns to idle/flagged per
    // its last result.
  }
  refreshPin(id);
  renderList();
  renderWall();
  renderReadouts();
  renderSystem();
  updateWatchButtons();
}

// ---------------------------------------------------------------- pin card (floating, Genetec style)

function openPinCard(id) {
  const cam = state.byId.get(id);
  if (!cam) return;
  els.pinCard.hidden = false;
  els.pinCardImg.src = cacheBust(cam.imageUrl);
  els.pinCardName.textContent = cam.name;
  els.pinCardMeta.textContent = `${cam.area} · NYC DOT test feed`;
  updatePinCardChip(id);
  updateWatchButtons();
  positionPinCard();
}

function updatePinCardChip(id) {
  if (els.pinCard.hidden || id !== state.focusedId) return;
  const entry = state.camState.get(id);
  // Division tag: the origin division of the camera's newest open
  // incident; failing that, the division of its latest assessment.
  const open = state.queue.openForCamera(id);
  const tagProduct = open?.productId ?? entry?.lastProduct ?? null;
  if (tagProduct) {
    els.pinCardDiv.hidden = false;
    els.pinCardDiv.className = `cmd-div-tag cmd-div-tag--${tagProduct}`;
    els.pinCardDiv.textContent = divisionShortName(tagProduct);
  } else {
    els.pinCardDiv.hidden = true;
  }
  if (open) {
    els.pinCardChip.textContent = `Flagged: ${open.category} — for human review`;
    els.pinCardChip.className = "cmd-chip cmd-chip--flagged";
    return;
  }
  if (!entry?.lastCategory) {
    els.pinCardChip.textContent = "Not assessed yet";
    els.pinCardChip.className = "cmd-chip";
    return;
  }
  els.pinCardChip.textContent = `Latest: ${entry.lastCategory}`;
  els.pinCardChip.className = "cmd-chip";
}

function positionPinCard() {
  if (els.pinCard.hidden || !state.focusedId) return;
  const cam = state.byId.get(state.focusedId);
  if (!cam) return;
  const rect = els.map.getBoundingClientRect();
  let x;
  let y;
  if (state.map) {
    const point = state.map.project([cam.longitude, cam.latitude]);
    x = point.x;
    y = point.y;
  } else {
    const dot = state.gridDots.get(cam.id);
    if (!dot) return;
    x = dot.offsetLeft + dot.offsetWidth / 2;
    y = dot.offsetTop;
  }
  const cardW = els.pinCard.offsetWidth || 264;
  const cardH = els.pinCard.offsetHeight || 300;
  const left = Math.min(Math.max(x - cardW / 2, 8), Math.max(rect.width - cardW - 8, 8));
  let top = y - cardH - 16;
  if (top < 96) top = y + 20; // keep clear of the floating top bar
  els.pinCard.style.left = `${left}px`;
  els.pinCard.style.top = `${top}px`;
}

// ---------------------------------------------------------------- assessment card + stepper

function renderAssessmentCard(id) {
  const entry = state.camState.get(id);
  const result = entry?.lastResult;
  if (!result) {
    els.assessment.hidden = true;
    els.assessment.textContent = "";
    return;
  }
  const a = result.assessment ?? {};
  els.assessment.hidden = false;
  els.assessment.textContent = "";
  // Origin division tag on the result itself: which of the three
  // divisions produced this assessment.
  if (entry.lastProduct) els.assessment.appendChild(makeDivisionTag(entry.lastProduct));
  const cat = document.createElement("p");
  cat.className = entry.lastFlagged ? "cmd-result-cat cmd-result-cat--flagged" : "cmd-result-cat";
  cat.textContent = a.category ?? "";
  const flagLine = document.createElement("p");
  flagLine.className = "note";
  flagLine.textContent = entry.lastFlagged
    ? `Flagged for human review — category outside the ${divisionShortName(entry.lastProduct)} baseline set.`
    : `Baseline category for ${divisionShortName(entry.lastProduct)} — this result raised no review flag.`;
  const summary = document.createElement("p");
  summary.textContent = a.summary ?? "";
  els.assessment.append(cat, flagLine, summary);
  if (Array.isArray(a.uncertainty) && a.uncertainty.length > 0) {
    const ul = document.createElement("ul");
    ul.className = "cmd-uncertainty";
    for (const line of a.uncertainty) {
      const li = document.createElement("li");
      li.textContent = line;
      ul.appendChild(li);
    }
    els.assessment.appendChild(ul);
  }
  const meta = document.createElement("p");
  meta.className = "note mono";
  const productName = PRODUCT_BY_ID[entry.lastProduct]?.name ?? entry.lastProduct ?? "";
  meta.textContent = `${productName} · ${fmtTime(entry.lastAt)} · ${result.processing?.model ?? ""}`;
  els.assessment.appendChild(meta);
}

const STEP_DEFS = [
  ["detected", "Detected"],
  ["investigating", "Investigating"],
  ["analyzed", "Analyzed"],
  ["awaiting-review", "Awaiting human review"],
  ["reviewed", "Reviewed"],
];

function renderStepper(id) {
  const entry = state.camState.get(id);
  const phase = entry?.phase ?? "none";
  const doneThrough =
    phase === "sampling" ? -1
    : phase === "inflight" ? 0
    : phase === "awaiting-review" ? 2
    : phase === "reviewed" ? 4
    : -1;
  const currentIdx =
    phase === "sampling" ? 0
    : phase === "inflight" ? 1
    : phase === "awaiting-review" ? 3
    : -1;
  els.stepper.textContent = "";
  STEP_DEFS.forEach(([key, label], idx) => {
    const li = document.createElement("li");
    li.className =
      idx <= doneThrough ? "cmd-step cmd-step--done"
      : idx === currentIdx ? "cmd-step cmd-step--current"
      : "cmd-step";
    const dotEl = document.createElement("span");
    dotEl.className = "cmd-step-dot";
    const text = document.createElement("span");
    text.textContent = label;
    li.append(dotEl, text);
    els.stepper.appendChild(li);
  });
  els.markReviewed.disabled = phase !== "awaiting-review";
  if (!entry || phase === "none") {
    els.stepperNote.textContent =
      "Not sampled yet. Watch this camera and run sampling, or choose “Assess this frame now”.";
  } else if (phase === "awaiting-review") {
    els.stepperNote.textContent =
      "The latest assessment is recorded in the session log and counts in the review queue. Mark it reviewed here once a human has looked at it.";
  } else if (phase === "reviewed") {
    els.stepperNote.textContent = "Marked reviewed by the operator in this session.";
  } else if (entry.errorNote) {
    els.stepperNote.textContent = entry.errorNote;
  } else {
    els.stepperNote.textContent = "";
  }
}

// ---------------------------------------------------------------- sampling pipeline

function loadImage(src, cors) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    if (cors) img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("image failed to load"));
    img.src = src;
  });
}

async function captureSnapshot(cam) {
  const url = cacheBust(cam.imageUrl);
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    try {
      const img = await loadImage(objUrl, false);
      return downscaleImageToDataURL(img, els.captureCanvas);
    } finally {
      URL.revokeObjectURL(objUrl);
    }
  } catch {
    try {
      const img = await loadImage(url, true);
      return downscaleImageToDataURL(img, els.captureCanvas);
    } catch {
      throw new Error("snapshot unavailable from this network (fetch and CORS image load both failed)");
    }
  }
}

function setPhase(id, phase, errorNote = null) {
  const entry =
    state.camState.get(id) ?? { flagged: false, flagByProduct: {}, phase: "none", reviewed: false };
  entry.phase = phase;
  entry.errorNote = errorNote;
  state.camState.set(id, entry);
  if (id === state.focusedId) renderStepper(id);
}

async function assessCamera(id) {
  const cam = state.byId.get(id);
  if (!cam) return false;
  if (id !== state.focusedId) selectCamera(id, {});
  state.counters.samples += 1;
  setPhase(id, "sampling");
  setStatus(`Sampling ${cam.name} — capturing a snapshot…`);
  renderSystem();
  let dataUrl;
  try {
    dataUrl = await captureSnapshot(cam);
  } catch (err) {
    state.counters.errors += 1;
    setPhase(id, "none", `Snapshot failed: ${err.message}`);
    setStatus(`Snapshot failed for ${cam.name}: ${err.message}`);
    pushActivity(`Feed error — ${cam.name}: snapshot capture failed`);
    renderSystem();
    return false;
  }
  const bridge = await getBridge();
  if (!bridge) {
    state.counters.errors += 1;
    setPhase(id, "none", "Assessment bridge unavailable — the console app did not load.");
    setStatus("Assessment bridge unavailable — the console app did not load.");
    renderSystem();
    return false;
  }
  setPhase(id, "inflight");
  const product = bridge.currentProductId();
  const timestamp = new Date().toISOString();
  let result;
  try {
    result = await bridge.submitAssessment(
      product,
      timestamp,
      dataUrl,
      `${cam.name} — NYC DOT public traffic camera (test feed)`,
      "live-test-feed",
    );
  } catch (err) {
    state.counters.errors += 1;
    setPhase(id, "none", `Assessment failed: ${err.message}`);
    setStatus(`Assessment failed for ${cam.name}: ${err.message}`);
    pushActivity(`Assessment failed — ${cam.name}`);
    renderSystem();
    return false;
  }
  state.counters.assessed += 1;
  state.lastModel = result?.processing?.model ?? null;
  state.lastLatencyMs =
    typeof result?.processing?.latency_ms === "number" ? result.processing.latency_ms : null;
  const category = result?.assessment?.category ?? "";
  const prev = state.camState.get(id) ?? { flagged: false, flagByProduct: {} };
  // Per-division flag state: the edge is computed against THIS
  // division's previous flag on the camera, never the camera-wide
  // one. A baseline result under Medicus must not clear a flag
  // Vigiles raised, and the camera stays flagged while ANY
  // division's flag stands (one system, three divisions).
  const prevDivFlagged = prev.flagByProduct?.[product] ?? false;
  const { flagged } = applyAssessmentToFlag(prevDivFlagged, product, category);
  const flagByProduct = { ...(prev.flagByProduct ?? {}), [product]: flagged };
  state.camState.set(id, {
    flagged: Object.values(flagByProduct).some(Boolean),
    flagByProduct,
    lastCategory: category,
    lastProduct: product,
    lastFlagged: flagged,
    lastAt: result?.timestamp ?? timestamp,
    lastResult: result,
    phase: "awaiting-review",
    reviewed: false,
    errorNote: null,
  });
  if (flagged) {
    const { incident, created } = state.queue.add({
      cameraId: id,
      productId: product,
      category,
      timestamp: result?.timestamp ?? timestamp,
      thumbnail: cam.imageUrl,
    });
    if (created && incident) {
      pushActivity(
        `Flag raised — ${divisionShortName(product)} · ${cam.name} — ${category} (${incident.priority})`,
      );
    }
  } else if (prevDivFlagged) {
    state.queue.clearForCamera(id, product);
    pushActivity(
      `Flag cleared — ${divisionShortName(product)} · ${cam.name} — baseline result (${category})`,
    );
  }
  setStatus(
    flagged
      ? `Assessed ${cam.name} — ${category}. Flagged for human review.`
      : `Assessed ${cam.name} — ${category}.`,
  );
  renderAssessmentCard(id);
  renderStepper(id);
  refreshPin(id);
  renderAlerts();
  renderList();
  renderReadouts();
  renderSystem();
  updatePinCardChip(id);
  return true;
}

function readIntervalMs() {
  const input = $("interval-seconds");
  const seconds = Number(input?.value);
  const clamped = Number.isFinite(seconds) ? Math.min(60, Math.max(1, seconds)) : 3;
  return Math.round(clamped * 1000);
}

function ensureSampler() {
  if (state.sampler) return state.sampler;
  state.sampler = new FrameSampler({
    intervalMs: readIntervalMs(),
    onSample: async () => {
      const id = nextWatchedId(state.watch.list(), state.lastSampledId);
      if (id === null) return;
      state.lastSampledId = id;
      await assessCamera(id);
    },
    onError: (err) => {
      state.counters.errors += 1;
      pushActivity(`Sampler error — ${err.message}`);
      renderSystem();
    },
  });
  return state.sampler;
}

function toggleSampling() {
  const sampler = ensureSampler();
  if (sampler.running) {
    sampler.stop();
    els.sampleToggle.textContent = "Start watch sampling";
    setStatus("Watch sampling stopped.");
  } else {
    if (state.watch.size === 0) {
      setStatus("Add at least one camera to the watch list first — only watched cameras are sampled.");
      return;
    }
    sampler.setIntervalMs(readIntervalMs());
    sampler.start();
    els.sampleToggle.textContent = "Stop watch sampling";
    setStatus(
      `Watch sampling running — one watched camera every ${Math.round(readIntervalMs() / 1000)}s, round-robin.`,
    );
  }
  updateWatchButtons();
  renderSystem();
}

// ---------------------------------------------------------------- incident queue UI

function renderAlerts() {
  const items = state.queue.list();
  els.alerts.textContent = "";
  els.alertsEmpty.hidden = items.length > 0;
  for (const incident of items.slice(0, 30)) {
    const cam = state.byId.get(incident.cameraId);
    if (!cam) continue;
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = [
      "cmd-alert",
      `cmd-alert--${incident.priority}`,
      incident.seen ? "cmd-alert--seen" : "",
      incident.cleared ? "cmd-alert--cleared" : "",
    ]
      .filter(Boolean)
      .join(" ");
    const thumb = document.createElement("img");
    thumb.className = "cmd-alert-thumb";
    thumb.alt = "";
    thumb.loading = "lazy";
    thumb.src = incident.thumbnail ?? cam.imageUrl;
    const body = document.createElement("span");
    body.className = "cmd-alert-body";
    const title = document.createElement("span");
    title.className = "cmd-alert-title";
    title.textContent = cam.name;
    // Origin division tag: the incident belongs to the one system
    // queue, the tag records which division raised it.
    const divTag = makeDivisionTag(incident.productId);
    const detail = document.createElement("span");
    detail.className = "cmd-alert-detail";
    detail.textContent = `${cam.area} · ${incident.category}`;
    const meta = document.createElement("span");
    meta.className = "cmd-alert-meta mono";
    const stateTag = incident.cleared ? "CLEARED" : incident.seen ? "SEEN" : "UNSEEN";
    meta.textContent = `${incident.priority.toUpperCase()} · ${fmtTime(incident.timestamp)} · ${stateTag}`;
    body.append(title, divTag, detail, meta);
    btn.append(thumb, body);
    btn.addEventListener("click", () => {
      state.queue.markSeen(incident.id);
      selectCamera(incident.cameraId, { pan: true, openCard: true });
      renderAlerts();
      refreshPin(incident.cameraId);
    });
    li.appendChild(btn);
    els.alerts.appendChild(li);
  }
  if (items.length > 30) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = `Showing the 30 most recent of ${items.length} queue entries.`;
    els.alerts.appendChild(note);
  }
}

// ---------------------------------------------------------------- camera wall

function renderWall() {
  els.wall.textContent = "";
  state.wallTiles = [];
  const addTile = ({ base, name, sub, cameraId }) => {
    const tile = document.createElement(cameraId ? "button" : "figure");
    if (cameraId) tile.type = "button";
    tile.className = "cmd-tile";
    const img = document.createElement("img");
    img.alt = cameraId ? `Live snapshot — ${name}` : `Live snapshot — ${name} (Los Angeles test feed)`;
    img.loading = "lazy";
    img.src = cacheBust(base);
    const caption = document.createElement("figcaption");
    const nameEl = document.createElement("span");
    nameEl.className = "cmd-tile-name";
    nameEl.textContent = name;
    const subEl = document.createElement("span");
    subEl.className = "cmd-tile-sub mono";
    subEl.textContent = sub;
    caption.append(nameEl, subEl);
    tile.append(img, caption);
    if (cameraId) {
      tile.addEventListener("click", () => selectCamera(cameraId, { openCard: true }));
    }
    els.wall.appendChild(tile);
    state.wallTiles.push({ img, base, subEl, sub });
  };
  for (const id of state.watch.list()) {
    const cam = state.byId.get(id);
    if (cam) addTile({ base: cam.imageUrl, name: cam.name, sub: `${cam.area} · watched`, cameraId: id });
  }
  if (state.watch.size === 0) {
    const empty = document.createElement("p");
    empty.className = "note cmd-wall-empty";
    empty.textContent = "No watched cameras yet — select a camera and choose Watch.";
    els.wall.appendChild(empty);
  }
  for (const feed of WALL_FEEDS) {
    addTile({ base: feed.imageUrl, name: feed.name, sub: feed.area, cameraId: null });
  }
}

function refreshWallSrcs() {
  const now = fmtTime(new Date());
  for (const tile of state.wallTiles) {
    tile.img.src = cacheBust(tile.base);
    tile.subEl.textContent = `${tile.sub} · ${now}`;
  }
  if (state.focusedId) {
    const cam = state.byId.get(state.focusedId);
    if (cam) {
      els.viewerImg.src = cacheBust(cam.imageUrl);
      els.viewerUpdated.textContent = `Snapshot ${now} — refreshes automatically`;
      if (!els.pinCard.hidden) els.pinCardImg.src = cacheBust(cam.imageUrl);
    }
  }
}

// ---------------------------------------------------------------- system readouts

function renderSystem() {
  const backend = $("backend-status");
  if (backend) {
    els.sysBackend.textContent = backend.textContent || "—";
    els.sysBackend.dataset.state = backend.dataset.state ?? "";
  }
  const bridge = state.bridge ?? window.MetaTrioCommand ?? null;
  els.sysEndpoint.textContent = bridge ? bridge.currentEndpoint() : "/api/assess";
  const productId = bridge ? bridge.currentProductId() : (document.body.dataset.product ?? "vigiles");
  els.sysProduct.textContent = PRODUCT_BY_ID[productId]?.name ?? productId;
  syncRingColor(productId);
  document.querySelectorAll("[data-cmd-product]").forEach((chip) => {
    chip.setAttribute("aria-pressed", String(chip.dataset.cmdProduct === productId));
  });
  const sampler = state.sampler;
  els.sysSampler.textContent = sampler?.running
    ? `Running — every ${Math.round(readIntervalMs() / 1000)}s · ${state.counters.samples} sent`
    : "Stopped";
  els.sysModel.textContent = state.lastModel ?? "—";
  els.sysLatency.textContent =
    state.lastLatencyMs !== null ? `${state.lastLatencyMs} ms (last result)` : "—";
  const logStats = $("log-stats");
  const match = /Session log entries:\s*(\d+)/.exec(logStats?.textContent ?? "");
  els.sysLog.textContent = match ? match[1] : "—";
  els.sysWatched.textContent = `${state.watch.size} / ${MAX_WATCHED}`;
  els.barWatched.style.width = `${(state.watch.size / MAX_WATCHED) * 100}%`;
  const flagged = flaggedCount();
  els.sysFlagged.textContent = `${flagged} of ${state.watch.size} watched`;
  els.barFlagged.style.width =
    state.watch.size > 0 ? `${(flagged / state.watch.size) * 100}%` : "0%";
  els.sysSamples.textContent = String(state.counters.samples);
  els.sysErrors.textContent = String(state.counters.errors);
}

// ---------------------------------------------------------------- activity strip

function historyEvents() {
  const items = [];
  document.querySelectorAll("#history-list .history-head").forEach((head) => {
    const text = head.textContent.trim().replace(/\s+/g, " ");
    if (text) items.push(text);
  });
  return items.slice(0, 6);
}

function renderActivity() {
  const commandTexts = state.activity.map((e) => `${fmtTime(e.at)} — ${e.text}`);
  const items = [...commandTexts, ...historyEvents()];
  if (items.length === 0) {
    els.activityText.textContent = "No session events yet.";
    els.activityCount.textContent = "";
    return;
  }
  const idx = state.activityIdx % items.length;
  els.activityText.textContent = items[idx];
  els.activityCount.textContent = `${idx + 1} / ${items.length}`;
}

// ---------------------------------------------------------------- loop feed (agent crew)

// The agent crew (patrol -> review -> investigation -> records ->
// response; docs/AGENT_CREW.md) works server-side on the queue and
// writes its own records; this panel is a read-only window onto
// them via GET /api/crew/status. When the endpoint does not answer
// (crew not running on this stack, or the page is hosted without
// the app server), the panel says so and keeps polling — it never
// invents crew activity.
async function refreshLoopFeed() {
  let payload;
  try {
    const res = await fetch("/api/crew/status", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    payload = await res.json();
  } catch {
    els.loopStatus.textContent = loopStatusText({ unreachable: true });
    return;
  }
  els.loopStatus.textContent = loopStatusText(payload);
  const items = loopFeedItems(payload, 12);
  els.loopFeed.textContent = "";
  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "note";
    li.textContent = "No crew events recorded yet.";
    els.loopFeed.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.className = `cmd-loop-item cmd-loop-item--${item.type}`;
    const when = document.createElement("span");
    when.className = "cmd-loop-when mono";
    when.textContent = item.at ? fmtTime(new Date(item.at)) : "";
    const text = document.createElement("span");
    text.textContent = item.text;
    li.append(when, text);
    els.loopFeed.appendChild(li);
  }
}

// ---------------------------------------------------------------- Ctrl+K search

function renderKResults() {
  const q = els.ksearch.value;
  els.kresults.textContent = "";
  const addItem = (label, sub, action) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cmd-kresult";
    const main = document.createElement("span");
    main.textContent = label;
    const meta = document.createElement("span");
    meta.className = "cmd-kresult-sub mono";
    meta.textContent = sub;
    btn.append(main, meta);
    btn.addEventListener("click", () => {
      closeSearch();
      action();
    });
    li.appendChild(btn);
    els.kresults.appendChild(li);
    return btn;
  };
  const firstActions = [];
  for (const cam of filterCameras(state.cameras, q).slice(0, 8)) {
    const btn = addItem(cam.name, `Camera · ${cam.area}`, () =>
      selectCamera(cam.id, { pan: true, openCard: true }),
    );
    firstActions.push(() => btn.click());
  }
  const qLower = q.trim().toLowerCase();
  for (const incident of state.queue.list()) {
    const cam = state.byId.get(incident.cameraId);
    if (!cam) continue;
    if (
      qLower &&
      !cam.name.toLowerCase().includes(qLower) &&
      !incident.category.toLowerCase().includes(qLower) &&
      !cam.area.toLowerCase().includes(qLower)
    ) {
      continue;
    }
    const btn = addItem(
      `${cam.name} — ${incident.category}`,
      `Incident · ${divisionShortName(incident.productId)} · ${incident.priority.toUpperCase()} · ${fmtTime(incident.timestamp)}`,
      () => {
        state.queue.markSeen(incident.id);
        selectCamera(incident.cameraId, { pan: true, openCard: true });
        renderAlerts();
        refreshPin(incident.cameraId);
      },
    );
    firstActions.push(() => btn.click());
    if (firstActions.length >= 13) break;
  }
  if (firstActions.length === 0) {
    const li = document.createElement("li");
    li.className = "note";
    li.textContent = "No cameras or incidents match.";
    els.kresults.appendChild(li);
  }
  els.kresults._firstAction = firstActions[0] ?? null;
}

function openSearch() {
  els.overlay.hidden = false;
  els.ksearch.value = "";
  renderKResults();
  els.ksearch.focus();
}

function closeSearch() {
  els.overlay.hidden = true;
}

// ---------------------------------------------------------------- map modes + AI focus

// The newest still-flagged camera: the open incident queue first
// (newest first), then any flagged camera state by latest result.
function newestFlaggedCamera() {
  for (const incident of state.queue.list()) {
    if (!incident.open) continue;
    if (state.camState.get(incident.cameraId)?.flagged) {
      return state.byId.get(incident.cameraId) ?? null;
    }
  }
  let bestId = null;
  let bestAt = "";
  for (const [id, entry] of state.camState) {
    if (entry.flagged && (entry.lastAt ?? "") > bestAt) {
      bestId = id;
      bestAt = entry.lastAt ?? "";
    }
  }
  return bestId ? (state.byId.get(bestId) ?? null) : null;
}

// Modes are camera presets + emphasis only — they move the 3D
// camera, nothing else. They never invent targets: Incident mode
// flies only when a real flagged incident exists.
function setMode(mode, { fly = true } = {}) {
  state.mode = mode;
  document.querySelectorAll("[data-cmd-mode]").forEach((btn) => {
    btn.setAttribute("aria-pressed", String(btn.dataset.cmdMode === mode));
  });
  if (!fly) return;
  if (!state.map) {
    setStatus("The 3D map is unavailable in this browser — mode presets are disabled.");
    return;
  }
  if (mode === "city") {
    state.map.flyTo({ center: NYC_CENTER, zoom: 10.9, pitch: 40, bearing: 0, duration: 1600 });
  } else if (mode === "tactical") {
    const cam = state.focusedId ? state.byId.get(state.focusedId) : null;
    state.map.flyTo({
      center: cam ? [cam.longitude, cam.latitude] : MANHATTAN_CENTER,
      zoom: 15.5,
      pitch: 60,
      duration: 1600,
    });
  } else if (mode === "incident") {
    const cam = newestFlaggedCamera();
    if (!cam) {
      setStatus("No flagged incidents right now — Incident mode has nowhere to fly.");
      return;
    }
    state.map.flyTo({
      center: [cam.longitude, cam.latitude],
      zoom: 16.5,
      pitch: 65,
      duration: 1800,
    });
  }
}

// AI Focus: fly to the newest flagged incident, select it, and open
// its inspector + pin card. With no flags it says so — it never
// picks a camera at random.
function aiFocus() {
  const cam = newestFlaggedCamera();
  if (!cam) {
    setStatus(
      "AI Focus: no flagged incidents in this session yet. When an assessment flags a camera, AI Focus flies to the newest one.",
    );
    return;
  }
  selectCamera(cam.id, { openCard: true });
  setMode("incident", { fly: false });
  if (state.map) {
    state.map.flyTo({
      center: [cam.longitude, cam.latitude],
      zoom: 16.5,
      pitch: 65,
      duration: 1800,
    });
  }
  pushActivity(`AI Focus — flew to newest flag: ${cam.name}`);
}

// ---------------------------------------------------------------- view switch

function setView(view) {
  document.body.dataset.view = view;
  $("btn-view-command")?.setAttribute("aria-pressed", String(view === "command"));
  $("btn-view-console")?.setAttribute("aria-pressed", String(view === "console"));
  if (view === "command" && state.map) {
    setTimeout(() => state.map.resize(), 60);
  }
}

// ---------------------------------------------------------------- init

function init() {
  setView("command");
  initMap();
  void loadCameras();
  renderWall();
  renderAlerts();
  renderReadouts();
  renderSystem();
  renderActivity();
  void getBridge().then(() => renderSystem());

  els.search.addEventListener("input", () => {
    state.query = els.search.value;
    renderList();
  });
  els.watchToggle.addEventListener("click", () => {
    if (state.focusedId) toggleWatch(state.focusedId);
  });
  els.pinCardWatch.addEventListener("click", () => {
    if (state.focusedId) toggleWatch(state.focusedId);
  });
  els.pinCardFocus.addEventListener("click", () => {
    const cam = state.byId.get(state.focusedId ?? "");
    if (!cam) return;
    if (state.map) {
      state.map.flyTo({
        center: [cam.longitude, cam.latitude],
        zoom: Math.max(state.map.getZoom(), 14.5),
        pitch: 55,
        duration: 1200,
      });
    }
    positionPinCard();
  });
  els.pinCardClose.addEventListener("click", () => {
    els.pinCard.hidden = true;
  });
  els.assessNow.addEventListener("click", () => {
    if (state.focusedId) void assessCamera(state.focusedId);
  });
  els.sampleToggle.addEventListener("click", toggleSampling);
  els.markReviewed.addEventListener("click", () => {
    const id = state.focusedId;
    if (!id) return;
    const entry = state.camState.get(id);
    if (!entry || entry.phase !== "awaiting-review") return;
    entry.phase = "reviewed";
    entry.reviewed = true;
    // Reviewing marks seen the open incident OF THE DIVISION whose
    // result was reviewed — another division's incident on the same
    // camera stays unseen and keeps its pulse.
    const open = state.queue.openForCamera(id, entry.lastProduct);
    if (open) state.queue.markSeen(open.id);
    const cam = state.byId.get(id);
    pushActivity(`Marked reviewed — ${cam?.name ?? id}`);
    renderStepper(id);
    renderAlerts();
    refreshPin(id);
  });
  const intervalInput = $("interval-seconds");
  intervalInput?.addEventListener("change", () => {
    if (state.sampler?.running) state.sampler.setIntervalMs(readIntervalMs());
    renderSystem();
  });
  document.querySelectorAll("[data-cmd-product]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const radio = document.querySelector(`input[name="product"][value="${chip.dataset.cmdProduct}"]`);
      radio?.click();
      renderSystem();
    });
  });
  $("btn-view-command")?.addEventListener("click", () => setView("command"));
  $("btn-view-console")?.addEventListener("click", () => setView("console"));
  document.querySelectorAll("[data-cmd-mode]").forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.cmdMode));
  });
  els.aiFocus.addEventListener("click", aiFocus);

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (els.overlay.hidden) openSearch();
      else closeSearch();
    } else if (event.key === "Escape" && !els.overlay.hidden) {
      closeSearch();
    }
  });
  els.ksearch.addEventListener("input", renderKResults);
  els.ksearch.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const first = els.kresults._firstAction;
      if (first) first();
    }
  });
  els.overlay.addEventListener("click", (event) => {
    if (event.target === els.overlay) closeSearch();
  });

  setInterval(refreshWallSrcs, 15000);
  refreshLoopFeed();
  setInterval(refreshLoopFeed, 5000);
  setInterval(() => {
    renderSystem();
    const items = state.activity.length + historyEvents().length;
    if (items > 0) {
      state.activityIdx = (state.activityIdx + 1) % Math.max(items, 1);
      renderActivity();
    }
  }, 4000);
  window.addEventListener("resize", positionPinCard);
}

init();
