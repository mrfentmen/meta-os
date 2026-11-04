// Meta Trio shared core: one state model for Police, Fire and EMS.
//
// The three division apps (trio/vigiles.html, trio/ignis.html,
// trio/medicus.html) share everything that is not layout. This file owns the
// backend calls, the camera list, the watch list, the assessment requests and
// the agent crew status. It renders nothing, so each page is free to lay the
// same data out its own way.
//
// Every failure is a value, not an exception that disappears. Callers get
// {ok:false, reason} where the reason names the port, so a dead backend shows
// up in the UI as "backend unreachable on 127.0.0.1:8080" instead of a spinner
// that never stops.

export const BACKEND_PORT = 8080;

export const DIVISIONS = {
  police: {
    key: "police",
    product: "vigiles",
    name: "Vigiles",
    full: "Meta Vigiles",
    dept: "Police",
    page: "trio/vigiles.html",
    icon: "police",
    accent: "#4F7EC2",
    brief: "Visual event awareness. Flags a camera for human review, never for dispatch.",
  },
  fire: {
    key: "fire",
    product: "ignis",
    name: "Ignis",
    full: "Meta Ignis",
    dept: "Fire",
    page: "trio/ignis.html",
    icon: "fire",
    accent: "#D9602B",
    brief: "Visible fire and smoke. A flag is a reason to look, not a report of an incident.",
  },
  ems: {
    key: "ems",
    product: "medicus",
    name: "Medicus",
    full: "Meta Medicus",
    dept: "EMS",
    page: "trio/medicus.html",
    icon: "ems",
    accent: "#3FA88B",
    brief: "Scene and casualty awareness. Triage here sorts frames for review, not patients.",
  },
};

export const MAX_WATCHED = 6;

export function backendBase() {
  if (typeof location !== "object" || !location.origin) return "http://127.0.0.1:" + BACKEND_PORT;
  return location.origin;
}

export function backendLabel() {
  const base = backendBase();
  try {
    const u = new URL(base);
    return u.host;
  } catch {
    return "127.0.0.1:" + BACKEND_PORT;
  }
}

// ---------------------------------------------------------------- cameras

export function normalizeCamera(raw) {
  if (!raw || typeof raw !== "object") return null;
  const { id, name, latitude, longitude, area, isOnline, imageUrl } = raw;
  if (typeof id !== "string" || id.length === 0) return null;
  if (typeof name !== "string" || name.length === 0) return null;
  if (typeof area !== "string" || area.length === 0) return null;
  if (typeof imageUrl !== "string" || imageUrl.length === 0) return null;
  if (typeof latitude !== "number" || !Number.isFinite(latitude)) return null;
  if (typeof longitude !== "number" || !Number.isFinite(longitude)) return null;
  return {
    id,
    name,
    latitude,
    longitude,
    area,
    imageUrl,
    online: isOnline === true || isOnline === "true",
    // "ipcam" is the server's own marker (server/ipcam.mjs) for a camera
    // reached through ffmpeg instead of the NYCTMC list. The pages name the
    // source because the two behave differently: NYCTMC publishes a JPEG and
    // an IP camera is a frame the server grabbed, with its own latency and
    // its own failure text.
    source: raw.source === "ipcam" ? "ipcam" : "nyctmc",
  };
}

// What the board shows for this camera's origin. Null means the ordinary
// NYCTMC list, which the header already names; a chip would only repeat it.
export function sourceTag(cam) {
  return cam && cam.source === "ipcam" ? "IP CAM" : null;
}

function listFromBody(body) {
  if (Array.isArray(body)) return body;
  if (body && Array.isArray(body.cameras)) return body.cameras;
  if (body && Array.isArray(body.data)) return body.data;
  return null;
}

// The offline subset ships with the console app. Importing it keeps one copy
// of the list instead of a second one here that can drift from it.
async function offlineCameras() {
  try {
    const mod = await import("../js/camera-fallback.js");
    const list = mod.FALLBACK_CAMERAS ?? [];
    return list.map(normalizeCamera).filter(Boolean);
  } catch (err) {
    return [];
  }
}

function cacheBust(url) {
  const sep = url.includes("?") ? "&" : "?";
  return url + sep + "t=" + Date.now();
}

function downscale(img, canvas, max) {
  const w = img.naturalWidth || img.width;
  const h = img.naturalHeight || img.height;
  if (!w || !h) throw new Error("snapshot had no pixels");
  const scale = Math.min(1, max / Math.max(w, h));
  canvas.width = Math.max(1, Math.round(w * scale));
  canvas.height = Math.max(1, Math.round(h * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("no 2d canvas context for the snapshot");
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85);
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("image failed to load"));
    img.src = src;
  });
}

// Fetches a camera's snapshot and returns it as a JPEG data URL, which is what
// /api/assess accepts. Both paths end in the same place; the CORS retry exists
// because the camera host serves images without an ACAO header.
export async function captureFrame(camera, canvas, max = 1024) {
  const url = cacheBust(camera.imageUrl);
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    try {
      const img = await loadImage(objUrl);
      return downscale(img, canvas, max);
    } finally {
      URL.revokeObjectURL(objUrl);
    }
  } catch (first) {
    try {
      const img = await loadImage(url);
      return downscale(img, canvas, max);
    } catch (second) {
      throw new Error("snapshot unavailable from this network");
    }
  }
}

// ---------------------------------------------------------------- store

const KEYS = {};
export function storeKey(division) {
  if (!KEYS[division]) KEYS[division] = "metaos.trio." + division + ".watch";
  return KEYS[division];
}

export function createStore(divisionKey) {
  const division = DIVISIONS[divisionKey] ?? DIVISIONS.police;
  const listeners = new Set();
  const canvas = document.createElement("canvas");

  const store = {
    division,
    cameras: [],
    byId: new Map(),
    source: { kind: "loading", note: "Loading the camera list." },
    watch: new Set(),
    results: new Map(), // camera id -> { status, category, summary, at, flagged, reason }
    busy: new Set(),
    activity: [], // newest first { at, text, ok }
    crew: null,
    crewError: null,
    health: null,
    healthError: null,
    query: "",
    selected: null,
    usingOffline: false,

    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },

    emit() {
      for (const fn of listeners) {
        try {
          fn(store);
        } catch (err) {
          // A broken renderer must not take the store down with it.
          console.error("trio: subscriber failed", err);
        }
      }
    },

    note(text, ok = true) {
      store.activity.unshift({ at: Date.now(), text, ok });
      if (store.activity.length > 120) store.activity.length = 120;
    },

    restoreWatch() {
      let raw = null;
      try {
        raw = localStorage.getItem(storeKey(division.key));
      } catch {
        raw = null;
      }
      if (!raw) return;
      try {
        const ids = JSON.parse(raw);
        if (Array.isArray(ids)) for (const id of ids) if (typeof id === "string") store.watch.add(id);
      } catch {
        // A corrupt entry is dropped, not repaired silently into something else.
      }
    },

    saveWatch() {
      try {
        localStorage.setItem(storeKey(division.key), JSON.stringify([...store.watch]));
      } catch {
        // Private mode, or a full quota: the watch list still works this session.
      }
    },

    async loadCameras() {
      const tries = [backendBase() + "/api/cameras"];
      let lastReason = null;
      for (const url of tries) {
        try {
          const ctrl = new AbortController();
          const timer = setTimeout(() => ctrl.abort(), 8000);
          const res = await fetch(url, { signal: ctrl.signal, cache: "no-store" });
          clearTimeout(timer);
          if (!res.ok) {
            lastReason = "camera list returned HTTP " + res.status + " from " + backendLabel();
            continue;
          }
          const raw = await res.json();
          const list = listFromBody(raw);
          if (!list) {
            lastReason = "camera list from " + backendLabel() + " was not a list";
            continue;
          }
          const cameras = list.map(normalizeCamera).filter(Boolean).filter((c) => c.online);
          if (cameras.length === 0) {
            lastReason = "camera list from " + backendLabel() + " had no online cameras";
            continue;
          }
          store.cameras = cameras;
          store.byId = new Map(cameras.map((c) => [c.id, c]));
          store.usingOffline = false;
          const ip = cameras.filter((c) => c.source === "ipcam").length;
          store.source = {
            kind: "live",
            note:
              "Live list from NYC DOT" +
              // An IP camera is not NYC DOT's, so the header says so instead
              // of folding it into their count.
              (ip > 0
                ? " and " + ip + (ip === 1 ? " IP camera" : " IP cameras")
                : "") +
              ". " + cameras.length + " cameras online.",
          };
          store.note("Camera list loaded, " + cameras.length + " online");
          store.emit();
          return { ok: true, count: cameras.length };
        } catch (err) {
          lastReason =
            err && err.name === "AbortError"
              ? "camera list timed out at " + backendLabel()
              : "backend unreachable on " + backendLabel();
        }
      }
      const fallback = await offlineCameras();
      store.cameras = fallback;
      store.byId = new Map(fallback.map((c) => [c.id, c]));
      store.usingOffline = fallback.length > 0;
      store.source = fallback.length
        ? { kind: "offline", note: "Offline camera list, " + fallback.length + " cameras. " + lastReason }
        : { kind: "none", note: lastReason ?? "No camera list and no offline copy." };
      store.note(lastReason ?? "No camera list", false);
      store.emit();
      return { ok: false, reason: lastReason, offline: fallback.length };
    },

    async loadHealth() {
      try {
        const res = await fetch(backendBase() + "/api/health", { cache: "no-store" });
        if (!res.ok) {
          store.health = null;
          store.healthError = "health returned HTTP " + res.status + " from " + backendLabel();
          store.emit();
          return { ok: false, reason: store.healthError };
        }
        store.health = await res.json();
        store.healthError = null;
        store.emit();
        return { ok: true, health: store.health };
      } catch {
        store.health = null;
        store.healthError = "backend unreachable on " + backendLabel();
        store.emit();
        return { ok: false, reason: store.healthError };
      }
    },

    async loadCrew() {
      try {
        const res = await fetch(backendBase() + "/api/crew/status", { cache: "no-store" });
        if (!res.ok) {
          store.crew = null;
          store.crewError = "crew status returned HTTP " + res.status + " from " + backendLabel();
          store.emit();
          return { ok: false, reason: store.crewError };
        }
        const body = await res.json();
        store.crew = body;
        store.crewError = body && body.available === false ? body.reason ?? "no crew records yet" : null;
        store.emit();
        return { ok: true, crew: body };
      } catch {
        store.crew = null;
        store.crewError = "backend unreachable on " + backendLabel();
        store.emit();
        return { ok: false, reason: store.crewError };
      }
    },

    toggleWatch(id) {
      if (!store.byId.has(id)) return { ok: false, reason: "no camera " + id };
      if (store.watch.has(id)) {
        store.watch.delete(id);
        store.saveWatch();
        store.note("Unwatched " + store.byId.get(id).name);
        store.emit();
        return { ok: true, watching: false };
      }
      if (store.watch.size >= MAX_WATCHED) {
        store.note("Watch list is full at " + MAX_WATCHED + " cameras", false);
        store.emit();
        return { ok: false, reason: "watch list is full at " + MAX_WATCHED };
      }
      store.watch.add(id);
      store.saveWatch();
      store.note("Watching " + store.byId.get(id).name);
      store.emit();
      return { ok: true, watching: true };
    },

    setSelected(id) {
      store.selected = id && store.byId.has(id) ? id : null;
      store.emit();
    },

    // One camera, one request. Never called twice for the same camera at once:
    // the busy set is the guard, because two frames of the same camera produce
    // two contradictory lines in the queue.
    async assess(id) {
      const camera = store.byId.get(id);
      if (!camera) return { ok: false, reason: "no camera " + id };
      if (store.busy.has(id)) return { ok: false, reason: "already assessing " + camera.name };
      store.busy.add(id);
      store.emit();
      const started = Date.now();
      let image;
      try {
        image = await captureFrame(camera, canvas);
      } catch (err) {
        store.busy.delete(id);
        store.results.set(id, {
          status: "failed",
          reason: err.message,
          at: Date.now(),
          flagged: false,
        });
        store.note("Snapshot failed for " + camera.name + ": " + err.message, false);
        store.emit();
        return { ok: false, reason: err.message };
      }
      try {
        const res = await fetch(backendBase() + "/api/assess", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product: division.product,
            timestamp: new Date().toISOString(),
            image,
          }),
        });
        const body = await res.json().catch(() => null);
        if (!res.ok) {
          const detail = body && typeof body.error === "string" ? body.error : "no error body";
          throw new Error("HTTP " + res.status + " from " + backendLabel() + ": " + detail);
        }
        if (body && typeof body.error === "string") throw new Error(body.error);
        const assessment = body && body.assessment ? body.assessment : null;
        if (!assessment || typeof assessment.category !== "string") {
          throw new Error("response from " + backendLabel() + " had no assessment.category");
        }
        store.results.set(id, {
          status: "ok",
          category: assessment.category,
          summary: typeof assessment.summary === "string" ? assessment.summary : "",
          review: assessment.requires_human_review === true,
          confidence: typeof assessment.confidence === "number" ? assessment.confidence : null,
          flagged: assessment.requires_human_review === true,
          product: body.product,
          model: body.processing && body.processing.model ? body.processing.model : null,
          latency: Date.now() - started,
          at: Date.now(),
        });
        store.busy.delete(id);
        store.note(
          camera.name + ": " + assessment.category + (assessment.requires_human_review ? " (review)" : "")
        );
        store.emit();
        return { ok: true, category: assessment.category };
      } catch (err) {
        store.busy.delete(id);
        store.results.set(id, {
          status: "failed",
          reason: err.message,
          at: Date.now(),
          flagged: false,
        });
        store.note(camera.name + ": " + err.message, false);
        store.emit();
        return { ok: false, reason: err.message };
      }
    },

    async assessWatched() {
      const ids = [...store.watch];
      if (ids.length === 0) return { ok: false, reason: "nothing is on the watch list" };
      const out = [];
      for (const id of ids) out.push(await store.assess(id));
      return { ok: true, results: out };
    },

    // The order a page draws: newest flag first, then newest result, then name.
    flaggedCameras() {
      return store.cameras
        .filter((c) => {
          const r = store.results.get(c.id);
          return r && r.flagged;
        })
        .sort((a, b) => (store.results.get(b.id).at ?? 0) - (store.results.get(a.id).at ?? 0));
    },

    recent(limit = 8) {
      return store.cameras
        .filter((c) => store.results.has(c.id))
        .sort((a, b) => (store.results.get(b.id).at ?? 0) - (store.results.get(a.id).at ?? 0))
        .slice(0, limit);
    },

    filter(query) {
      store.query = typeof query === "string" ? query : "";
      const q = store.query.trim().toLowerCase();
      if (!q) return [...store.cameras];
      return store.cameras.filter(
        (c) => c.name.toLowerCase().includes(q) || c.area.toLowerCase().includes(q)
      );
    },
  };

  store.restoreWatch();
  return store;
}

// ---------------------------------------------------------------- helpers

export function ago(at) {
  if (!at) return "never";
  const s = Math.max(0, Math.round((Date.now() - at) / 1000));
  if (s < 60) return s + "s ago";
  const m = Math.round(s / 60);
  if (m < 60) return m + "m ago";
  const h = Math.round(m / 60);
  return h + "h ago";
}

export function clock(at = Date.now()) {
  const d = new Date(at);
  const pad = (n) => String(n).padStart(2, "0");
  return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "text") node.textContent = v;
    else if (k === "class") node.className = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// ---------------------------------------------------------------- local map
//
// A small Web-Mercator canvas map. It draws the camera pins, a grid, and the
// five borough labels, and it needs no network: maplibre's basemap style is a
// remote CDN file, which on this image is a blank grey rectangle. A street
// basemap is the right thing for a release; for a demo that must work with no
// network, a coordinate grid plus real camera positions is honest and it moves
// when dragged.

const BOROUGHS = [
  { name: "Manhattan", lat: 40.7831, lon: -73.9712 },
  { name: "Brooklyn", lat: 40.6782, lon: -73.9442 },
  { name: "Queens", lat: 40.7282, lon: -73.7949 },
  { name: "Bronx", lat: 40.8448, lon: -73.8648 },
  { name: "Staten Island", lat: 40.5795, lon: -74.1502 },
];

// The five borough outlines, shipped with the site (28 KB). Without them the
// map is a grid with dots, which reads as broken. Loaded once, cached, and
// redrawn in place; a missing file leaves the grid rather than an error.
let boroughGeometry = null;
let boroughRequest = null;

export function loadBoroughs(url = "/vendor/geo/nyc-boroughs.geojson") {
  if (boroughGeometry) return Promise.resolve(boroughGeometry);
  if (boroughRequest) return boroughRequest;
  boroughRequest = fetch(url, { cache: "force-cache" })
    .then((res) => (res.ok ? res.json() : null))
    .then((geo) => {
      boroughGeometry = geo && geo.type === "FeatureCollection" ? geo : null;
      return boroughGeometry;
    })
    .catch(() => null);
  return boroughRequest;
}

function project(lat, lon, center, zoom, w, h) {
  const scale = 256 * Math.pow(2, zoom);
  const x = ((lon + 180) / 360) * scale;
  const s = Math.sin((lat * Math.PI) / 180);
  const y = (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * scale;
  const cx = ((center.lon + 180) / 360) * scale;
  const cs = Math.sin((center.lat * Math.PI) / 180);
  const cy = (0.5 - Math.log((1 + cs) / (1 - cs)) / (4 * Math.PI)) * scale;
  return [w / 2 + (x - cx), h / 2 + (y - cy)];
}

export function LocalMap(canvas, opts = {}) {
  const state = {
    center: opts.center ?? { lat: 40.73, lon: -73.95 },
    zoom: opts.zoom ?? 10.6,
    cameras: [],
    results: new Map(),
    watch: new Set(),
    selected: null,
    onSelect: opts.onSelect ?? (() => {}),
    accent: opts.accent ?? "#4F7EC2",
    drag: null,
    moved: false,
  };

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // Land under the grid: filled borough polygons with an even-odd fill so
    // enclaves read as holes instead of blobs.
    if (boroughGeometry) {
      ctx.beginPath();
      for (const feature of boroughGeometry.features) {
        const geom = feature.geometry;
        if (!geom) continue;
        const polys = geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
        for (const poly of polys) {
          for (const ring of poly) {
            for (let i = 0; i < ring.length; i++) {
              const [x, y] = project(ring[i][1], ring[i][0], state.center, state.zoom, w, h);
              if (i === 0) ctx.moveTo(x, y);
              else ctx.lineTo(x, y);
            }
            ctx.closePath();
          }
        }
      }
      ctx.fillStyle = "rgba(26, 41, 66, 0.72)";
      ctx.fill("evenodd");
      ctx.strokeStyle = "rgba(104, 136, 182, 0.38)";
      ctx.lineWidth = 1.1;
      ctx.stroke();
    }

    // grid, one line per 0.02 degrees, so the empty map still reads as a map
    ctx.strokeStyle = "rgba(120, 150, 200, 0.10)";
    ctx.lineWidth = 1;
    const stepPx = (() => {
      const a = project(state.center.lat, state.center.lon, state.center, state.zoom, w, h);
      const b = project(state.center.lat, state.center.lon + 0.02, state.center, state.zoom, w, h);
      return b[0] - a[0];
    })();
    if (stepPx > 6) {
      const origin = project(0, 0, state.center, state.zoom, w, h);
      for (let x = origin[0] % stepPx; x < w; x += stepPx) {
        ctx.beginPath();
        ctx.moveTo(Math.round(x) + 0.5, 0);
        ctx.lineTo(Math.round(x) + 0.5, h);
        ctx.stroke();
      }
      for (let y = origin[1] % stepPx; y < h; y += stepPx) {
        ctx.beginPath();
        ctx.moveTo(0, Math.round(y) + 0.5);
        ctx.lineTo(w, Math.round(y) + 0.5);
        ctx.stroke();
      }
    }

    ctx.font = "11px ui-monospace, monospace";
    ctx.fillStyle = "rgba(150, 170, 205, 0.55)";
    for (const b of BOROUGHS) {
      const [x, y] = project(b.lat, b.lon, state.center, state.zoom, w, h);
      if (x < 20 || y < 20 || x > w - 20 || y > h - 20) continue;
      ctx.fillText(b.name.toUpperCase(), x, y);
    }

    // Plain dots first, then flagged, then watched, then selected. At 975
    // cameras a watched dot drawn early is painted over by its neighbours,
    // which is why the board's six cameras were invisible on the map.
    const order = (cam) => {
      if (cam.id === state.selected) return 3;
      if (state.results.get(cam.id)?.flagged) return 2;
      if (state.watch.has(cam.id)) return 1;
      return 0;
    };
    for (const cam of [...state.cameras].sort((a, b) => order(a) - order(b))) {
      const [x, y] = project(cam.latitude, cam.longitude, state.center, state.zoom, w, h);
      if (x < -20 || y < -20 || x > w + 20 || y > h + 20) continue;
      const result = state.results.get(cam.id);
      const flagged = result && result.flagged;
      const watched = state.watch.has(cam.id);
      const selected = cam.id === state.selected;
      ctx.beginPath();
      ctx.arc(x, y, selected ? 7 : flagged ? 6 : watched ? 5.5 : 4.5, 0, Math.PI * 2);
      ctx.fillStyle = flagged ? "#E0564F" : watched ? state.accent : "rgba(180, 200, 230, 0.65)";
      ctx.fill();
      // A watched camera gets a ring as well as the fill: at 975 dots a colour
      // change alone disappears, and the board's six cameras are the point.
      if (watched && !flagged && !selected) {
        ctx.beginPath();
        ctx.arc(x, y, 8.5, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
      if (flagged || selected) {
        ctx.beginPath();
        ctx.arc(x, y, selected ? 11 : 10, 0, Math.PI * 2);
        ctx.strokeStyle = flagged ? "rgba(224, 86, 79, 0.55)" : "rgba(210, 225, 250, 0.5)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }

  function pick(ev) {
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    let best = null;
    let bestD = 14;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    for (const cam of state.cameras) {
      const [x, y] = project(cam.latitude, cam.longitude, state.center, state.zoom, w, h);
      const d = Math.hypot(x - mx, y - my);
      if (d < bestD) {
        bestD = d;
        best = cam;
      }
    }
    return best;
  }

  canvas.addEventListener("pointerdown", (ev) => {
    state.drag = { x: ev.clientX, y: ev.clientY, center: { ...state.center } };
    state.moved = false;
    canvas.setPointerCapture?.(ev.pointerId);
  });
  canvas.addEventListener("pointermove", (ev) => {
    if (!state.drag) return;
    const dx = ev.clientX - state.drag.x;
    const dy = ev.clientY - state.drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) state.moved = true;
    const scale = 256 * Math.pow(2, state.zoom);
    const lonPerPx = 360 / scale;
    const latPerPx = lonPerPx * 0.75;
    state.center = {
      lon: state.drag.center.lon - dx * lonPerPx,
      lat: Math.max(-80, Math.min(80, state.drag.center.lat + dy * latPerPx)),
    };
    draw();
  });
  canvas.addEventListener("pointerup", (ev) => {
    const wasDrag = state.moved;
    state.drag = null;
    state.moved = false;
    if (wasDrag) return;
    const hit = pick(ev);
    if (hit) state.onSelect(hit.id);
  });
  canvas.addEventListener(
    "wheel",
    (ev) => {
      ev.preventDefault();
      state.zoom = Math.max(8, Math.min(15, state.zoom - Math.sign(ev.deltaY) * 0.4));
      draw();
    },
    { passive: false }
  );
  window.addEventListener("resize", draw);
  loadBoroughs(opts.geojsonUrl).then((geo) => {
    if (geo) draw();
  });

  return {
    state,
    draw,
    set(data) {
      if (data.cameras) state.cameras = data.cameras;
      if (data.results) state.results = data.results;
      if (data.watch) state.watch = data.watch;
      if ("selected" in data) state.selected = data.selected;
      draw();
    },
    focus(camera) {
      if (!camera) return;
      state.center = { lat: camera.latitude, lon: camera.longitude };
      state.zoom = Math.max(state.zoom, 13);
      draw();
    },
  };
}
