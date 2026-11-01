// Node built-in test runner, no dependencies:  node --test tests/ui-wave-error-states.test.mjs
// Covers HN-014 (error states with retry + the real error class).
// The unit half maps each failure kind; the live half kills the
// local server mid-session — a first crew-status fetch succeeds,
// the server is closed, and the next fetch must reject with the
// network class the retry row would show. No mocked fetch, no
// invented error: the refused connection is real.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { errorClassFor } from "../js/loading.js";
import { readCrewStatus } from "../server/crew-status.mjs";
import { createAssessServer } from "../server/server.mjs";

const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

test("errorClassFor names the real failure kind", () => {
  assert.equal(errorClassFor(new TypeError("fetch failed")), "network");
  assert.equal(errorClassFor(new Error("HTTP 502")), "http");
  assert.equal(errorClassFor(new Error("Endpoint response was not valid JSON: boom")), "invalid");
  assert.equal(errorClassFor(new Error("something odd")), "unknown");
  assert.equal(errorClassFor(null), "unknown");
});

test("loop feed wires a retry control carrying the error class", () => {
  assert.ok(mapJs.includes('import { createDelayedIndicator, errorClassFor } from "./loading.js";'));
  assert.match(mapJs, /Retry \(error: \$\{kind\}\)/);
  assert.match(mapJs, /retry\.addEventListener\("click", \(\) => \{\n\s+li\.remove\(\);\n\s+refreshLoopFeed\(\);\n\s+\}\);/);
  assert.ok(css.includes(".cmd-retry { margin-top: 4px; }"));
});

test("killing the local server mid-session yields the network class", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "crew-kill-"));
  await writeFile(path.join(dir, "crew-status.json"), JSON.stringify({
    service: "imperium-patrol", state: "running", reason: null,
    at: "2026-11-01T04:00:00.000Z", camera_source: "fallback-subset",
    cameras: 1, counts: { checks: 1, baseline: 1, flagged: 0, reported: 0, feed_errors: 0, job_errors: 0 },
  }));
  const server = createAssessServer({ crewStatus: () => readCrewStatus(dir) });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const url = `http://127.0.0.1:${port}/api/crew/status`;
  try {
    const first = await fetch(url, { cache: "no-store" });
    assert.equal(first.ok, true);
    const body = await first.json();
    assert.equal(body.available, true);
    if (typeof server.closeAllConnections === "function") server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
    let caught = null;
    try {
      await fetch(url, { cache: "no-store" });
    } catch (err) {
      caught = err;
    }
    assert.ok(caught, "fetch after the kill must reject");
    assert.equal(errorClassFor(caught), "network");
  } finally {
    if (server.listening) {
      if (typeof server.closeAllConnections === "function") server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    }
  }
});
