// Node built-in test runner, no dependencies:
//   node --test tests/session-avg-latency.test.mjs
//
// Rowan DETAIL-4 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains an average-successful-
// latency line, computed only from measurements the log actually
// recorded. DETAIL-1 bucketed successes by product, DETAIL-2 broke
// failures down by cause, DETAIL-3 named the most recent success;
// this says how slow successes typically were, so a session of fast
// successes reads differently from one of slow ones. Failures never
// contribute, an ok entry with no finite latency is skipped rather
// than counted as zero, and an empty log reads "none" — no sampling,
// no model, no invented latency.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, latencyMs, product = "ignis") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, status = "network_error", latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: "ignis",
    latencyMs,
    status,
    error: "boom",
  });
}

test("empty log: avgOkLatencyMs is null", () => {
  const log = new SessionLog();
  assert.equal(log.stats().avgOkLatencyMs, null);
});

test("mean over ok latencies only", () => {
  const log = new SessionLog();
  recordOk(log, 100);
  recordOk(log, 300);
  assert.equal(log.stats().avgOkLatencyMs, 200);
});

test("failures never contribute, even with a recorded latency", () => {
  const log = new SessionLog();
  recordOk(log, 100);
  recordFailed(log, "http_error", 9999);
  assert.equal(log.stats().avgOkLatencyMs, 100);
});

test("failures alone leave avgOkLatencyMs null", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", 500);
  assert.equal(log.stats().avgOkLatencyMs, null);
});

test("ok entry with no usable latency is skipped, not counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, 200);
  recordOk(log, null);
  recordOk(log, undefined);
  assert.equal(log.stats().avgOkLatencyMs, 200);
});

test("ok entries with no usable latency at all leave avgOkLatencyMs null", () => {
  const log = new SessionLog();
  recordOk(log, null);
  assert.equal(log.stats().avgOkLatencyMs, null);
});

test("avgOkLatencyMs follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, 100);
  log.clear();
  assert.equal(log.stats().avgOkLatencyMs, null);
});

test("web wiring: updateLogStats renders the average-latency line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsAvgLatency: \$\("log-stats-avg-latency"\)/);
  assert.match(
    app,
    /Average successful latency: \$\{stats\.avgOkLatencyMs === null \? "none"/,
    "updateLogStats sets the average-latency line from stats()",
  );
});

test("web wiring: session-log panel holds the average-latency stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-avg-latency" class="note mono">Average successful latency: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
