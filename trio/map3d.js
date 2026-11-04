// trio/map3d.js — the pitched city map the three division apps share.
//
// Why this file exists: the command console (imperium/index.html) draws a
// MapLibre map at pitch 40 over the shipped borough basemap, and that is the
// map people recognise as "the map". When the console was split into Vigiles,
// Ignis and Medicus, the divisions kept only the flat canvas map in core.js,
// so the three apps showed a level grid and no city. This module is the same
// MapLibre map, mounting into the page's own <canvas id="map"> slot and
// speaking the exact interface the flat map has (`set`, `focus`, `draw`,
// `state`, `onSelect`), so a page can swap one for the other without knowing
// which it got.
//
// Offline contract: the style is built here from the shipped borough GeoJSON
// (/vendor/geo/nyc-boroughs.geojson) and not fetched from a CDN, so the map
// paints on a machine with no network. Cameras are GeoJSON circle layers
// rather than DOM markers: the roster is 975 cameras on a live list, and 975
// DOM nodes at 60fps is a stutter, not a map.
//
// Container: MapLibre needs a <div> to append its own canvas to. The pages
// hand it a <canvas> (that is the flat map's slot), so this module inserts a
// positioned host div over that canvas and hides it. Overlays that follow the
// canvas in the DOM (legend, mode buttons) keep painting on top.
//
// Returns null when MapLibre or WebGL is unavailable — the caller falls back
// to the canvas map rather than showing an empty rectangle.

// The frame is chosen so the city fills the panel and the tilt reads: at the
// console's old zoom 10.6 over a whole borough the land was a wide dark shape
// with no street detail, and a pitched map of nothing looks like a flat map.
// Over Manhattan, not over the harbour: the old centre sat on Brooklyn Heights,
// so the middle of the frame was water and the city sat in one corner.
const DEFAULT_CENTER = { lat: 40.742, lon: -73.977 };
const DEFAULT_ZOOM = 12.1;
// Tilted on purpose: a level map reads as a diagram, a pitched one reads as a
// place. 55 is steep enough that the street grid converges on screen, which is
// what makes the three dimensions visible without any building data.
const PITCH = 55;
const BEARING = -22;

// The same basemap the old command console drew (dark matter). It needs the
// network for its vector tiles, so the shipped borough outline below stays as
// the offline fallback: a division on a machine with no route out of the VM
// still gets a map, just a coarser one.
const REMOTE_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
// Medicus is a paper sheet, so its basemap is the light one. A dark city under
// a cream page reads as a bug, the same reason the offline style has palettes.
const REMOTE_STYLE_LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";
// Long enough for a slow tile server, short enough that the fallback is not a
// blank rectangle in front of a judge.
const REMOTE_STYLE_TIMEOUT_MS = 4000;

// Two palettes, because the three divisions are not one theme: Vigiles and
// Ignis are dark consoles, Medicus is a paper sheet. A dark basemap dropped
// into the cream page reads as a bug, not as a map.
const PALETTES = {
  dark: { bg: "#060a12", land: "#0b1422", coast: "#22344e" },
  light: { bg: "#eeeadd", land: "#e4dfd0", coast: "#c4bca6" },
};

const CAM_SOURCE = "meta-cams";
const HOT_SOURCE = "meta-hotspots";

function buildStyle({ palette, geojsonUrl }) {
  const p = PALETTES[palette] || PALETTES.dark;
  return {
    version: 8,
    name: "Meta OS basemap",
    sources: {
      boroughs: {
        type: "geojson",
        data: geojsonUrl || "/vendor/geo/nyc-boroughs.geojson",
      },
    },
    layers: [
      { id: "ink", type: "background", paint: { "background-color": p.bg } },
      {
        id: "land",
        type: "fill",
        source: "boroughs",
        paint: { "fill-color": p.land, "fill-opacity": 1 },
      },
      {
        id: "coast",
        type: "line",
        source: "boroughs",
        paint: { "line-color": p.coast, "line-width": 1.2 },
      },
    ],
  };
}

function cameraFeatures(cameras, results, watch, selected) {
  const features = [];
  for (const cam of cameras || []) {
    if (!Number.isFinite(cam.latitude) || !Number.isFinite(cam.longitude)) continue;
    const result = results && results.get ? results.get(cam.id) : null;
    const flagged = !!(result && result.flagged);
    const watched = !!(watch && watch.has && watch.has(cam.id));
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [cam.longitude, cam.latitude] },
      properties: {
        id: cam.id,
        name: cam.name || "",
        flagged: flagged ? 1 : 0,
        watched: watched ? 1 : 0,
        selected: selected && cam.id === selected ? 1 : 0,
      },
    });
  }
  return { type: "FeatureCollection", features };
}

function hotspotFeatures(hotspots) {
  const features = [];
  for (const h of hotspots || []) {
    if (!Number.isFinite(h.lat) || !Number.isFinite(h.lon)) continue;
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [h.lon, h.lat] },
      properties: { frp: h.frp ?? 0 },
    });
  }
  return { type: "FeatureCollection", features };
}

export function Map3D(canvas, opts = {}) {
  const gl = window.maplibregl;
  if (!gl || !canvas) return null;

  // A machine without WebGL (a VM with a half-built GL stack) makes the
  // MapLibre constructor throw. Catch it here, not three frames later.
  const probe = document.createElement("canvas");
  const hasGL =
    !!(probe.getContext("webgl2") || probe.getContext("webgl") || probe.getContext("experimental-webgl"));
  if (!hasGL) return null;

  const state = {
    cameras: [],
    results: new Map(),
    watch: new Set(),
    hotspots: [],
    selected: null,
    accent: opts.accent || "#4F7EC2",
    onSelect: opts.onSelect || (() => {}),
    ready: false,
  };

  // The flat map's slot is a <canvas>; MapLibre wants a container element it
  // can append its own canvas to, and a canvas inside a canvas never paints.
  const parent = canvas.parentElement;
  if (!parent) return null;
  if (getComputedStyle(parent).position === "static") parent.style.position = "relative";
  const host = document.createElement("div");
  host.className = "map3d-host";
  host.setAttribute("aria-hidden", "true");
  // First child, z-index 0: the header strip, legend and mode buttons that
  // follow it in the DOM still paint above the map, as they did over the
  // canvas. The canvas itself stays in place (hidden) so the page's layout
  // rules still size the slot.
  host.style.cssText = "position:absolute;inset:0;z-index:0;overflow:hidden;";
  parent.insertBefore(host, parent.firstChild);
  canvas.style.visibility = "hidden";

  // Online: the street basemap. Offline (or if that style cannot be fetched):
  // the borough outline shipped with the app. `navigator.onLine` is a hint,
  // not a promise, which is why the fallback also has a timer.
  const offlineStyle = buildStyle(opts);
  const online = navigator.onLine !== false;
  const remoteStyle = opts.style || (opts.palette === "light" ? REMOTE_STYLE_LIGHT : REMOTE_STYLE);
  const startRemote = !opts.style && online;
  let usingRemote = startRemote;
  let fellBack = false;

  let map;
  try {
    map = new gl.Map({
      container: host,
      style: startRemote ? remoteStyle : offlineStyle,
      center: [opts.center?.lon ?? DEFAULT_CENTER.lon, opts.center?.lat ?? DEFAULT_CENTER.lat],
      zoom: opts.zoom ?? DEFAULT_ZOOM,
      pitch: opts.pitch ?? PITCH,
      bearing: opts.bearing ?? BEARING,
      maxPitch: 70,
      antialias: true,
      // The remote style carries its own OpenStreetMap/CARTO credit; the
      // offline style ships in this tree, so it needs none.
      attributionControl: startRemote ? { compact: true } : false,
    });
  } catch (err) {
    console.warn("trio: 3D map unavailable", err);
    host.remove();
    canvas.style.visibility = "";
    return null;
  }
  host.style.cursor = "grab";

  map.addControl(new gl.NavigationControl({ visualizePitch: true, showCompass: true }), "bottom-right");

  // ---- data plumbing -----------------------------------------------------
  let pending = null; // a set() that landed before the style was ready

  function push() {
    if (!state.ready) return;
    const camData = cameraFeatures(state.cameras, state.results, state.watch, state.selected);
    const src = map.getSource(CAM_SOURCE);
    if (src) src.setData(camData);
    const hotSrc = map.getSource(HOT_SOURCE);
    if (hotSrc) hotSrc.setData(hotspotFeatures(state.hotspots));
  }

  function installLayers() {
    if (!map.getSource(CAM_SOURCE)) {
      map.addSource(CAM_SOURCE, {
        type: "geojson",
        data: cameraFeatures(state.cameras, state.results, state.watch, state.selected),
      });
    }
    if (!map.getSource(HOT_SOURCE)) {
      map.addSource(HOT_SOURCE, { type: "geojson", data: hotspotFeatures(state.hotspots) });
    }

    // Fire hotspots: context under the cameras, never instead of them.
    if (!map.getLayer("meta-hotspots-ring")) {
      map.addLayer({
        id: "meta-hotspots-ring",
        type: "circle",
        source: HOT_SOURCE,
        paint: {
          "circle-radius": 10,
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-width": 1,
          "circle-stroke-color": "rgba(224, 102, 47, 0.45)",
        },
      });
      map.addLayer({
        id: "meta-hotspots-dot",
        type: "circle",
        source: HOT_SOURCE,
        paint: { "circle-radius": 3, "circle-color": "rgba(224, 102, 47, 0.85)" },
      });
    }

    if (!map.getLayer("meta-cams-halo")) {
      // Three passes, weakest first: a plain camera, a watched one, a flagged
      // one. Draw order is the layer order, so the important dot is never
      // painted over by its neighbours.
      map.addLayer({
        id: "meta-cams-halo",
        type: "circle",
        source: CAM_SOURCE,
        filter: ["any", ["==", ["get", "watched"], 1], ["==", ["get", "flagged"], 1], ["==", ["get", "selected"], 1]],
        paint: {
          "circle-radius": ["case", ["==", ["get", "selected"], 1], 13, ["==", ["get", "flagged"], 1], 11, 10],
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-width": 1.3,
          "circle-stroke-color": [
            "case",
            ["==", ["get", "flagged"], 1],
            "rgba(224, 86, 79, 0.55)",
            ["==", ["get", "selected"], 1],
            "rgba(210, 225, 250, 0.65)",
            "rgba(255, 255, 255, 0.42)",
          ],
        },
      });
      map.addLayer({
        id: "meta-cams-dot",
        type: "circle",
        source: CAM_SOURCE,
        paint: {
          "circle-radius": [
            "case",
            ["==", ["get", "selected"], 1],
            7,
            ["==", ["get", "flagged"], 1],
            6,
            ["==", ["get", "watched"], 1],
            5.5,
            4.5,
          ],
          "circle-color": [
            "case",
            ["==", ["get", "flagged"], 1],
            "#E0564F",
            ["==", ["get", "watched"], 1],
            state.accent,
            "rgba(180, 200, 230, 0.65)",
          ],
          "circle-stroke-width": ["case", ["==", ["get", "selected"], 1], 1.5, 0],
          "circle-stroke-color": "rgba(255,255,255,0.9)",
        },
      });
    }

    map.on("click", "meta-cams-dot", (ev) => {
      const f = ev.features && ev.features[0];
      if (f && f.properties && f.properties.id) state.onSelect(f.properties.id);
    });
    map.on("mouseenter", "meta-cams-dot", () => {
      host.style.cursor = "pointer";
    });
    map.on("mouseleave", "meta-cams-dot", () => {
      host.style.cursor = "grab";
    });
  }

  function ready() {
    if (state.ready) return;
    state.ready = true;
    installLayers();
    // The map is built while the page is still laying out; a 0x0 canvas at
    // this point paints the city into nothing, which reads as "no map".
    map.resize();
    push();
    if (pending) {
      state.cameras = pending.cameras || state.cameras;
      state.results = pending.results || state.results;
      state.watch = pending.watch || state.watch;
      state.hotspots = pending.hotspots || state.hotspots;
      if ("selected" in pending) state.selected = pending.selected;
      pending = null;
      push();
    }
  }

  map.on("load", ready);
  // After a fallback the style arrives later than the first load, so the ready
  // work is triggered by whichever of the two events lands first.
  map.on("styledata", () => {
    if (!state.ready && map.isStyleLoaded()) ready();
  });

  function useOfflineStyle() {
    if (fellBack || state.ready) return;
    fellBack = true;
    usingRemote = false;
    console.info("trio: basemap unreachable, drawing the shipped borough outline");
    try {
      map.setStyle(offlineStyle);
    } catch (err) {
      console.warn("trio: offline basemap failed too", err);
    }
  }
  if (startRemote) setTimeout(useOfflineStyle, REMOTE_STYLE_TIMEOUT_MS);

  // A style that fails to parse leaves a black rectangle forever. Fall back by
  // removing the canvas and letting the caller draw its flat map instead —
  // but only before the style has loaded, so a single bad tile cannot swap a
  // working map for a grid mid-demo.
  map.on("error", (ev) => {
    if (!state.ready) console.warn("trio: 3D map style error", ev && ev.error);
  });

  new ResizeObserver(() => map.resize()).observe(host);
  window.addEventListener("resize", () => map.resize());

  return {
    state,
    threeD: true,
    online: () => usingRemote,
    draw() {
      push();
    },
    set(data = {}) {
      if (!state.ready) {
        pending = { ...(pending || {}), ...data };
        return;
      }
      if (data.cameras) state.cameras = data.cameras;
      if (data.results) state.results = data.results;
      if (data.watch) state.watch = data.watch;
      if (data.hotspots) state.hotspots = data.hotspots;
      if ("selected" in data) state.selected = data.selected;
      push();
    },
    focus(camera) {
      if (!camera || !Number.isFinite(camera.latitude) || !Number.isFinite(camera.longitude)) return;
      map.flyTo({
        center: [camera.longitude, camera.latitude],
        zoom: Math.max(map.getZoom(), 13.2),
        pitch: 55,
        duration: 900,
      });
    },
    resize() {
      map.resize();
    },
    destroy() {
      map.remove();
      host.remove();
      canvas.style.visibility = "";
    },
  };
}
