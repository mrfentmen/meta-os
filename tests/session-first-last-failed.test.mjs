// Node built-in test runner, no dependencies:
//   node --test tests/session-first-last-failed.test.mjs
//
// Hana DETAIL-32: the session-log panel gains global
// first- and last-failure lines, naming the endpoints
// DETAIL-23's global failure span already spans — the
// session's first and last recorded failure timestamps, any
// cause, across products — where the per-product
// DETAIL-19/7 lines alone do not say it at a glance, and
// where DETAIL-23's span alone does not say when the
// session's failures began or last happened. No new stats
// fields: stats() already exposes firstFailedAt/lastFailedAt,
// set by insertion order, so a failure with an unknown or
// missing product still opens and closes them (the
// per-product buckets stay product-gated), a timestamp-less
// failure leaves both endpoints in place, and successes
// never move them. Each line renders "none" with no usable
// failure, same always-renders shape as the other stats
// lines. No sampling, no model, no invented products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordAt(log, timestamp, product, status = "network_error") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

function recordOkAt(log, timestamp, product) {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

test("empty log: the global first and last failures are null, not fabricated timestamps", () => {
  const log = new SessionLog();
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, null);
  assert.equal(stats.lastFailedAt, null);
});

test("first and last failure follow insertion order across products, not timestamp order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "http_error");
  recordAt(log, "2026-10-29T12:03:00.000Z", "medicus", "invalid_response");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:05:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:03:00.000Z");
});

test("successes never move the first or last failure, before, between, or after failures", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:04:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:06:00.000Z", "vigiles", "http_error");
  recordOkAt(log, "2026-10-29T12:08:00.000Z", "medicus");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:02:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:06:00.000Z");
});

test("a failure with an unknown product still opens and closes the global endpoints", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis", "http_error");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:05:00.000Z");
  assert.deepEqual(stats.firstFailedAtByProduct, {
    vigiles: null,
    ignis: "2026-10-29T12:05:00.000Z",
    medicus: null,
  });
  assert.equal(stats.failed, 2);
});

test("a failure with a missing product still opens and closes the global endpoints", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles", "http_error");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:05:00.000Z");
});

test("a timestamp-less failure leaves both endpoints in place", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis", "http_error");
  recordAt(log, "", "ignis");
  log.record({ product: "ignis", latencyMs: null, status: "invalid_response", error: "boom" });
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:05:00.000Z");
});

test("a timestamp-less first failure leaves both endpoints open for later usable failures", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis", "http_error");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:05:00.000Z");
});

test("a single usable failure opens first and last at the same timestamp, span 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus", "http_error");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.failedSpanMs, 0);
});

test("a later failure never overwrites the first failure, even with an earlier timestamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "http_error");
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, "2026-10-29T12:05:00.000Z");
  assert.equal(stats.lastFailedAt, "2026-10-29T12:00:00.000Z");
});

test("first and last failure follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis", "http_error");
  log.clear();
  const stats = log.stats();
  assert.equal(stats.firstFailedAt, null);
  assert.equal(stats.lastFailedAt, null);
});

test("web wiring: updateLogStats renders the global first- and last-failure lines from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFirstFailed: \$\("log-stats-first-failed"\)/);
  assert.match(app, /logStatsLastFailed: \$\("log-stats-last-failed"\)/);
  assert.match(
    app,
    /First failure: \$\{stats\.firstFailedAt \?\? "none"\}/,
    "updateLogStats sets the global first-failure line from stats()",
  );
  assert.match(
    app,
    /Last failure: \$\{stats\.lastFailedAt \?\? "none"\}/,
    "updateLogStats sets the global last-failure line from stats()",
  );
});

test("web wiring: session-log panel holds the global first- and last-failure stats elements", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-first-failed" class="note mono">First failure: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
  assert.match(
    html,
    /<p id="log-stats-last-failed" class="note mono">Last failure: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
