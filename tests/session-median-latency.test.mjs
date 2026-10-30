// Node built-in test runner, no dependencies:
//   node --test tests/session-median-latency.test.mjs
//
// Rowan DETAIL-26: the session-log panel gains a global median
// successful latency line, computed only from entries the log
// actually recorded. The median is the middle recorded round-trip
// latency over successful assessments, where DETAIL-4's mean can
// be pulled by one very slow success and DETAIL-6's range alone
// does not say where the typical success sits. Same measurement
// rules as the mean and range: failures never contribute, and an
// ok entry with no finite latency_ms is skipped rather than
// counted as zero, so the median is always over real recorded
// measurements, across products — an ok entry with an unknown or
// missing product still counts here, just as it counts in the
// global mean and range. An odd count reads its middle value;
// an even count reads the mean of its two middle values. No
// sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, product, latencyMs) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "network_error",
    error: "boom",
  });
}

test("empty log: median is null, not a fabricated latency", () => {
  const log = new SessionLog();
  assert.equal(log.stats().medianOkLatencyMs, null);
});

test("a single success reads its own latency as the median", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 100);
  assert.equal(log.stats().medianOkLatencyMs, 100);
});

test("an odd count reads the middle value, regardless of insertion order", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 300);
  recordOk(log, "ignis", 100);
  recordOk(log, "medicus", 200);
  assert.equal(log.stats().medianOkLatencyMs, 200);
});

test("an even count reads the mean of the two middle values", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 400);
  recordOk(log, "ignis", 100);
  recordOk(log, "medicus", 300);
  recordOk(log, "vigiles", 200);
  assert.equal(log.stats().medianOkLatencyMs, 250);
});

test("a two-success session reads the midpoint, not one end", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 101);
  recordOk(log, "ignis", 102);
  assert.equal(log.stats().medianOkLatencyMs, 101.5);
});

test("failures never contribute, even when they carry a latency", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", 5);
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 200);
  assert.equal(log.stats().medianOkLatencyMs, 150);
});

test("ok entries with no finite latency are skipped, not counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", null);
  recordOk(log, "ignis", NaN);
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 300);
  assert.equal(log.stats().medianOkLatencyMs, 200);
});

test("a session with only failures and latency-less successes reads null", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", 50);
  recordOk(log, "ignis", null);
  assert.equal(log.stats().medianOkLatencyMs, null);
});

test("entries with an unknown or missing product still count in the global median", () => {
  const log = new SessionLog();
  recordOk(log, "mystery", 100);
  recordOk(log, null, 300);
  assert.equal(log.stats().medianOkLatencyMs, 200);
  assert.equal(log.stats().avgOkLatencyMs, 200);
});

test("median follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 200);
  log.clear();
  assert.equal(log.stats().medianOkLatencyMs, null);
});

test("web wiring: updateLogStats renders the median-latency line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsMedianLatency: \$\("log-stats-median-latency"\)/);
  assert.match(
    app,
    /Median successful latency: \$\{stats\.medianOkLatencyMs === null \? "none" : `\$\{Math\.round\(stats\.medianOkLatencyMs\)\} ms`\}/,
    "updateLogStats sets the median-latency line from stats()",
  );
});

test("web wiring: session-log panel holds the median-latency stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-median-latency" class="note mono">Median successful latency: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
