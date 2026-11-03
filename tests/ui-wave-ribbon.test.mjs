// Node built-in test runner, no dependencies:  node --test tests/ui-wave-ribbon.test.mjs
// Covers HN-011 (crew-board live ribbon): the ribbon picks the
// newest incident from the SAME crew-status payload the loop feed
// renders, and the staged-record proof — a test incident written
// to a temp crew data directory in the crew's own record shape is
// projected by readCrewStatus and picked up by the ribbon helper
// with its display tier. No second source, no invented incident.

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { ribbonIncident, ribbonText, flagTier } from "../js/command-loop.js";
import { readCrewStatus } from "../server/crew-status.mjs";

const html = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");

test("ribbonIncident picks the newest incident by created_at, even unsorted", () => {
  const payload = { incidents: [
    { id: "old", created_at: "2026-11-01T03:00:00.000Z", category: "visible smoke" },
    { id: "new", created_at: "2026-11-01T03:30:00.000Z", category: "visible flame" },
    { id: "mid", created_at: "2026-11-01T03:15:00.000Z", category: "dark smoke" },
  ] };
  assert.equal(ribbonIncident(payload).id, "new");
});

test("ribbonIncident returns null when the store holds no incidents", () => {
  assert.equal(ribbonIncident({ incidents: [] }), null);
  assert.equal(ribbonIncident({}), null);
  assert.equal(ribbonIncident(null), null);
});

test("ribbonText names camera, division, category, status, and tier", () => {
  const text = ribbonText({
    camera_name: "1 Ave @ 84 St", division: "vigiles",
    category: "energetic movement", status: "reported",
  });
  assert.match(text, /1 Ave @ 84 St/);
  assert.match(text, /Vigiles/);
  assert.match(text, /energetic movement/);
  assert.match(text, /reported/);
  assert.match(text, /YELLOW/);
  assert.equal(ribbonText(null), null);
});

test("staged-record proof: a raised test alert in the crew store ribbons yellow", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "crew-ribbon-"));
  await writeFile(path.join(dir, "incidents.json"), JSON.stringify({
    "test-alert-1": {
      id: "test-alert-1", status: "reported",
      created_at: "2026-11-01T03:40:00.000Z",
      camera: { id: "cam-test", name: "Test Cam @ 1 Ave", area: "Manhattan" },
      division: "vigiles", category: "energetic movement", priority: "low",
      evidence: { files: [] }, timeline: [{ step: "flag" }],
    },
  }));
  const payload = await readCrewStatus(dir);
  assert.equal(payload.incidents.length, 1);
  const picked = ribbonIncident(payload);
  assert.equal(picked.id, "test-alert-1");
  assert.equal(flagTier(picked.division, picked.category), "yellow");
  assert.match(ribbonText(picked), /Test Cam @ 1 Ave/);
  assert.match(ribbonText(picked), /YELLOW/);
});

test("ribbon element exists in the command view and the map wires it", () => {
  assert.ok(html.includes('<p id="cmd-ribbon" class="cmd-ribbon" role="status" hidden></p>'));
  assert.ok(mapJs.includes('ribbon: $("cmd-ribbon")'));
  assert.ok(mapJs.includes("ribbonIncident(payload)"));
});
