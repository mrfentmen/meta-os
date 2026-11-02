// Node built-in test runner, no dependencies:
//   node --test tests/federation-notice.test.mjs
//
// BUILD WAVE W4 — the federation's first moment: an open Ignis
// incident in the one system queue derives a Medicus incoming-scene
// notice, labelled SIMULATED on every surface. The notice is not a
// Medicus assessment: no Medicus category, no priority, no severity,
// no triage, no treatment language, no dispatch. It closes when its
// source incident clears or is superseded. Pure logic plus the
// command-map wiring, checked statically (no browser in this suite).

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  FEDERATION_SOURCE_PRODUCT,
  FEDERATION_TARGET_PRODUCT,
  FederationNotices,
  buildFederationNotice,
  federationNoticeText,
} from "../js/federation.js";
import { IncidentQueue } from "../js/command-flag.js";

const map = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");

const ignisIncident = (overrides = {}) => ({
  id: "incident-1",
  seq: 1,
  cameraId: "cam-7",
  productId: "ignis",
  category: "visible smoke",
  timestamp: "2026-11-02T11:00:00.000Z",
  seen: false,
  open: true,
  cleared: false,
  clearedReason: null,
  ...overrides,
});

test("federation: the notice links incident, camera, and time, and is labelled SIMULATED", () => {
  const notice = buildFederationNotice(ignisIncident());
  assert.equal(notice.sourceProductId, "ignis");
  assert.equal(notice.targetProductId, "medicus");
  assert.equal(notice.sourceIncidentId, "incident-1");
  assert.equal(notice.cameraId, "cam-7");
  assert.equal(notice.timestamp, "2026-11-02T11:00:00.000Z");
  assert.equal(notice.simulated, true);
  assert.equal(notice.label, "SIMULATED");
  assert.equal(notice.category, "visible smoke");
  assert.equal(notice.id, "federation-incident-1");
  assert.match(notice.text, /\(SIMULATED\)/);
  assert.match(notice.text, /no Medicus assessment, no dispatch/);
});

test("federation: the notice text stays scene-only — no diagnosis, triage, treatment, or severity language", () => {
  const text = federationNoticeText("visible smoke");
  assert.doesNotMatch(text, /diagnos/i);
  assert.doesNotMatch(text, /triage/i);
  assert.doesNotMatch(text, /treatment/i);
  assert.doesNotMatch(text, /severity/i);
  assert.doesNotMatch(text, /prescri/i);
  assert.equal(text.includes("priority"), false);
});

test("federation: baseline, closed, superseded, and non-Ignis incidents produce no notice", () => {
  assert.equal(buildFederationNotice(ignisIncident({ category: "no hazard visible" })), null);
  assert.equal(buildFederationNotice(ignisIncident({ category: "steam or fog" })), null);
  assert.equal(buildFederationNotice(ignisIncident({ open: false, cleared: true })), null);
  assert.equal(buildFederationNotice(ignisIncident({ productId: "medicus", category: "person on ground" })), null);
  assert.equal(buildFederationNotice(ignisIncident({ productId: "vigiles", category: "person down" })), null);
  assert.equal(buildFederationNotice(ignisIncident({ id: "" })), null);
  assert.equal(buildFederationNotice(ignisIncident({ cameraId: "" })), null);
  assert.equal(buildFederationNotice(ignisIncident({ timestamp: "" })), null);
  assert.equal(buildFederationNotice(null), null);
});

test("federation: the store refreshes on a repeat, supersedes on a new incident, and closes with its source", () => {
  const store = new FederationNotices();
  const first = store.add(ignisIncident());
  assert.equal(first.created, true);
  assert.equal(store.list().length, 1);

  const refreshed = store.add(ignisIncident({ timestamp: "2026-11-02T11:05:00.000Z" }));
  assert.equal(refreshed.created, false);
  assert.equal(refreshed.notice.timestamp, "2026-11-02T11:05:00.000Z");
  assert.equal(store.list().length, 1);

  const second = store.add(ignisIncident({ id: "incident-2", category: "visible flame" }));
  assert.equal(second.created, true);
  assert.equal(store.list().length, 2);
  const old = store.list().find((notice) => notice.sourceIncidentId === "incident-1");
  assert.equal(old.open, false);
  assert.equal(old.clearedReason, "superseded");
  assert.equal(store.openForCamera("cam-7").sourceIncidentId, "incident-2");

  const seen = store.markSeen("federation-incident-2");
  assert.equal(seen.seen, true);
  assert.equal(store.markSeen("federation-nope"), null);

  const closed = store.clearForSource("incident-2");
  assert.equal(closed.open, false);
  assert.equal(closed.clearedReason, "source cleared");
  assert.equal(store.openForCamera("cam-7"), null);
  assert.equal(store.clearForSource("incident-2"), null);
});

test("federation: a real IncidentQueue incident drives the store end to end", () => {
  const queue = new IncidentQueue();
  const store = new FederationNotices();
  const { incident, created } = queue.add({
    cameraId: "cam-7",
    productId: "ignis",
    category: "visible smoke",
    timestamp: "2026-11-02T11:00:00.000Z",
  });
  assert.equal(created, true);
  const fed = store.add(incident);
  assert.equal(fed.created, true);
  assert.equal(fed.notice.sourceIncidentId, incident.id);
  assert.equal(fed.notice.cameraId, incident.cameraId);
  assert.equal(fed.notice.timestamp, incident.timestamp);

  const cleared = queue.clearForCamera("cam-7", "ignis");
  assert.equal(cleared.id, incident.id);
  assert.equal(store.clearForSource(cleared.id).open, false);
  assert.equal(store.openForCamera("cam-7"), null);
});

test("federation: command-map wires the notice at flag creation, closes it on clear, and renders it SIMULATED", () => {
  assert.match(map, /import \{ FederationNotices \} from "\.\/federation\.js";/);
  assert.match(map, /federation: new FederationNotices\(\),/);
  assert.match(map, /const fed = state\.federation\.add\(incident\);/);
  assert.match(map, /Federation notice \(SIMULATED\) — Medicus incoming-scene notice/);
  assert.match(map, /const clearedIncident = state\.queue\.clearForCamera\(id, product\);/);
  assert.match(map, /state\.federation\.clearForSource\(clearedIncident\.id\);/);
  assert.match(map, /const federationNotices = state\.federation\.list\(\)\.filter\(\(notice\) => notice\.open\);/);
  assert.match(map, /cmd-alert--federation/);
  assert.match(map, /Incoming scene notice \(SIMULATED\) — Ignis flag open/);
  assert.match(map, /Notice only — no Medicus assessment, no dispatch\./);
  assert.match(map, /state\.federation\.markSeen\(notice\.id\);/);
});

test("federation: source and target products are the ones the wave named", () => {
  assert.equal(FEDERATION_SOURCE_PRODUCT, "ignis");
  assert.equal(FEDERATION_TARGET_PRODUCT, "medicus");
});
