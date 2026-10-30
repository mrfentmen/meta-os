// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-share-of-ok-window-by-product.test.mjs
//
// Hana DETAIL-70: the session-log panel gains a
// per-product entry-span-share-of-the-global-success-
// window line, computed only from entries the
// log actually recorded. DETAIL-66's global share says
// how the whole recording stretches against the
// success window, and DETAIL-68's own-ok shares say
// how each product's recording stretches against
// its own successes, but neither says how a
// product's whole recording stretches against the
// session's whole success window: a product whose
// recording ran twice the whole success window
// reads differently from one that barely outlasts
// it, even when the product's own successes are a
// small slice of all successes. This re-bases
// DETAIL-17's per-product entry spans on the
// global DETAIL-22 ok span, so a session where
// Vigiles recorded across 20 minutes while all
// successes spanned 10 minutes reads 2 at a
// glance — the entry-side companion to
// DETAIL-48's ok-span shares of the same window,
// the global-window mirror of DETAIL-68. Any
// status of that product moves its numerator, so
// a failure-only product still covers the window
// its failures stretched across, while only
// successes move the denominator. Null per
// product with no usable global ok window at all
// (empty log, failure-only log, a single success,
// or all successes at one timestamp — a zero
// global ok span has no share to divide, never
// NaN); null per product with entries but no
// usable entry timestamp pair; 0 per product
// with no entries once a nonzero ok window
// exists, and 0 per single-entry product. Raw
// ratios, never clamped: above 1 is the normal
// case, below 1 or below 0 means timestamps ran
// out of insertion order. An unknown- or
// missing-product success stretches the global
// window without moving any bucket; an unknown-
// or missing-product entry moves no bucket. No
// sampling, no model, no invented measurements.

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
  assert.deepEqual(log.stats().entrySpanShareOfOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a failure-only log reads null: no success window to divide by", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().entrySpanShareOfOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a single success reads null: a zero success window has no share to divide", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOkWindowByProduct.vigiles, null);
});

test("mixed products read their own entry span over the global success window", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles recorded 10 minutes and Ignis 20
  // minutes, while all successes span only the
  // first-to-last recorded successes, 12:00 to
  // 12:05 — 5 minutes.
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.vigiles, 2);
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.ignis, 4);
  // The shares do NOT sum to 1: product entry
  // windows overlap, and the global window is
  // first-to-last successes, not a sum.
  assert.equal(stats.entrySpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.entrySpanMsByProduct.ignis, 20 * 60 * 1000);
  assert.equal(stats.okSpanMs, 5 * 60 * 1000);
});

test("a failure-only product still covers the success window its failures stretched across", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles has no successes, but its 20-minute
  // recording covers twice the 10-minute success
  // window; Ignis recorded exactly that window.
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.vigiles, 2);
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.ignis, 1);
});

test("a product with no entries reads 0 once a nonzero success window exists", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOkWindowByProduct.medicus, 0);
});

test("a single-entry product reads 0 against a nonzero success window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.equal(log.stats().entrySpanShareOfOkWindowByProduct.vigiles, 0);
});

test("an unparseable first-entry timestamp reads null, never a fabricated window", () => {
  const log = new SessionLog();
  // The unparseable entry is a failure, so it
  // poisons only Vigiles' entry span, not the
  // global success window it never opens.
  recordAt(log, "not-a-date", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
  assert.equal(stats.entrySpanMsByProduct.vigiles, null);
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.vigiles, null);
});

test("an unknown-product success stretches the global window and dilutes every share", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles still recorded 10 minutes, but the
  // global success window now stretches 30
  // minutes, so Vigiles reads 1/3.
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.vigiles, 1 / 3);
  assert.equal(stats.okSpanMs, 30 * 60 * 1000);
  assert.equal(stats.entrySpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("an unknown-product failure moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.vigiles, 1);
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
});

test("a missing-product success stretches the global window and dilutes every share", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.ignis, 1 / 3);
  assert.equal(stats.okSpanMs, 30 * 60 * 1000);
});

test("a missing-product failure moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:30:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfOkWindowByProduct.ignis, 1);
  assert.equal(stats.okSpanMs, 10 * 60 * 1000);
});

test("a share above 1 is kept raw, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  // Entries stretch 20 minutes across a 5-minute
  // success window: the raw ratio is 4.
  assert.equal(log.stats().entrySpanShareOfOkWindowByProduct.vigiles, 4);
});

test("a negative share is kept raw when entries run out of order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  // Entries inserted late-to-early span -15
  // minutes across a 10-minute success window:
  // -3/2.
  assert.equal(log.stats().entrySpanShareOfOkWindowByProduct.vigiles, -3 / 2);
});

test("the share equals the DETAIL-17 span over the DETAIL-22 span", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.entrySpanShareOfOkWindowByProduct.vigiles,
    stats.entrySpanMsByProduct.vigiles / stats.okSpanMs,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().entrySpanShareOfOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the entry-span-share-of-ok-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanShareOfOkWindowByProduct: \$\("log-stats-entry-span-share-of-ok-window-by-product"\)/);
  assert.match(
    app,
    /Entry-span share of success window by product: Vigiles \$\{stats\.entrySpanShareOfOkWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.entrySpanShareOfOkWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the entry-span-share-of-ok-window line from stats()",
  );
});

test("web wiring: session-log panel holds the entry-span-share-of-ok-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-share-of-ok-window-by-product" class="note mono">Entry-span share of success window by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
