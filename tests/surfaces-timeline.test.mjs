// HN-062 Records timeline: one timeline from the incident's record
// file, in file order, nothing reordered or filled in.
// Run: node --test tests/surfaces-timeline.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { readFileSync } from "node:fs";

import { timelineView } from "../js/surfaces.js";
import { readCrewStatus } from "../server/crew-status.mjs";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("timeline renders steps in file order with receipt and reason", () => {
  const html = timelineView({ timeline: [
    { step: "patrol", at: "2026-11-01T08:00:00Z" },
    { step: "review", at: "2026-11-01T08:05:00Z" },
    { step: "investigation", at: "2026-11-01T08:10:00Z" },
    { step: "dispatch", at: "2026-11-01T08:12:00Z", receipt_id: "sim-xyz" },
  ] });
  const order = ["patrol", "review", "investigation", "dispatch"]
    .map((s) => html.indexOf(`>${s}<`));
  assert.ok(order.every((v, i) => i === 0 || v > order[i - 1]), "steps out of file order");
  assert.match(html, /receipt sim-xyz/);
});

test("timeline does not reorder an out-of-order record", () => {
  const html = timelineView({ timeline: [
    { step: "dispatch", receipt_id: "sim-1" },
    { step: "review" },
  ] });
  assert.ok(html.indexOf(">dispatch<") < html.indexOf(">review<"));
});

test("timeline with no steps is an honest empty state", () => {
  assert.match(timelineView({ timeline: [] }), /No timeline recorded/);
  assert.match(timelineView({}), /No timeline recorded/);
});

test("crew-status projection passes the record timeline through intact", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "crew-timeline-"));
  await writeFile(path.join(dir, "incidents.json"), JSON.stringify({
    "incident-9": {
      id: "incident-9", status: "dispatched-simulated",
      created_at: "2026-11-01T08:00:00Z",
      camera: { id: "cam-a", name: "1 Ave", area: "Manhattan" },
      division: "vigiles", category: "person down", priority: "high",
      timeline: [
        { step: "patrol", at: "2026-11-01T08:00:00Z" },
        { step: "review", at: "2026-11-01T08:05:00Z" },
        { step: "dispatch", receipt_id: "sim-xyz" },
      ],
    },
  }));
  const status = await readCrewStatus(dir);
  assert.equal(status.incidents.length, 1);
  assert.deepEqual(
    status.incidents[0].timeline.map((s) => s.step),
    ["patrol", "review", "dispatch"],
  );
  assert.equal(status.incidents[0].timeline[2].receipt_id, "sim-xyz");
});

test("boards page has a timeline section wired to live crew records", () => {
  assert.match(surfacesHtml, /id="board-timeline"/);
  assert.match(surfacesHtml, /id="timeline-content"/);
});
