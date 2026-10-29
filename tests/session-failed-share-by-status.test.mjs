// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-status.test.mjs
//
// Rowan DETAIL-31: the session-log panel gains a global
// failure-cause share of all failures line, computed only from
// entries the log actually recorded. DETAIL-9 named the global
// counts per cause and DETAIL-29 split them per product; this
// divides each global count by the session's failed total, so a
// session where half of all failures are network errors reads
// differently from one where the same count is a small slice of
// a much larger failure total. The denominator is the failed
// total: a session with no failures at all reads null per cause
// (an empty log and a success-only log alike), but once the
// session holds any failure, a cause with no failures reads 0,
// never "none". Unlike DETAIL-29's cells, these always sum to 1
// once any failure exists: failedByStatus is product-blind, so
// a failure with an unknown or missing product still moves its
// cause cell, and record() rejects any other status, so no
// failure can sit in the denominator without a cell. Successes
// never move a cell. No sampling, no model, no invented
// measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_CAUSES = { network_error: null, http_error: null, invalid_response: null };

function recordFailed(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

function recordOk(log, product) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

test("empty log: every cause is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareByStatus, NULL_CAUSES);
});

test("a single failure reads 1 in its own cause and 0 elsewhere", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatus, {
    network_error: 0,
    http_error: 1,
    invalid_response: 0,
  });
});

test("mixed causes across products divide by the failed total, not by product", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "sanitas", "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatus, {
    network_error: 0.5,
    http_error: 0.25,
    invalid_response: 0.25,
  });
});

test("all three causes read thirds of all failures", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "sanitas", "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatus, {
    network_error: 1 / 3,
    http_error: 1 / 3,
    invalid_response: 1 / 3,
  });
});

test("causes sum to 1 whenever failures exist", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "sanitas", "invalid_response");
  const shares = log.stats().failedShareByStatus;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a failure with an unknown product still moves its cause cell", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "mystery", "network_error");
  assert.deepEqual(log.stats().failedShareByStatus, {
    network_error: 1,
    http_error: 0,
    invalid_response: 0,
  });
  const shares = log.stats().failedShareByStatus;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a failure with a missing product still moves its cause cell", () => {
  const log = new SessionLog();
  recordFailed(log, "sanitas", "invalid_response");
  recordFailed(log, null, "http_error");
  assert.deepEqual(log.stats().failedShareByStatus, {
    network_error: 0,
    http_error: 0.5,
    invalid_response: 0.5,
  });
});

test("successes never move a cell, and a success-only log reads null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().failedShareByStatus, NULL_CAUSES);
  recordFailed(log, "ignis", "network_error");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareByStatus, {
    network_error: 1,
    http_error: 0,
    invalid_response: 0,
  });
});

test("a cause with no failures reads 0, never null, once failures exist", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.equal(log.stats().failedShareByStatus.network_error, 0);
  assert.equal(log.stats().failedShareByStatus.invalid_response, 0);
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "network_error");
  log.clear();
  assert.deepEqual(log.stats().failedShareByStatus, NULL_CAUSES);
});

test("web wiring: updateLogStats renders the failed-share-by-status line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByStatus: \$\("log-stats-failed-share-by-status"\)/);
  assert.match(
    app,
    /Failure-cause share of all failures: Network \$\{stats\.failedShareByStatus\.network_error === null \? "none" : `\$\{Math\.round\(stats\.failedShareByStatus\.network_error \* 100\)\}%`\}/,
    "updateLogStats sets the failed-share-by-status line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-share-by-status stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-status" class="note mono">Failure-cause share of all failures: Network none, HTTP none, Invalid response none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
