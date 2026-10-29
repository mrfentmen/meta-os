// Node built-in test runner, no dependencies:
//   node --test tests/session-latency-range.test.mjs
//
// Rowan DETAIL-6 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a fastest/slowest-
// successful-latency line, bounding DETAIL-4's mean with the range
// over measurements the log actually recorded. A mean alone cannot
// tell a tight session from one with a single very slow success;
// the range says which. Failures never contribute, an ok entry with
// no finite latency is skipped rather than counted as zero, and an
// empty log reads "none" — no sampling, no model, no invented
// latency.

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

test("empty log: min/max ok latency are null", () => {
  const log = new SessionLog();
  assert.equal(log.stats().minOkLatencyMs, null);
  assert.equal(log.stats().maxOkLatencyMs, null);
});

test("range spans ok latencies only", () => {
  const log = new SessionLog();
  recordOk(log, 300);
  recordOk(log, 100);
  recordOk(log, 200);
  assert.equal(log.stats().minOkLatencyMs, 100);
  assert.equal(log.stats().maxOkLatencyMs, 300);
});

test("single ok entry: min and max are that latency", () => {
  const log = new SessionLog();
  recordOk(log, 150);
  assert.equal(log.stats().minOkLatencyMs, 150);
  assert.equal(log.stats().maxOkLatencyMs, 150);
});

test("failures never move the range, even with a recorded latency", () => {
  const log = new SessionLog();
  recordOk(log, 100);
  recordOk(log, 300);
  recordFailed(log, "http_error", 9999);
  recordFailed(log, "network_error", 1);
  assert.equal(log.stats().minOkLatencyMs, 100);
  assert.equal(log.stats().maxOkLatencyMs, 300);
});

test("failures alone leave min/max null", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", 500);
  assert.equal(log.stats().minOkLatencyMs, null);
  assert.equal(log.stats().maxOkLatencyMs, null);
});

test("ok entry with no usable latency is skipped, not counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, 200);
  recordOk(log, null);
  recordOk(log, undefined);
  assert.equal(log.stats().minOkLatencyMs, 200);
  assert.equal(log.stats().maxOkLatencyMs, 200);
});

test("ok entries with no usable latency at all leave min/max null", () => {
  const log = new SessionLog();
  recordOk(log, null);
  assert.equal(log.stats().minOkLatencyMs, null);
  assert.equal(log.stats().maxOkLatencyMs, null);
});

test("min/max follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, 100);
  recordOk(log, 300);
  log.clear();
  assert.equal(log.stats().minOkLatencyMs, null);
  assert.equal(log.stats().maxOkLatencyMs, null);
});

test("web wiring: updateLogStats renders the latency-range line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsLatencyRange: \$\("log-stats-latency-range"\)/);
  assert.match(
    app,
    /Fastest\/slowest successful latency: \$\{stats\.minOkLatencyMs === null \? "none"/,
    "updateLogStats sets the latency-range line from stats()",
  );
});

test("web wiring: session-log panel holds the latency-range stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-latency-range" class="note mono">Fastest\/slowest successful latency: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
