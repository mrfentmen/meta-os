// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-share-of-own-failed-window-by-product.test.mjs
//
// Hana DETAIL-69: the session-log panel gains a
// per-product entry-span-share-of-that-product's-own-
// failure-window line, computed only from entries the
// log actually recorded. DETAIL-67's global share says
// how much of the whole recording the failures
// covered, and DETAIL-59's per-product shares say how
// much of everything a product recorded its failures
// covered, but neither says how a product's whole
// recording stretches against its own failures
// alone: a product whose recording ran twice
// everything it itself failed across reads
// differently from one whose recording barely
// outlasts its failures. This re-bases DETAIL-17's
// per-product entry spans on each product's own
// DETAIL-20 failed span, so a session where Vigiles
// recorded across 20 minutes while Vigiles failures
// spanned 5 minutes reads 4 at a glance — the mirror
// of DETAIL-68, the within-product mirror of
// DETAIL-67, the last own-window direction
// DETAIL-59/60's own-entry shares imply but do not
// state from the entry side. Only that product's
// entries move its numerator and only that product's
// failures move its denominator, so other products'
// entries stretch no share here. Null per product
// with no usable own failure window at all (no
// failures, a single failure, or all failures at one
// timestamp — a zero own failed span has no share to
// divide, never NaN); null per product with entries
// but no usable entry timestamp pair; 0 per product
// whose first and last entries share one timestamp
// against a nonzero own failure window. Raw ratios,
// never clamped: above 1 is the normal case, below 1
// or below 0 means timestamps ran out of insertion
// order. An unknown- or missing-product entry moves
// no bucket and no product denominator. No sampling,
// no model, no invented measurements.

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
  assert.deepEqual(log.stats().entrySpanShareOfOwnFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a successes-only product reads null: no failure window to divide by", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats().entrySpanShareOfOwnFailedWindowByProduct;
  assert.equal(stats.vigiles, null);
  assert.equal(stats.ignis, null);
  assert.equal(stats.sanitas, null);
});

test("a failures-only product reads 1: its recording is its failure window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOwnFailedWindowByProduct.vigiles, 1);
});

test("a single failure reads null: a zero failed span has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:09:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOwnFailedWindowByProduct.vigiles, null);
});

test("mixed products read their own entry span over their own failed span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:04:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles recorded 20 minutes across a 5-minute
  // failure window; Ignis recorded 2 minutes across
  // a 4-minute failure window.
  assert.equal(stats.entrySpanShareOfOwnFailedWindowByProduct.vigiles, 4);
  assert.equal(stats.entrySpanShareOfOwnFailedWindowByProduct.ignis, 1 / 2);
  // Cross-check against the spans themselves.
  assert.equal(stats.entrySpanMsByProduct.vigiles, 20 * 60 * 1000);
  assert.equal(stats.failedSpanMsByProduct.vigiles, 5 * 60 * 1000);
});

test("a zero entry span against a nonzero failed window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  // First and last entries share 12:00 while the
  // failures span 10 minutes: the out-of-order
  // reading, kept raw at 0.
  assert.equal(log.stats().entrySpanShareOfOwnFailedWindowByProduct.vigiles, 0);
});

test("an unparseable first-entry timestamp reads null, never a fabricated window", () => {
  const log = new SessionLog();
  recordOkAt(log, "not-a-date", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(log.stats().entrySpanShareOfOwnFailedWindowByProduct.vigiles, null);
});

test("an unknown-product success moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles still reads 1/2: the mystery successes
  // stretch no Vigiles window. Its entry span is 5
  // minutes (first entry 12:00, last Vigiles entry
  // the 12:05 success) over its 10-minute failed span.
  assert.equal(stats.entrySpanShareOfOwnFailedWindowByProduct.vigiles, 1 / 2);
  assert.equal(stats.failedSpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.entrySpanMsByProduct.vigiles, 5 * 60 * 1000);
});

test("an unknown-product failure moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles still reads 1: the mystery failures
  // stretch no Vigiles failed span.
  assert.equal(stats.entrySpanShareOfOwnFailedWindowByProduct.vigiles, 1);
  assert.equal(stats.entrySpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("a missing-product entry moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  recordAt(log, "2026-10-29T12:02:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfOwnFailedWindowByProduct.ignis, 1);
  assert.equal(stats.failedSpanMsByProduct.ignis, 10 * 60 * 1000);
  assert.equal(stats.entrySpanMsByProduct.ignis, 10 * 60 * 1000);
});

test("a share above 1 is kept raw, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:06:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Entries stretch 10 minutes across a 1-minute
  // failure window: the raw ratio is 10.
  assert.equal(log.stats().entrySpanShareOfOwnFailedWindowByProduct.vigiles, 10);
});

test("a negative share is kept raw when entries run out of order", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  // Entries inserted late-to-early span -10 minutes
  // across a 5-minute failure window: -2.
  assert.equal(log.stats().entrySpanShareOfOwnFailedWindowByProduct.vigiles, -2);
});

test("the share equals the DETAIL-17 span over the DETAIL-20 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.entrySpanShareOfOwnFailedWindowByProduct.vigiles,
    stats.entrySpanMsByProduct.vigiles / stats.failedSpanMsByProduct.vigiles,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().entrySpanShareOfOwnFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the entry-span-share-of-own-failed-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanShareOfOwnFailedWindowByProduct: \$\("log-stats-entry-span-share-of-own-failed-window-by-product"\)/);
  assert.match(
    app,
    /Entry-span share of that product's own failure window by product: Vigiles \$\{stats\.entrySpanShareOfOwnFailedWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.entrySpanShareOfOwnFailedWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the entry-span-share-of-own-failed-window line from stats()",
  );
});

test("web wiring: session-log panel holds the entry-span-share-of-own-failed-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-share-of-own-failed-window-by-product" class="note mono">Entry-span share of that product's own failure window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
