// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-by-product.test.mjs
//
// ROWAN DETAIL-50: the session-log panel gains a per-product
// failed-span-share-of-failed-window line, computed only from
// entries the log actually recorded. DETAIL-20's per-product
// failed spans say how long each product's failures stretch,
// but not how much of the session's whole failed window each
// product covers: a product can fail twice in a
// one-minute burst inside an hour-long failed window. This
// re-bases DETAIL-20's per-product failed spans on the session's
// global failed span (DETAIL-23), so each product's failed-window
// coverage reads at a glance — the failed-only mirror of
// DETAIL-48's ok-span shares. The denominator is the global
// first-to-last failed window, not a sum of product failed
// windows, so these are raw ratios, never clamped, and they
// do NOT sum to 1: product failed windows overlap, and a share
// above 1 or below 0 means timestamps ran out of insertion
// order, exactly as DETAIL-20's raw spans do. Only failures move
// the endpoints, so successes move neither a bucket nor the
// global failed window, and a failure with an unknown or missing
// product moves no product bucket but still stretches the global
// window, so it dilutes every share without moving any bucket.
// Null per product when the session holds no usable failed window
// at all — an empty log, a success-only log, a single failure,
// or all failures at one timestamp — because a zero global
// failed span has no shares to divide, never NaN; null per
// product whose own failed span is unknown (failures recorded
// but no usable timestamp pair — never a fabricated window);
// 0 per product with no failures once a nonzero failed window
// exists, because it covered none of the window, and 0 per
// single-failure product, whose zero-length window covers none
// of a nonzero window. No sampling, no model, no invented
// measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, medicus: null };

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

test("empty log: every share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedSpanShareByProduct, NULL_SHARES);
});

test("a single failure reads null: a zero global failed span has no shares to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().failedSpanShareByProduct, NULL_SHARES);
});

test("all failures at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "http_error");
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus", "invalid_response");
  assert.deepEqual(log.stats().failedSpanShareByProduct, NULL_SHARES);
});

test("a success-only log reads null: no failed window exists at all", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.deepEqual(log.stats().failedSpanShareByProduct, NULL_SHARES);
});

test("mixed windows divide by the global failed window, and a product with no failures reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis", "http_error");
  recordAt(log, "2026-10-29T12:06:30.000Z", "ignis", "http_error");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Global failed window is 600000 ms (first recorded
  // failure 12:00 to last recorded failure 12:10); ignis
  // covers 330000 of it. Medicus recorded no failure, so
  // it covered none of the window — 0, not "none".
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: 1,
    ignis: 0.55,
    medicus: 0,
  });
});

test("a single-failure product inside a nonzero failed window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "medicus");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: 1,
    ignis: 0,
    medicus: 0,
  });
});

test("an unknown-product failure stretches the global failed window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "mystery");
  // Global failed window is now 1200000 ms; vigiles still
  // spans 600000 of it, and no product bucket moved.
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
});

test("a missing-product failure stretches the global failed window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:20:00.000Z", null);
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: 0,
    ignis: 0.5,
    medicus: 0,
  });
});

test("out-of-order timestamps stay raw: shares can exceed 1 and go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  // Global failed window: first recorded failure 12:10 to
  // last recorded failure 12:20 = 600000 ms. Vigiles spans
  // 12:10 back to 12:00 = -600000 (-1 of the window); ignis
  // spans 12:20 alone = 0. The shares do not sum to 1, and
  // that is the honest reading.
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: -1,
    ignis: 0,
    medicus: 0,
  });
});

test("a product with failures but no usable timestamp pair reads null, distinct from a no-failure product's 0", () => {
  const log = new SessionLog();
  recordAt(log, "", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  // Vigiles recorded failures but no usable timestamps, so
  // its failed window is unknown — null, never a fabricated
  // 0 — while medicus, with no failures at all, covered none
  // of the window and reads 0.
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: null,
    ignis: 1,
    medicus: 0,
  });
});

test("successes never move a share, even outside the failed window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "ignis");
  // Unlike DETAIL-46, successes do not stretch the window:
  // the global failed window stays 600000 ms, vigiles covers
  // all of it, and success-only ignis reads 0, not null.
  assert.deepEqual(log.stats().failedSpanShareByProduct, {
    vigiles: 1,
    ignis: 0,
    medicus: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedSpanShareByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failed-span-share line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareByProduct: \$\("log-stats-failed-span-share-by-product"\)/);
  assert.match(
    app,
    /Failure-span share of failed window by product: Vigiles \$\{stats\.failedSpanShareByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the failed-span-share line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-span-share stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-share-by-product" class="note mono">Failure-span share of failed window by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
