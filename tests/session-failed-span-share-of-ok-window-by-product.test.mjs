// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-of-ok-window-by-product.test.mjs
//
// Hana DETAIL-72: the session-log panel gains a
// per-product failed-span-share-of-the-global-success-
// window line, computed only from entries the
// log actually recorded. DETAIL-65's global share says
// how all failures stretch against all successes,
// and DETAIL-50's failed-window shares say how
// each product's failures stretch against all
// failures, but neither says how a product's
// failures stretch against the session's whole
// success window: a product whose failures ran
// twice the whole success window reads differently
// from one that barely outlasts it, even when
// the product's own failures are a small slice of
// all failures. This re-bases DETAIL-20's
// per-product failed spans on the global DETAIL-22
// ok span, so a session where Vigiles failures
// spanned 20 minutes while all successes spanned
// 10 minutes reads 2 at a glance — the by-product
// split of DETAIL-65, the cross-span companion to
// DETAIL-50. Only failures move the numerator, so
// successes move neither a bucket nor the
// numerator, while only successes move the
// denominator. Null per product with no usable
// global ok window at all (empty log, failure-only
// log, a single success, or all successes at one
// timestamp — a zero global ok span has no share
// to divide, never NaN); null per product with
// failures but no usable failed timestamp pair;
// 0 per product with no failures once a nonzero
// ok window exists, and 0 per single-failure
// product. Raw ratios, never clamped: above 1 is
// the normal case, below 1 or below 0 means
// timestamps ran out of insertion order. An
// unknown- or missing-product success stretches
// the global window without moving any bucket;
// an unknown- or missing-product failure moves no
// bucket and no denominator. No sampling, no
// model, no invented measurements.

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
  assert.deepEqual(log.stats().failedSpanShareOfOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a failure-only log reads null: no success window to divide by", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().failedSpanShareOfOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a single success reads null: a zero success window has no share to divide", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOkWindowByProduct.vigiles, null);
});

test("mixed products read their own failed span over the global success window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles failures span 10 minutes and Ignis
  // failures 20 minutes, while all successes span
  // only the first-to-last recorded successes,
  // 12:00 to 12:05 — 5 minutes.
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.vigiles, 2);
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.ignis, 4);
  // The shares do NOT sum to 1: product failed
  // windows overlap, and the global window is
  // first-to-last successes, not a sum.
  assert.equal(stats.failedSpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.failedSpanMsByProduct.ignis, 20 * 60 * 1000);
  assert.equal(stats.okSpanMs, 5 * 60 * 1000);
});

test("a product with no failures reads 0 once a nonzero success window exists", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.vigiles, 0);
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.ignis, 1);
});

test("a single-failure product reads 0 against a nonzero success window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanShareOfOkWindowByProduct.vigiles, 0);
});

test("an unparseable first-failure timestamp reads null, never a fabricated window", () => {
  const log = new SessionLog();
  // The unparseable entry is a failure, so it
  // poisons only Vigiles' failed span, not the
  // global success window it never opens.
  recordAt(log, "not-a-date", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
  assert.equal(stats.failedSpanMsByProduct.vigiles, null);
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.vigiles, null);
});

test("an unknown-product success stretches the global window and dilutes every share", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles failures still span 10 minutes, but
  // the global success window now stretches 30
  // minutes, so Vigiles reads 1/3.
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.vigiles, 1 / 3);
  assert.equal(stats.okSpanMs, 30 * 60 * 1000);
  assert.equal(stats.failedSpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("an unknown-product failure moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.vigiles, 1);
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
});

test("a missing-product success stretches the global window and dilutes every share", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.ignis, 1 / 3);
  assert.equal(stats.okSpanMs, 30 * 60 * 1000);
});

test("a missing-product failure moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.ignis, 1);
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
});

test("another product's failures move no share", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  const stats = log.stats();
  // Ignis failures stretch the global failed span
  // but not the success window, so Vigiles stays 1
  // while Ignis reads its own 30 minutes over 10.
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.vigiles, 1);
  assert.equal(stats.failedSpanShareOfOkWindowByProduct.ignis, 3);
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
});

test("a share above 1 is kept raw, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  // Failures stretch 20 minutes across a 5-minute
  // success window: the raw ratio is 4.
  assert.equal(log.stats().failedSpanShareOfOkWindowByProduct.vigiles, 4);
});

test("a negative share is kept raw when failures run out of order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  // Failures inserted late-to-early span -15
  // minutes across a 10-minute success window:
  // -3/2.
  assert.equal(log.stats().failedSpanShareOfOkWindowByProduct.vigiles, -3 / 2);
});

test("the share equals the DETAIL-20 span over the DETAIL-22 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.failedSpanShareOfOkWindowByProduct.vigiles,
    stats.failedSpanMsByProduct.vigiles / stats.okSpanMs,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedSpanShareOfOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the failed-span-share-of-ok-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareOfOkWindowByProduct: \$\("log-stats-failed-span-share-of-ok-window-by-product"\)/);
  assert.match(
    app,
    /Failure-span share of success window by product: Vigiles \$\{stats\.failedSpanShareOfOkWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareOfOkWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the failed-span-share-of-ok-window line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-span-share-of-ok-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-share-of-ok-window-by-product" class="note mono">Failure-span share of success window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
