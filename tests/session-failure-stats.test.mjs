// Node built-in test runner, no dependencies:
//   node --test tests/session-failure-stats.test.mjs
//
// Rowan DETAIL-2 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a failures-by-cause line,
// computed only from entries the log actually recorded. DETAIL-1
// bucketed successful assessments by product and left failures as one
// total; this breaks that total down by recorded status — network,
// HTTP, or invalid response — so a failing session says what is
// failing, not just that something failed. No sampling, no model, no
// invented counts: a status the log never recorded stays zero, and
// the buckets always sum to the failed total.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordFailed(log, status) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: "ignis",
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("each failure status buckets separately; buckets sum to failed", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error");
  recordFailed(log, "network_error");
  recordFailed(log, "http_error");
  recordFailed(log, "invalid_response");
  recordFailed(log, "invalid_response");
  recordFailed(log, "invalid_response");
  const stats = log.stats();
  assert.equal(stats.failed, 6);
  assert.deepEqual(stats.failedByStatus, {
    network_error: 2,
    http_error: 1,
    invalid_response: 3,
  });
});

test("ok entries leave every failure bucket at zero", () => {
  const log = new SessionLog();
  log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: { product: "ignis" },
  });
  assert.deepEqual(log.stats().failedByStatus, {
    network_error: 0,
    http_error: 0,
    invalid_response: 0,
  });
});

test("failure buckets follow clear: back to zero", () => {
  const log = new SessionLog();
  recordFailed(log, "http_error");
  log.clear();
  assert.deepEqual(log.stats().failedByStatus, {
    network_error: 0,
    http_error: 0,
    invalid_response: 0,
  });
});

test("web wiring: updateLogStats renders the failure line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsByFailure: \$\("log-stats-by-failure"\)/);
  assert.match(
    app,
    /Failures by cause: Network \$\{stats\.failedByStatus\.network_error\} · HTTP \$\{stats\.failedByStatus\.http_error\} · Invalid response \$\{stats\.failedByStatus\.invalid_response\}/,
    "updateLogStats sets the failure line from stats()",
  );
});

test("web wiring: session-log panel holds the failure stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-by-failure" class="note mono">Failures by cause: Network 0 · HTTP 0 · Invalid response 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
