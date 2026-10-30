// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-of-failed-by-product.test.mjs
//
// Rowan DETAIL-39: the session-log panel gains a per-product
// failed-count share line, computed only from entries the
// log actually recorded. DETAIL-34 bucketed failed counts per
// product, but raw counts alone cannot say which product's
// failures dominate the session's failures: this re-bases
// each product's failed count on the session's failed total.
// The denominator is the failed total, not the entry total:
// successes are not failures, so they sit in neither a bucket
// nor the denominator, and a session with no failures at all
// reads null per product (an empty log and a success-only log
// alike). Once the session holds any failure, a product with
// no failures reads 0, never "none". A failure with an
// unknown or missing product moves no bucket but still sits
// in the denominator, so the shares sum to 1 only when every
// failure carries a known product, exactly as DETAIL-37's
// shares do. Unlike DETAIL-29/31/33's cause splits, a
// failure's cause does not matter here: every failed status
// counts alike. No sampling, no model, no invented counts.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, medicus: null };

function recordOk(log, product, latencyMs = 100) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, status = "network_error", latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status,
    error: "boom",
  });
}

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, NULL_SHARES);
});

test("a single failure reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("mixed counts divide by the failed total, not the entry total", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "vigiles", "http_error");
  recordFailed(log, "ignis");
  recordFailed(log, "medicus");
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  // 4 failures, not 6 entries: successes move neither bucket nor denominator.
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0.5,
    ignis: 0.25,
    medicus: 0.25,
  });
});

test("shares sum to 1 when every failure carries a known product", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "medicus", "invalid_response");
  const shares = log.stats().failedShareOfFailedByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a failure with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "mystery");
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
});

test("a failure with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordFailed(log, "medicus");
  recordFailed(log, null);
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0.5,
  });
});

test("successes never move a share, and a success-only log reads null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, NULL_SHARES);
  recordFailed(log, "ignis");
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("failures for one product read 1 even beside successes of other products", () => {
  const log = new SessionLog();
  recordFailed(log, "medicus");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 1,
  });
});

test("every failed status counts alike, unlike the cause splits", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "medicus", "invalid_response");
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 1 / 3,
    ignis: 1 / 3,
    medicus: 1 / 3,
  });
});

test("a failure carrying a latency value still counts, unlike the latency sums", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordFailed(log, "ignis", "http_error", 250);
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, {
    vigiles: 0.5,
    ignis: 0.5,
    medicus: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedShareOfFailedByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failed-share-of-failed-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareOfFailedByProduct: \$\("log-stats-failed-share-of-failed-by-product"\)/);
  assert.match(
    app,
    /Failed share of failures by product: Vigiles \$\{stats\.failedShareOfFailedByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedShareOfFailedByProduct\.vigiles \* 100\)\}%`\} /,
    "updateLogStats sets the failed-share-of-failed-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-share-of-failed-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-of-failed-by-product" class="note mono">Failed share of failures by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
