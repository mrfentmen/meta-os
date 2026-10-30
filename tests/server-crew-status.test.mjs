// Tests for GET /api/crew/status (server/crew-status.mjs via
// server/server.mjs): the read-only projection of the agent crew's
// record files that the Command view's loop feed polls. Fixtures are
// real record files written in the crew's own shapes
// (server/queue/crew_records.py); the empty case must answer
// honestly (available: false), never an invented idle state.

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { readCrewStatus } from "../server/crew-status.mjs";
import { createAssessServer } from "../server/server.mjs";

async function fixtureDir() {
  const dir = await mkdtemp(path.join(tmpdir(), "crew-status-"));
  await writeFile(path.join(dir, "crew-status.json"), JSON.stringify({
    service: "imperium-patrol", state: "running", reason: null,
    at: "2026-10-30T10:00:00.000Z", camera_source: "fallback-subset",
    cameras: 60, counts: { checks: 4, baseline: 3, flagged: 1, reported: 1, feed_errors: 0, job_errors: 0 },
  }));
  await writeFile(path.join(dir, "events.jsonl"), [
    JSON.stringify({ at: "2026-10-30T09:59:00.000Z", type: "patrol-check", camera_name: "1 Ave @ 84 St", division: "vigiles", outcome: "baseline", category: "normal activity" }),
    JSON.stringify({ at: "2026-10-30T10:00:00.000Z", type: "dispatch", camera_name: "1 Ave @ 84 St", division: "vigiles", simulated: true, receipt_id: "sim-abc123" }),
    "{torn line",
    "",
  ].join("\n"));
  await writeFile(path.join(dir, "incidents.json"), JSON.stringify({
    "incident-1": {
      id: "incident-1", status: "dispatched-simulated",
      created_at: "2026-10-30T09:59:30.000Z",
      camera: { id: "cam-a", name: "1 Ave @ 84 St", area: "Manhattan" },
      division: "vigiles", category: "person down", priority: "high",
      timeline: [
        { step: "flag" }, { step: "review" }, { step: "reported" },
        { step: "dispatch", receipt_id: "sim-abc123" },
      ],
    },
  }));
  await writeFile(path.join(dir, "dispatches.jsonl"), JSON.stringify({
    simulated: true, incident_id: "incident-1", receipt_id: "sim-abc123",
    received_at: "2026-10-30T10:00:01.000Z",
  }) + "\n");
  return dir;
}

test("readCrewStatus projects the crew's record files", async () => {
  const status = await readCrewStatus(await fixtureDir());
  assert.equal(status.available, true);
  assert.equal(status.reason, null);
  assert.equal(status.simulated_dispatch, true);
  assert.equal(status.patrol.state, "running");
  assert.equal(status.patrol.camera_source, "fallback-subset");
  // Newest first, torn lines skipped.
  assert.equal(status.events.length, 2);
  assert.equal(status.events[0].type, "dispatch");
  assert.equal(status.events[1].type, "patrol-check");
  assert.equal(status.incidents.length, 1);
  assert.equal(status.incidents[0].id, "incident-1");
  assert.equal(status.incidents[0].steps, 4);
  assert.equal(status.incidents[0].receipt_id, "sim-abc123");
  assert.equal(status.dispatches.count, 1);
  assert.equal(status.dispatches.last.receipt_id, "sim-abc123");
});

test("readCrewStatus on an empty directory answers honestly", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "crew-status-empty-"));
  const status = await readCrewStatus(dir);
  assert.equal(status.available, false);
  assert.match(status.reason, /patrol worker has not written/);
  assert.deepEqual(status.events, []);
  assert.deepEqual(status.incidents, []);
  assert.equal(status.dispatches.count, 0);
  assert.equal(status.patrol, null);
});

test("GET /api/crew/status serves the projection; POST is refused", async () => {
  const dir = await fixtureDir();
  const server = createAssessServer({ crewStatus: () => readCrewStatus(dir) });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const res = await fetch(`${base}/api/crew/status`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.available, true);
    assert.equal(body.incidents[0].category, "person down");
    const post = await fetch(`${base}/api/crew/status`, { method: "POST" });
    assert.equal(post.status, 405);
  } finally {
    server.close();
  }
});
