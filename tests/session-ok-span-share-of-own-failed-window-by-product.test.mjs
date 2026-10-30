// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-span-share-of-own-failed-window-by-product.test.mjs
//
// Hana DETAIL-63: the session-log panel gains a
// per-product ok-span-share-of-that-product's-own-
// failure-window line, computed only from entries the
// log actually recorded. DETAIL-62's per-product
// shares say how failures stretch against successes
// alone, but neither DETAIL-62 nor DETAIL-59/60 says
// how successes stretch against failures alone: a
// product whose successes stretch across half of
// everything it failed across reads differently from
// one whose successes sit inside a short failure
// window. This re-bases DETAIL-21's per-product ok
// spans on each product's own DETAIL-20 failed span,
// so a session where Vigiles successes stretch 5
// minutes across a 10-minute Vigiles failure window
// reads 1/2 at a glance — the mirror of DETAIL-62,
// the cross-span within-product slice DETAIL-59/60's
// own-entry shares imply but do not state from the
// other side. Only that product's failures move its
// denominator, so other products' failures stretch
// no share here. Null per product with no usable
// own failure window at all (no failures, a single
// failure, or all failures at one timestamp — a
// zero own failed span has no share to divide, never
// NaN or Infinity); null per product with successes
// but no usable ok timestamp pair; 0 per product
// with no successes once a nonzero failure window
// exists, and 0 per single-success product. Raw
// ratios, never clamped: above 1 or below 0 means
// timestamps ran out of insertion order. An unknown-
// or missing-product entry moves no bucket and no
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
  assert.deepEqual(log.stats().okSpanShareOfOwnFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a success-only product reads null: no failure window to divide by", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats().okSpanShareOfOwnFailedWindowByProduct;
  assert.equal(stats.vigiles, null);
  assert.equal(stats.ignis, null);
  assert.equal(stats.medicus, null);
});

test("a failure-only product with a real window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfOwnFailedWindowByProduct.vigiles, 0);
});

test("a single failure reads null: a zero failed span has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:09:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfOwnFailedWindowByProduct.vigiles, null);
});

test("mixed products read their own ok span over their own failed span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:04:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:03:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles successes stretch 5 minutes across a
  // 10-minute failure window; Ignis successes stretch
  // 2 minutes across a 4-minute failure window.
  assert.equal(stats.okSpanShareOfOwnFailedWindowByProduct.vigiles, 1 / 2);
  assert.equal(stats.okSpanShareOfOwnFailedWindowByProduct.ignis, 1 / 2);
  // Cross-check against the spans themselves.
  assert.equal(stats.okSpanMsByProduct.vigiles, 5 * 60 * 1000);
  assert.equal(stats.failedSpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("a single success reads 0 once a nonzero failure window exists", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfOwnFailedWindowByProduct.vigiles, 0);
});

test("a success with no usable timestamp reads null, never a fabricated window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, undefined, "vigiles");
  assert.equal(log.stats().okSpanShareOfOwnFailedWindowByProduct.vigiles, null);
});

test("an unknown-product failure moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  const stats = log.stats();
  // Vigiles still reads 1/2: the mystery failures
  // stretch no Vigiles window.
  assert.equal(stats.okSpanShareOfOwnFailedWindowByProduct.vigiles, 1 / 2);
  assert.equal(stats.failedSpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("an unknown-product success moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles reads 0: the mystery successes stretch no
  // Vigiles ok span, so they cannot move it.
  assert.equal(stats.okSpanShareOfOwnFailedWindowByProduct.vigiles, 0);
  assert.equal(stats.okSpanMsByProduct.vigiles, null);
});

test("a missing-product entry moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:10:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.okSpanShareOfOwnFailedWindowByProduct.ignis, 0);
  assert.equal(stats.failedSpanMsByProduct.ignis, 10 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.ignis, null);
});

test("a share above 1 is kept raw, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:06:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Successes stretch 10 minutes across a 1-minute
  // failure window: the raw ratio is 10.
  assert.equal(log.stats().okSpanShareOfOwnFailedWindowByProduct.vigiles, 10);
});

test("a negative share is kept raw when successes run out of order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:09:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  // Successes inserted late-to-early span -8 minutes
  // across a 10-minute failure window: -4/5.
  assert.equal(log.stats().okSpanShareOfOwnFailedWindowByProduct.vigiles, -4 / 5);
});

test("the share equals the DETAIL-21 span over the DETAIL-20 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.okSpanShareOfOwnFailedWindowByProduct.vigiles,
    stats.okSpanMsByProduct.vigiles / stats.failedSpanMsByProduct.vigiles,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().okSpanShareOfOwnFailedWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the ok-span-share-of-own-failed-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkSpanShareOfOwnFailedWindowByProduct: \$\("log-stats-ok-span-share-of-own-failed-window-by-product"\)/);
  assert.match(
    app,
    /Success-span share of that product's own failure window by product: Vigiles \$\{stats\.okSpanShareOfOwnFailedWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okSpanShareOfOwnFailedWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-span-share-of-own-failed-window line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-span-share-of-own-failed-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-span-share-of-own-failed-window-by-product" class="note mono">Success-span share of that product's own failure window by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
