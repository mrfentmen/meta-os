// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-status-of-entries-within-product.test.mjs
//
// ROWAN DETAIL-44: the session-log panel gains a per-product
// failure-cause-share-of-that-product's-entries line, computed only
// from entries the log actually recorded. DETAIL-42 re-based DETAIL-9's
// product-cause counts on the session's entry total, but a global
// denominator cannot say what slice of Vigiles' own recorded entries
// are Vigiles network errors: this re-bases each product-cause count
// on that product's own entry total (DETAIL-14). The denominator is
// the product's own entry count, not the session entry total and not
// the failed total: successes of a product sit in that product's
// denominator but move no cell, and a product with no entries of its
// own reads null per cell even while other products have entries —
// unlike DETAIL-42, which reads 0 for that product once the session
// holds any entry at all. Once a product holds any entry, a cell with
// no failures of that combination reads 0, never "none" — including
// a success-only product, unlike DETAIL-33, whose denominator is the
// product's failed total and which reads null until the product's
// first failure. A failure with an unknown or missing product moves
// no cell and no denominator, exactly as DETAIL-33's within-product
// cells do. The three cause cells for a product sum to that product's
// DETAIL-12 failed share. No sampling, no model, no invented
// measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_CELL = { network_error: null, http_error: null, invalid_response: null };
const ZERO_CELL = { network_error: 0, http_error: 0, invalid_response: 0 };
const NULL_SHARES = { vigiles: NULL_CELL, ignis: NULL_CELL, sanitas: NULL_CELL };

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
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, NULL_SHARES);
});

test("a single failure reads 1 in its own cell; products with no entries read null, not 0", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, {
    vigiles: NULL_CELL,
    ignis: { network_error: 0, http_error: 1, invalid_response: 0 },
    sanitas: NULL_CELL,
  });
});

test("mixed counts divide by the product's own entry total, not the session total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "ignis", "invalid_response");
  // Vigiles holds 3 entries, Ignis holds 3 — not 6 each: each
  // product's cells divide by its own entry count.
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, {
    vigiles: { network_error: 1 / 3, http_error: 0, invalid_response: 0 },
    ignis: { network_error: 0, http_error: 1 / 3, invalid_response: 1 / 3 },
    sanitas: NULL_CELL,
  });
});

test("a product's three cause cells sum to its DETAIL-12 failed share", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "sanitas", "invalid_response");
  const stats = log.stats();
  const ignisCells = stats.failedShareByStatusOfEntriesWithinProduct.ignis;
  const ignisSum = ignisCells.network_error + ignisCells.http_error + ignisCells.invalid_response;
  assert.equal(ignisSum, stats.failedShareByProduct.ignis);
  const sanitasCells = stats.failedShareByStatusOfEntriesWithinProduct.sanitas;
  const sanitasSum = sanitasCells.network_error + sanitasCells.http_error + sanitasCells.invalid_response;
  assert.equal(sanitasSum, stats.failedShareByProduct.sanitas);
});

test("a failure with an unknown product moves no cell and no denominator", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "mystery", "network_error");
  // Unlike DETAIL-42, the unknown failure does not even sit in a
  // per-product denominator: every product's cells are unchanged
  // (vigiles 0 per cause from its own success, others null).
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, {
    vigiles: ZERO_CELL,
    ignis: NULL_CELL,
    sanitas: NULL_CELL,
  });
  assert.equal(log.stats().failedShare, 0.5);
});

test("a failure with a missing product moves no cell and no denominator", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas");
  recordFailed(log, null, "http_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, {
    vigiles: NULL_CELL,
    ignis: NULL_CELL,
    sanitas: ZERO_CELL,
  });
  assert.equal(log.stats().failedShare, 0.5);
});

test("an ok entry with an unknown product creates no per-product denominator", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  // Unlike DETAIL-42, which reads 0 per cell once the session holds
  // any entry, every product still reads null: no product holds an
  // entry of its own.
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, NULL_SHARES);
});

test("successes sit in the denominator but move no cell, and a success-only product reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, {
    vigiles: ZERO_CELL,
    ignis: ZERO_CELL,
    sanitas: NULL_CELL,
  });
});

test("a failure-only product divides by its own failure count", () => {
  const log = new SessionLog();
  recordFailed(log, "sanitas", "network_error");
  recordFailed(log, "sanitas", "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, {
    vigiles: NULL_CELL,
    ignis: NULL_CELL,
    sanitas: { network_error: 0.5, http_error: 0, invalid_response: 0.5 },
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  log.clear();
  assert.deepEqual(log.stats().failedShareByStatusOfEntriesWithinProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failure-cause-share-of-that-product's-entries line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByStatusOfEntriesWithinProduct: \$\("log-stats-failed-share-by-status-of-entries-within-product"\)/);
  assert.match(
    app,
    /Failure-cause share of that product's entries by product: Vigiles Network \$\{stats\.failedShareByStatusOfEntriesWithinProduct\.vigiles\.network_error === null \? "none" : `\$\{Math\.round\(stats\.failedShareByStatusOfEntriesWithinProduct\.vigiles\.network_error \* 100\)\}%`\}/,
    "updateLogStats sets the failure-cause-share-of-that-product's-entries line from stats()",
  );
});

test("web wiring: session-log panel holds the failure-cause-share-of-that-product's-entries stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-status-of-entries-within-product" class="note mono">Failure-cause share of that product's entries by product: Vigiles Network none, HTTP none, Invalid response none · Ignis Network none, HTTP none, Invalid response none · Sanitas Network none, HTTP none, Invalid response none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
