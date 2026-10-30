// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-of-own-ok-window-by-product.test.mjs
//
// Hana DETAIL-62: the session-log panel gains a
// per-product failed-span-share-of-that-product's-own-
// success-window line, computed only from entries the
// log actually recorded. DETAIL-59's per-product
// shares say how much of everything a product
// recorded its failures covered, and DETAIL-60's say
// how much of everything it recorded its successes
// covered, but neither says how failures stretch
// against successes alone: a product whose failures
// stretch across half of everything it succeeded
// across reads differently from one whose failures
// sit inside a short success window. This re-bases
// DETAIL-20's per-product failed spans on each
// product's own DETAIL-21 ok span, so a session
// where Vigiles failures stretch 5 minutes across
// a 10-minute Vigiles success window reads 1/2 at
// a glance — the cross-span within-product slice
// DETAIL-59/60's own-entry shares imply but do not
// state. Only that product's successes move its
// denominator, so other products' successes stretch
// no share here. Null per product with no usable
// own success window at all (no successes, a single
// success, or all successes at one timestamp — a
// zero own ok span has no share to divide, never
// NaN); null per product with failures but no usable
// failed timestamp pair; 0 per product with no
// failures once a nonzero own success window exists,
// and 0 per single-failure product. Raw ratios, never
// clamped: above 1 or below 0 means timestamps ran
// out of insertion order. An unknown- or
// missing-product entry moves no bucket and no
// product denominator. No sampling, no model, no
// invented measurements.

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
  assert.deepEqual(log.stats().failedSpanShareOfOwnOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a failure-only product reads null: no success window to divide by", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats().failedSpanShareOfOwnOkWindowByProduct;
  assert.equal(stats.vigiles, null);
  assert.equal(stats.ignis, null);
  assert.equal(stats.sanitas, null);
});

test("a successes-only product with a real window reads 0", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOwnOkWindowByProduct.vigiles, 0);
});

test("a single success reads null: a zero ok span has no share to divide", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:09:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOwnOkWindowByProduct.vigiles, null);
});

test("mixed products read their own failed span over their own ok span", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:04:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:03:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles failures stretch 5 minutes across a
  // 10-minute success window; Ignis failures stretch
  // 2 minutes across a 4-minute success window.
  assert.equal(stats.failedSpanShareOfOwnOkWindowByProduct.vigiles, 1 / 2);
  assert.equal(stats.failedSpanShareOfOwnOkWindowByProduct.ignis, 1 / 2);
  // Cross-check against the spans themselves.
  assert.equal(stats.failedSpanMsByProduct.vigiles, 5 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("a single failure reads 0 once a nonzero success window exists", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOwnOkWindowByProduct.vigiles, 0);
});

test("a failure with no usable timestamp reads null, never a fabricated window", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, undefined, "vigiles");
  assert.equal(log.stats().failedSpanShareOfOwnOkWindowByProduct.vigiles, null);
});

test("an unknown-product success moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  const stats = log.stats();
  // Vigiles still reads 1/2: the mystery successes
  // stretch no Vigiles window.
  assert.equal(stats.failedSpanShareOfOwnOkWindowByProduct.vigiles, 1 / 2);
  assert.equal(stats.okSpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("an unknown-product failure moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:09:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles reads 0: the mystery failures stretch no
  // Vigiles failed span, so they cannot move it.
  assert.equal(stats.failedSpanShareOfOwnOkWindowByProduct.vigiles, 0);
  assert.equal(stats.failedSpanMsByProduct.vigiles, null);
});

test("a missing-product entry moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  recordAt(log, "2026-10-29T12:02:00.000Z", null);
  recordAt(log, "2026-10-29T12:07:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOwnOkWindowByProduct.ignis, 0);
  assert.equal(stats.okSpanMsByProduct.ignis, 10 * 60 * 1000);
  assert.equal(stats.failedSpanMsByProduct.ignis, null);
});

test("a share above 1 is kept raw, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:06:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Failures stretch 10 minutes across a 1-minute
  // success window: the raw ratio is 10.
  assert.equal(log.stats().failedSpanShareOfOwnOkWindowByProduct.vigiles, 10);
});

test("a negative share is kept raw when failures run out of order", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:09:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  // Failures inserted late-to-early span -8 minutes
  // across a 10-minute success window: -4/5.
  assert.equal(log.stats().failedSpanShareOfOwnOkWindowByProduct.vigiles, -4 / 5);
});

test("the share equals the DETAIL-20 span over the DETAIL-21 span", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.failedSpanShareOfOwnOkWindowByProduct.vigiles,
    stats.failedSpanMsByProduct.vigiles / stats.okSpanMsByProduct.vigiles,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedSpanShareOfOwnOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the failed-span-share-of-own-ok-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareOfOwnOkWindowByProduct: \$\("log-stats-failed-span-share-of-own-ok-window-by-product"\)/);
  assert.match(
    app,
    /Failure-span share of that product's own success window by product: Vigiles \$\{stats\.failedSpanShareOfOwnOkWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareOfOwnOkWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the failed-span-share-of-own-ok-window line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-span-share-of-own-ok-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-share-of-own-ok-window-by-product" class="note mono">Failure-span share of that product's own success window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
