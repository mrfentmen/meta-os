// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-span-share-of-failed-window-by-product.test.mjs
//
// Hana DETAIL-73: the session-log panel gains a
// per-product ok-span-share-of-the-global-failure-
// window line, computed only from entries the
// log actually recorded. DETAIL-64's global share says
// how all successes stretch against all failures,
// and DETAIL-48's ok-window shares say how
// each product's successes stretch against all
// successes, but neither says how a product's
// successes stretch against the session's whole
// failure window: a product whose successes ran
// twice the whole failure window reads differently
// from one that barely outlasts it, even when
// the product's own successes are a small slice of
// all successes. This re-bases DETAIL-21's
// per-product ok spans on the global DETAIL-23
// failed span, so a session where Vigiles successes
// spanned 20 minutes while all failures spanned
// 10 minutes reads 2 at a glance — the by-product
// split of DETAIL-64, the cross-span companion to
// DETAIL-48. Only successes move the numerator, so
// failures move neither a bucket nor the
// numerator, while only failures move the
// denominator. Null per product with no usable
// global failed window at all (empty log,
// success-only log, a single failure, or all
// failures at one timestamp — a zero global
// failed span has no share to divide, never NaN);
// null per product with successes but no usable
// ok timestamp pair; 0 per product with no
// successes once a nonzero failed window exists,
// and 0 per single-success product. Raw ratios,
// never clamped: above 1 is the normal case,
// below 1 or below 0 means timestamps ran out of
// insertion order. An unknown- or missing-product
// failure stretches the global window without
// moving any bucket; an unknown- or
// missing-product success moves no bucket and no
// denominator. No sampling, no model, no invented
// measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOkAt(log, timestamp, product) {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

function recordAt(log, timestamp, product, status = "network_error") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().okSpanShareOfFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a success-only log reads null: no failure window to divide by", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().okSpanShareOfFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a single failure reads null: a zero failure window has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindowByProduct.vigiles, null);
});

test("all failures at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindowByProduct.vigiles, null);
});

test("a failure-only log reads 0: successes covered none of a nonzero failure window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().okSpanShareOfFailedWindowByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0,
  });
});

test("mixed products read their own ok span over the global failure window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles successes span 10 minutes and Ignis
  // successes 20 minutes, while all failures span
  // only the first-to-last recorded failures,
  // 12:00 to 12:05 — 5 minutes.
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.vigiles, 2);
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.ignis, 4);
  // The shares do NOT sum to 1: product success
  // windows overlap, and the global window is
  // first-to-last failures, not a sum.
  assert.equal(stats.okSpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.ignis, 20 * 60 * 1000);
  assert.equal(stats.failedSpanMs, 5 * 60 * 1000);
});

test("a product with no successes reads 0 once a nonzero failure window exists", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  const stats = log.stats();
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.vigiles, 0);
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.ignis, 1);
});

test("a single-success product reads 0 against a nonzero failure window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindowByProduct.vigiles, 0);
});

test("an unparseable first-success timestamp reads null, never a fabricated window", () => {
  const log = new SessionLog();
  // The unparseable entry is a success, so it
  // poisons only Vigiles' ok span, not the
  // global failure window it never opens.
  recordOkAt(log, "not-a-date", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.failedSpanMs, 10 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.vigiles, null);
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.vigiles, null);
});

test("an unknown-product failure stretches the global window and dilutes every share", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles successes still span 10 minutes, but
  // the global failure window now stretches 30
  // minutes, so Vigiles reads 1/3.
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.vigiles, 1 / 3);
  assert.equal(stats.failedSpanMs, 30 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("an unknown-product success moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.vigiles, 1);
  assert.equal(stats.failedSpanMs, 10 * 60 * 1000);
});

test("a missing-product failure stretches the global window and dilutes every share", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.ignis, 1 / 3);
  assert.equal(stats.failedSpanMs, 30 * 60 * 1000);
});

test("a missing-product success moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.ignis, 1);
  assert.equal(stats.failedSpanMs, 10 * 60 * 1000);
});

test("another product's successes move no share", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  const stats = log.stats();
  // Ignis successes stretch no failure window, so
  // Vigiles stays 1 while Ignis reads its own 30
  // minutes over 10.
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.vigiles, 1);
  assert.equal(stats.okSpanShareOfFailedWindowByProduct.ignis, 3);
  assert.equal(stats.failedSpanMs, 10 * 60 * 1000);
});

test("a share above 1 is kept raw, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  // Successes stretch 20 minutes across a 5-minute
  // failure window: the raw ratio is 4.
  assert.equal(log.stats().okSpanShareOfFailedWindowByProduct.vigiles, 4);
});

test("a negative share is kept raw when successes run out of order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  // Successes inserted late-to-early span -15
  // minutes across a 10-minute failure window:
  // -3/2.
  assert.equal(log.stats().okSpanShareOfFailedWindowByProduct.vigiles, -3 / 2);
});

test("the share equals the DETAIL-21 span over the DETAIL-23 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.okSpanShareOfFailedWindowByProduct.vigiles,
    stats.okSpanMsByProduct.vigiles / stats.failedSpanMs,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().okSpanShareOfFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the ok-span-share-of-failed-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkSpanShareOfFailedWindowByProduct: \$\("log-stats-ok-span-share-of-failed-window-by-product"\)/);
  assert.match(
    app,
    /Success-span share of failure window by product: Vigiles \$\{stats\.okSpanShareOfFailedWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okSpanShareOfFailedWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-span-share-of-failed-window line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-span-share-of-failed-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-span-share-of-failed-window-by-product" class="note mono">Success-span share of failure window by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
