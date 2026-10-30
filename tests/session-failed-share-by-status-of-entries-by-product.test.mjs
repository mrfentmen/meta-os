// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-status-of-entries-by-product.test.mjs
//
// HANA DETAIL-42: the session-log panel gains a per-product
// failure-cause-share-of-all-entries line, computed only from
// entries the log actually recorded. DETAIL-9 bucketed failed
// counts per product and cause, and DETAIL-29 re-based those
// counts on the failed total, but failed-total cells alone
// cannot say what slice of everything recorded a product's
// network errors are: this re-bases each product-cause count
// on the session's entry total. The denominator is the entry
// total, not the failed total: successes sit in the
// denominator but move no cell, and a session with no entries
// at all reads null per cell (an empty log). Once the session
// holds any entry, a cell with no failures of that
// combination reads 0, never "none" — including a
// success-only log, unlike DETAIL-29, whose denominator is
// the failed total and which reads null until the first
// failure. A failure with an unknown or missing product moves
// no cell but still sits in the denominator, so the nine
// cells sum to the global failed share only when every
// failure carries a known product. The three cause cells for
// a product sum to that product's DETAIL-40 failed share.
// No sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_CELL = { network_error: null, http_error: null, invalid_response: null };
const ZERO_CELL = { network_error: 0, http_error: 0, invalid_response: 0 };
const NULL_SHARES = { vigiles: NULL_CELL, ignis: NULL_CELL, medicus: NULL_CELL };
const ZERO_SHARES = { vigiles: ZERO_CELL, ignis: ZERO_CELL, medicus: ZERO_CELL };

function recordOk(log, product, latencyMs = 100) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: every cell is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, NULL_SHARES);
});

test("a single failure reads 1 in its own cell and 0 elsewhere", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, {
    vigiles: ZERO_CELL,
    ignis: { network_error: 0, http_error: 1, invalid_response: 0 },
    medicus: ZERO_CELL,
  });
});

test("mixed counts divide by the entry total, not the failed total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "ignis", "invalid_response");
  // 6 entries, not 3 failures: successes sit in the denominator only.
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, {
    vigiles: { network_error: 1 / 6, http_error: 0, invalid_response: 0 },
    ignis: { network_error: 0, http_error: 1 / 6, invalid_response: 1 / 6 },
    medicus: ZERO_CELL,
  });
});

test("cells sum to the global failed share when every failure carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "medicus", "http_error");
  const shares = log.stats().failedShareByStatusOfEntriesByProduct;
  const sum = Object.values(shares).flatMap((cell) => Object.values(cell)).reduce((a, b) => a + b, 0);
  assert.equal(sum, log.stats().failedShare);
});

test("a failure with an unknown product moves no cell but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "mystery", "network_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, ZERO_SHARES);
  // The cells sum to 0 while the global failed share is 0.5.
  assert.equal(log.stats().failedShare, 0.5);
});

test("a failure with a missing product moves no cell but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordFailed(log, null, "http_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, ZERO_SHARES);
  assert.equal(log.stats().failedShare, 0.5);
});

test("successes never move a cell, and a success-only log reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, ZERO_SHARES);
});

test("a product's three cause cells sum to its DETAIL-40 failed share", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "medicus", "invalid_response");
  const stats = log.stats();
  const ignisCells = stats.failedShareByStatusOfEntriesByProduct.ignis;
  const ignisSum = ignisCells.network_error + ignisCells.http_error + ignisCells.invalid_response;
  assert.equal(ignisSum, stats.failedShareOfEntriesByProduct.ignis);
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  log.clear();
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failure-cause-share-of-entries-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByStatusOfEntriesByProduct: \$\("log-stats-failed-share-by-status-of-entries-by-product"\)/);
  assert.match(
    app,
    /Failure-cause share of all entries by product: Vigiles Network \$\{stats\.failedShareByStatusOfEntriesByProduct\.vigiles\.network_error === null \? "none" : `\$\{Math\.round\(stats\.failedShareByStatusOfEntriesByProduct\.vigiles\.network_error \* 100\)\}%`\}/,
    "updateLogStats sets the failure-cause-share-of-entries-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the failure-cause-share-of-entries-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-status-of-entries-by-product" class="note mono">Failure-cause share of all entries by product: Vigiles Network none, HTTP none, Invalid response none · Ignis Network none, HTTP none, Invalid response none · Medicus Network none, HTTP none, Invalid response none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
