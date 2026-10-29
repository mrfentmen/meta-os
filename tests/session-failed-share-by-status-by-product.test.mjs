// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-status-by-product.test.mjs
//
// Rowan DETAIL-29: the session-log panel gains a per-product
// failure-cause share of all failures line, computed only from
// entries the log actually recorded. DETAIL-9 named the counts per
// product per cause; this divides each count by the session's
// failed total, so a session where half of all failures are Ignis
// network errors reads differently from one where the same count
// is a small slice of a much larger failure total. The denominator
// is the failed total, not the product's own failures: a session
// with no failures at all reads null per cell (an empty log and a
// success-only log alike), but once the session holds any failure,
// a product-cause cell with no failures reads 0, never "none".
// The cells sum to 1 when every failure carries a known product,
// and to less than 1 when unknown- or missing-product failures sit
// in the denominator but in no cell, exactly as DETAIL-13's shares
// do. Successes never move a cell. No sampling, no model, no
// invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_CELLS = {
  vigiles: { network_error: null, http_error: null, invalid_response: null },
  ignis: { network_error: null, http_error: null, invalid_response: null },
  sanitas: { network_error: null, http_error: null, invalid_response: null },
};

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

test("empty log: every cell is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareByStatusByProduct, NULL_CELLS);
});

test("a single failure reads 1 in its own cell and 0 everywhere else", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, {
    vigiles: { network_error: 0, http_error: 0, invalid_response: 0 },
    ignis: { network_error: 0, http_error: 1, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 0 },
  });
});

test("mixed causes and products divide by the failed total, not by product", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "vigiles", "http_error");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "sanitas", "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, {
    vigiles: { network_error: 1 / 4, http_error: 1 / 4, invalid_response: 0 },
    ignis: { network_error: 1 / 4, http_error: 0, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 1 / 4 },
  });
});

test("all three causes for one product read thirds of all failures", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "vigiles", "http_error");
  recordFailed(log, "vigiles", "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, {
    vigiles: { network_error: 1 / 3, http_error: 1 / 3, invalid_response: 1 / 3 },
    ignis: { network_error: 0, http_error: 0, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 0 },
  });
});

test("cells sum to 1 when every failure carries a known product", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "sanitas", "invalid_response");
  const shares = log.stats().failedShareByStatusByProduct;
  const sum = Object.values(shares).flatMap((byStatus) => Object.values(byStatus)).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a failure with an unknown product sits in the denominator but moves no cell", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "mystery", "network_error");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, {
    vigiles: { network_error: 0.5, http_error: 0, invalid_response: 0 },
    ignis: { network_error: 0, http_error: 0, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 0 },
  });
  const shares = log.stats().failedShareByStatusByProduct;
  const sum = Object.values(shares).flatMap((byStatus) => Object.values(byStatus)).reduce((a, b) => a + b, 0);
  assert.equal(sum, 0.5);
});

test("a failure with a missing product sits in the denominator but moves no cell", () => {
  const log = new SessionLog();
  recordFailed(log, "sanitas", "invalid_response");
  recordFailed(log, null, "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, {
    vigiles: { network_error: 0, http_error: 0, invalid_response: 0 },
    ignis: { network_error: 0, http_error: 0, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 0.5 },
  });
});

test("successes never move a cell, and a success-only log reads null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, NULL_CELLS);
  recordFailed(log, "ignis", "network_error");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareByStatusByProduct, {
    vigiles: { network_error: 0, http_error: 0, invalid_response: 0 },
    ignis: { network_error: 1, http_error: 0, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 0 },
  });
});

test("a product with no failures reads 0, never null, once failures exist", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusByProduct.vigiles, {
    network_error: 0,
    http_error: 0,
    invalid_response: 0,
  });
  assert.deepEqual(log.stats().failedShareByStatusByProduct.sanitas, {
    network_error: 0,
    http_error: 0,
    invalid_response: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "network_error");
  log.clear();
  assert.deepEqual(log.stats().failedShareByStatusByProduct, NULL_CELLS);
});

test("web wiring: updateLogStats renders the failed-share-by-status-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByStatusByProduct: \$\("log-stats-failed-share-by-status-by-product"\)/);
  assert.match(
    app,
    /Failure-cause share of all failures by product: Vigiles Network \$\{stats\.failedShareByStatusByProduct\.vigiles\.network_error === null \? "none" : `\$\{Math\.round\(stats\.failedShareByStatusByProduct\.vigiles\.network_error \* 100\)\}%`\}/,
    "updateLogStats sets the failed-share-by-status-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-share-by-status-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-status-by-product" class="note mono">Failure-cause share of all failures by product: Vigiles Network none, HTTP none, Invalid response none · Ignis Network none, HTTP none, Invalid response none · Sanitas Network none, HTTP none, Invalid response none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
