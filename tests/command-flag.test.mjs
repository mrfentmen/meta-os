// Node built-in test runner, no dependencies:  node --test tests/command-flag.test.mjs
// Covers the Command view's pure logic (js/command-flag.js): the
// category-based flag rule and its baseline sets per product, the
// incident priority mapping and pulse modes, the capped watch list,
// the incident queue lifecycle, round-robin sampling order, camera
// record validation, borough grouping, and the list search filter.
// Baseline/priority expectations are cross-checked against the real
// category sets in js/products.js so a taxonomy change breaks here.

import { test } from "node:test";
import assert from "node:assert/strict";

import { PRODUCTS, PRODUCT_BY_ID } from "../js/products.js";
import {
  BASELINE_CATEGORIES,
  BOROUGHS,
  CATEGORY_PRIORITY,
  IncidentQueue,
  MAX_WATCHED,
  WatchList,
  applyAssessmentToFlag,
  circlePolygon,
  distanceMeters,
  filterCameras,
  groupCamerasByBorough,
  isBaselineCategory,
  isCameraOnline,
  isFlaggedCategory,
  nearestCameras,
  nextWatchedId,
  normalizeCamera,
  pinStateFor,
  priorityForCategory,
  pulseModeFor,
} from "../js/command-flag.js";

test("baseline sets use only real categories from products.js", () => {
  for (const product of PRODUCTS) {
    const baseline = BASELINE_CATEGORIES[product.id];
    assert.ok(Array.isArray(baseline), `${product.id} has a baseline set`);
    for (const category of baseline) {
      assert.ok(
        product.categories.includes(category),
        `${product.id} baseline "${category}" is a real category`,
      );
    }
  }
});

test("vigiles and medicus baselines are exactly normal activity + indeterminate", () => {
  assert.deepEqual([...BASELINE_CATEGORIES.vigiles].sort(), ["indeterminate", "normal activity"]);
  assert.deepEqual([...BASELINE_CATEGORIES.medicus].sort(), ["indeterminate", "normal activity"]);
});

test("ignis baseline covers no-hazard, indeterminate, and both look-alikes", () => {
  assert.deepEqual(
    [...BASELINE_CATEGORIES.ignis].sort(),
    ["flame-like lighting", "indeterminate", "no hazard visible", "steam or fog"],
  );
});

test("every non-baseline category flags, every baseline category does not", () => {
  for (const product of PRODUCTS) {
    for (const category of product.categories) {
      const baseline = BASELINE_CATEGORIES[product.id].includes(category);
      assert.equal(isBaselineCategory(product.id, category), baseline);
      assert.equal(
        isFlaggedCategory(product.id, category),
        !baseline,
        `${product.id} "${category}" flag=${!baseline}`,
      );
    }
  }
});

test("ignis look-alikes never flag; visible hazards and obscured hazard do", () => {
  assert.equal(isFlaggedCategory("ignis", "steam or fog"), false);
  assert.equal(isFlaggedCategory("ignis", "flame-like lighting"), false);
  assert.equal(isFlaggedCategory("ignis", "visible smoke"), true);
  assert.equal(isFlaggedCategory("ignis", "visible flame"), true);
  assert.equal(isFlaggedCategory("ignis", "obscured or distant hazard"), true);
});

test("flag rule refuses empty categories and unknown products", () => {
  assert.equal(isFlaggedCategory("vigiles", ""), false);
  assert.equal(isFlaggedCategory("vigiles", null), false);
  assert.equal(isFlaggedCategory("vigiles", undefined), false);
  assert.equal(isFlaggedCategory("nope", "person down"), false);
  assert.equal(isBaselineCategory("nope", "normal activity"), false);
});

test("applyAssessmentToFlag reports the rising and falling edges", () => {
  assert.deepEqual(applyAssessmentToFlag(false, "vigiles", "person down"), {
    flagged: true,
    changed: true,
  });
  assert.deepEqual(applyAssessmentToFlag(true, "vigiles", "possible altercation"), {
    flagged: true,
    changed: false,
  });
  assert.deepEqual(applyAssessmentToFlag(true, "vigiles", "normal activity"), {
    flagged: false,
    changed: true,
  });
  assert.deepEqual(applyAssessmentToFlag(false, "medicus", "indeterminate"), {
    flagged: false,
    changed: false,
  });
});

test("pinStateFor: flagged beats watched beats idle", () => {
  assert.equal(pinStateFor({ watched: true, flagged: true }), "flagged");
  assert.equal(pinStateFor({ watched: true, flagged: false }), "watched");
  assert.equal(pinStateFor({}), "idle");
  assert.equal(pinStateFor(), "idle");
});

test("priority mapping uses only real categories and covers the brief's examples", () => {
  for (const [productId, mapping] of Object.entries(CATEGORY_PRIORITY)) {
    for (const category of Object.keys(mapping)) {
      assert.ok(
        PRODUCT_BY_ID[productId].categories.includes(category),
        `${productId} priority "${category}" is a real category`,
      );
      assert.equal(isFlaggedCategory(productId, category), true, `${productId} "${category}" flags`);
    }
  }
  assert.equal(priorityForCategory("vigiles", "person down"), "high");
  assert.equal(priorityForCategory("vigiles", "possible altercation"), "high");
  assert.equal(priorityForCategory("vigiles", "energetic movement"), "medium");
  assert.equal(priorityForCategory("vigiles", "ambiguous gesture"), "medium");
  assert.equal(priorityForCategory("ignis", "visible flame"), "high");
  assert.equal(priorityForCategory("ignis", "visible smoke"), "high");
  assert.equal(priorityForCategory("medicus", "person on ground"), "high");
  assert.equal(priorityForCategory("vigiles", "normal activity"), null);
  assert.equal(priorityForCategory("ignis", "steam or fog"), null);
  assert.equal(priorityForCategory("nope", "person down"), null);
});

test("pulseModeFor: fast for unseen HIGH, slow for other unseen, steady when all seen", () => {
  const high = { priority: "high", seen: false };
  const med = { priority: "medium", seen: false };
  const highSeen = { priority: "high", seen: true };
  assert.equal(pulseModeFor(false, [high]), "none");
  assert.equal(pulseModeFor(true, [high]), "fast");
  assert.equal(pulseModeFor(true, [med]), "slow");
  assert.equal(pulseModeFor(true, [highSeen, med]), "slow");
  assert.equal(pulseModeFor(true, [highSeen]), "steady");
  assert.equal(pulseModeFor(true, []), "steady");
});

test("WatchList enforces the max-6 cap and toggles", () => {
  const watch = new WatchList();
  assert.equal(MAX_WATCHED, 6);
  for (let i = 1; i <= 6; i += 1) {
    assert.deepEqual(watch.add(`cam-${i}`), { ok: true });
  }
  assert.equal(watch.full, true);
  assert.deepEqual(watch.add("cam-7"), { ok: false, reason: "full" });
  assert.deepEqual(watch.add("cam-1"), { ok: false, reason: "duplicate" });
  assert.deepEqual(watch.toggle("cam-7"), { ok: false, watched: false, reason: "full" });
  assert.deepEqual(watch.toggle("cam-1"), { ok: true, watched: false });
  assert.equal(watch.size, 5);
  assert.deepEqual(watch.toggle("cam-7"), { ok: true, watched: true, reason: null });
  assert.deepEqual(watch.list(), ["cam-2", "cam-3", "cam-4", "cam-5", "cam-6", "cam-7"]);
  assert.throws(() => new WatchList(0), RangeError);
});

test("nextWatchedId walks the watch list round-robin", () => {
  assert.equal(nextWatchedId([], null), null);
  assert.equal(nextWatchedId(["a"], null), "a");
  assert.equal(nextWatchedId(["a", "b", "c"], null), "a");
  assert.equal(nextWatchedId(["a", "b", "c"], "a"), "b");
  assert.equal(nextWatchedId(["a", "b", "c"], "c"), "a");
  assert.equal(nextWatchedId(["a", "b"], "gone"), "a");
});

test("IncidentQueue: rising edge creates, same category refreshes, new category supersedes", () => {
  const queue = new IncidentQueue();
  const first = queue.add({
    cameraId: "cam-1",
    productId: "vigiles",
    category: "person down",
    timestamp: "2026-10-30T12:00:00.000Z",
  });
  assert.equal(first.created, true);
  assert.equal(first.incident.priority, "high");
  assert.equal(first.incident.seen, false);
  const again = queue.add({
    cameraId: "cam-1",
    productId: "vigiles",
    category: "person down",
    timestamp: "2026-10-30T12:01:00.000Z",
  });
  assert.equal(again.created, false);
  assert.equal(again.incident.id, first.incident.id);
  assert.equal(again.incident.timestamp, "2026-10-30T12:01:00.000Z");
  const changed = queue.add({
    cameraId: "cam-1",
    productId: "vigiles",
    category: "possible altercation",
    timestamp: "2026-10-30T12:02:00.000Z",
  });
  assert.equal(changed.created, true);
  assert.equal(first.incident.open, false);
  assert.equal(first.incident.clearedReason, "superseded");
  assert.equal(queue.openForCamera("cam-1").id, changed.incident.id);
});

test("IncidentQueue: baseline results never create entries; clear closes the open one", () => {
  const queue = new IncidentQueue();
  const none = queue.add({
    cameraId: "cam-1",
    productId: "ignis",
    category: "steam or fog",
    timestamp: "2026-10-30T12:00:00.000Z",
  });
  assert.deepEqual(none, { incident: null, created: false });
  queue.add({
    cameraId: "cam-1",
    productId: "ignis",
    category: "visible smoke",
    timestamp: "2026-10-30T12:01:00.000Z",
  });
  const cleared = queue.clearForCamera("cam-1");
  assert.equal(cleared.category, "visible smoke");
  assert.equal(cleared.clearedReason, "baseline result");
  assert.equal(queue.openForCamera("cam-1"), null);
  assert.equal(queue.clearForCamera("cam-1"), null);
});

test("IncidentQueue: incidents from different divisions coexist on one camera", () => {
  const queue = new IncidentQueue();
  const vig = queue.add({
    cameraId: "cam-1",
    productId: "vigiles",
    category: "person down",
    timestamp: "2026-10-30T12:00:00.000Z",
    thumbnail: "https://example.test/vig.jpg",
  });
  const ign = queue.add({
    cameraId: "cam-1",
    productId: "ignis",
    category: "visible smoke",
    timestamp: "2026-10-30T12:01:00.000Z",
  });
  assert.equal(vig.created, true);
  assert.equal(ign.created, true);
  // The Ignis flag did NOT supersede the Vigiles incident.
  assert.equal(vig.incident.open, true);
  assert.equal(vig.incident.clearedReason, null);
  assert.equal(ign.incident.open, true);
  // Origin division and thumbnail are recorded on the incident.
  assert.equal(vig.incident.productId, "vigiles");
  assert.equal(ign.incident.productId, "ignis");
  assert.equal(vig.incident.thumbnail, "https://example.test/vig.jpg");
  assert.equal(ign.incident.thumbnail, null);
  // Both are open, addressable per division and together.
  assert.equal(queue.openForCamera("cam-1", "vigiles").id, vig.incident.id);
  assert.equal(queue.openForCamera("cam-1", "ignis").id, ign.incident.id);
  assert.equal(queue.openForCamera("cam-1", "medicus"), null);
  assert.deepEqual(
    queue.openIncidentsForCamera("cam-1").map((i) => i.id),
    [ign.incident.id, vig.incident.id],
    "open incidents newest first",
  );
  assert.equal(queue.list().length, 2);
});

test("IncidentQueue: only a baseline from the SAME division clears its incident", () => {
  const queue = new IncidentQueue();
  const vig = queue.add({
    cameraId: "cam-1",
    productId: "vigiles",
    category: "possible altercation",
    timestamp: "2026-10-30T12:00:00.000Z",
  }).incident;
  const med = queue.add({
    cameraId: "cam-1",
    productId: "medicus",
    category: "person on ground",
    timestamp: "2026-10-30T12:01:00.000Z",
  }).incident;
  // A division with no open incident on the camera clears nothing.
  assert.equal(queue.clearForCamera("cam-1", "ignis"), null);
  assert.equal(vig.open, true);
  assert.equal(med.open, true);
  // Medicus baseline clears only the Medicus incident.
  const cleared = queue.clearForCamera("cam-1", "medicus");
  assert.equal(cleared.id, med.id);
  assert.equal(cleared.clearedReason, "baseline result");
  assert.equal(vig.open, true, "the Vigiles incident survives another division's baseline");
  assert.equal(queue.openForCamera("cam-1", "vigiles").id, vig.id);
  assert.equal(queue.openForCamera("cam-1", "medicus"), null);
  // And the Vigiles incident is still in the one system queue.
  assert.ok(queue.list().some((i) => i.id === vig.id && i.open));
});

test("IncidentQueue: a division switch does not hide or drop open incidents", () => {
  const queue = new IncidentQueue();
  queue.add({
    cameraId: "cam-7",
    productId: "vigiles",
    category: "energetic movement",
    timestamp: "2026-10-30T12:00:00.000Z",
  });
  // Operator switches to Medicus and works there; the Vigiles
  // incident raised earlier is still listed and still pulses.
  queue.add({
    cameraId: "cam-8",
    productId: "medicus",
    category: "crowd gathered around a person",
    timestamp: "2026-10-30T12:05:00.000Z",
  });
  const listed = queue.list();
  assert.equal(listed.length, 2);
  assert.equal(listed[1].productId, "vigiles");
  assert.equal(listed[1].open, true);
  assert.equal(pulseModeFor(true, queue.openIncidentsForCamera("cam-7")), "slow");
  // A same-division category change still supersedes its own only.
  const vig2 = queue.add({
    cameraId: "cam-7",
    productId: "vigiles",
    category: "person down",
    timestamp: "2026-10-30T12:06:00.000Z",
  });
  assert.equal(vig2.created, true);
  assert.equal(queue.openIncidentsForCamera("cam-7").length, 1);
  assert.equal(pulseModeFor(true, queue.openIncidentsForCamera("cam-7")), "fast");
});

test("IncidentQueue: markSeen flips the pulse from fast to steady via pulseModeFor", () => {
  const queue = new IncidentQueue();
  const { incident } = queue.add({
    cameraId: "cam-9",
    productId: "medicus",
    category: "person motionless",
    timestamp: "2026-10-30T12:00:00.000Z",
  });
  assert.equal(pulseModeFor(true, [queue.openForCamera("cam-9")]), "fast");
  assert.equal(queue.markSeen(incident.id).seen, true);
  assert.equal(pulseModeFor(true, [queue.openForCamera("cam-9")]), "steady");
  assert.equal(queue.markSeen("missing"), null);
  const other = queue.add({
    cameraId: "cam-2",
    productId: "vigiles",
    category: "energetic movement",
    timestamp: "2026-10-30T12:03:00.000Z",
  });
  assert.equal(queue.list()[0].id, other.incident.id, "list is newest first");
});

const RAW_CAM = {
  id: "abc-123",
  name: "Broadway @ 45 St",
  latitude: 40.757953,
  longitude: -73.98549,
  area: "Manhattan",
  isOnline: "true",
  imageUrl: "https://webcams.nyctmc.org/api/cameras/abc-123/image",
};

test("normalizeCamera keeps a full API record and rejects unusable ones", () => {
  assert.deepEqual(normalizeCamera(RAW_CAM), RAW_CAM);
  assert.equal(normalizeCamera(null), null);
  assert.equal(normalizeCamera({ ...RAW_CAM, latitude: "40.7" }), null);
  assert.equal(normalizeCamera({ ...RAW_CAM, longitude: Number.NaN }), null);
  assert.equal(normalizeCamera({ ...RAW_CAM, imageUrl: "" }), null);
  assert.equal(normalizeCamera({ ...RAW_CAM, name: "" }), null);
  assert.equal(normalizeCamera({ ...RAW_CAM, id: 7 }), null);
});

test("isCameraOnline accepts the API's string form and booleans", () => {
  assert.equal(isCameraOnline(RAW_CAM), true);
  assert.equal(isCameraOnline({ ...RAW_CAM, isOnline: true }), true);
  assert.equal(isCameraOnline({ ...RAW_CAM, isOnline: "false" }), false);
  assert.equal(isCameraOnline(null), false);
});

test("groupCamerasByBorough orders the five boroughs and omits empty groups", () => {
  const cams = [
    { ...RAW_CAM, id: "q1", area: "Queens" },
    { ...RAW_CAM, id: "m1", area: "Manhattan" },
    { ...RAW_CAM, id: "m2", area: "Manhattan" },
    { ...RAW_CAM, id: "s1", area: "Staten Island" },
  ];
  const groups = groupCamerasByBorough(cams);
  assert.deepEqual(
    groups.map((g) => g.area),
    ["Manhattan", "Queens", "Staten Island"],
  );
  assert.deepEqual(
    groups[0].cameras.map((c) => c.id),
    ["m1", "m2"],
  );
  assert.deepEqual(BOROUGHS, ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]);
});

test("filterCameras matches name and borough, case-insensitive; blank returns all", () => {
  const cams = [
    { ...RAW_CAM, id: "1", name: "Broadway @ 45 St", area: "Manhattan" },
    { ...RAW_CAM, id: "2", name: "Belt Pkwy @ Ocean Pkwy", area: "Brooklyn" },
    { ...RAW_CAM, id: "3", name: "Belt Pkwy @ 125 St", area: "Queens" },
  ];
  assert.deepEqual(filterCameras(cams, "").map((c) => c.id), ["1", "2", "3"]);
  assert.deepEqual(filterCameras(cams, "  ").map((c) => c.id), ["1", "2", "3"]);
  assert.deepEqual(filterCameras(cams, "belt").map((c) => c.id), ["2", "3"]);
  assert.deepEqual(filterCameras(cams, "QUEENS").map((c) => c.id), ["3"]);
  assert.deepEqual(filterCameras(cams, "zzz"), []);
  assert.deepEqual(filterCameras(null, "belt"), []);
});

test("distanceMeters: zero for the same point, ~111 m for 0.001° of latitude", () => {
  const a = { latitude: 40.758, longitude: -73.9855 };
  assert.equal(distanceMeters(a, a), 0);
  const d = distanceMeters(a, { latitude: 40.759, longitude: -73.9855 });
  assert.ok(d > 105 && d < 118, `0.001° latitude ≈ 111 m, got ${d}`);
  const dLng = distanceMeters(a, { latitude: 40.758, longitude: -73.9845 });
  assert.ok(dLng > 80 && dLng < 90, `0.001° longitude at NYC ≈ 85 m, got ${dLng}`);
});

test("nearestCameras returns only in-radius cameras, nearest first, capped", () => {
  const point = { latitude: 40.758, longitude: -73.9855 };
  const cams = [
    { ...RAW_CAM, id: "far", latitude: 40.768, longitude: -73.9855 },
    { ...RAW_CAM, id: "near", latitude: 40.7585, longitude: -73.9855 },
    { ...RAW_CAM, id: "mid", latitude: 40.760, longitude: -73.9855 },
    { ...RAW_CAM, id: "outside", latitude: 40.9, longitude: -73.9 },
  ];
  const found = nearestCameras(cams, point, 2000);
  assert.deepEqual(found.map((e) => e.camera.id), ["near", "mid", "far"]);
  assert.ok(found[0].distance < found[1].distance && found[1].distance < found[2].distance);
  assert.deepEqual(nearestCameras(cams, point, 2000, 2).map((e) => e.camera.id), ["near", "mid"]);
  assert.deepEqual(nearestCameras(cams, point, 10), []);
  assert.deepEqual(nearestCameras(null, point, 100), []);
});

test("circlePolygon returns a closed ring at roughly the requested radius", () => {
  const ring = circlePolygon(40.758, -73.9855, 120, 32);
  assert.equal(ring.length, 33);
  assert.deepEqual(ring[0], ring[ring.length - 1], "ring is closed");
  for (const [lng, lat] of ring) {
    const d = distanceMeters(
      { latitude: 40.758, longitude: -73.9855 },
      { latitude: lat, longitude: lng },
    );
    assert.ok(Math.abs(d - 120) < 3, `ring point at ${d} m, expected ~120`);
  }
});
