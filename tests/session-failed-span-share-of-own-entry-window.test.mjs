// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-of-own-entry-window.test.mjs
//
// Hana DETAIL-59 (renumbered after Rowan's distinct DETAIL-58 landed first, both sides kept in the merge): the session-log panel gains a
// per-product failed-span-share-of-that-product's-own-
// entry-window line, computed only from entries the
// log actually recorded. DETAIL-55's per-product
// shares say how much of the session's whole recording
// window each product's failures cover, but not how
// much of that product's own recorded activity its
// failures cover: a product that is a small slice of
// the session can still fail across half of everything
// it recorded. This re-bases DETAIL-20's per-product
// failed span on that product's own DETAIL-17 entry
// span, so a session where Vigiles failures stretch
// across half of everything Vigiles recorded reads
// that at a glance — the within-product re-base
// DETAIL-55's global-entry shares imply but do not
// state, and the failed mirror of the own-window
// slice DETAIL-56 gives the latency counts. Only
// that product's entries move its denominator's
// endpoints, so other products' entries stretch
// DETAIL-55's global window without touching these.
// These are raw ratios, never clamped, and a share
// above 1 or below 0 means timestamps ran out of
// insertion order, exactly as DETAIL-20's raw spans
// do. Null per product with no usable own entry
// window at all — no entries of that product, a
// single entry of that product, or all of that
// product's entries at one timestamp — because a
// zero own entry span has no share to divide, never
// NaN; null per product whose own failed span is
// unknown (failures recorded but no usable timestamp
// pair — never a fabricated window); 0 per product
// with no failures once a nonzero own entry window
// exists, because failures covered none of its own
// window, and 0 per single-failure product, whose
// zero-length failed window covers none of a nonzero
// own window. An unknown- or missing-product failure
// moves no bucket and no product denominator, unlike
// DETAIL-57's product-blind global. No sampling,
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
  assert.deepEqual(log.stats().failedSpanShareOfOwnEntryWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a single entry reads null: a zero own entry span has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().failedSpanShareOfOwnEntryWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("all of a product's entries at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  assert.deepEqual(log.stats().failedSpanShareOfOwnEntryWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("other products' entries do not move a product's own-window share, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles own window is 11:00 to 12:10 = 4200000 ms;
  // its failed span covers 600000 of it. DETAIL-55's
  // Vigiles share divides by the global 11:00-13:00
  // window instead and reads 600000 / 7200000.
  assert.equal(stats.failedSpanShareOfOwnEntryWindowByProduct.vigiles, 600000 / 4200000);
  assert.equal(stats.failedSpanShareOfEntryWindowByProduct.vigiles, 600000 / 7200000);
  // Ignis recorded a single entry, so its own window
  // is zero and its own-window share is null, even
  // though the Ignis entry stretched the global
  // window DETAIL-55 divides by.
  assert.equal(stats.failedSpanShareOfOwnEntryWindowByProduct.ignis, null);
});

test("a failures-only product reads 1: its failed span is its whole own window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanShareOfOwnEntryWindowByProduct.vigiles, 1);
});

test("no failures once a nonzero own entry window exists reads 0, not null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats().failedSpanShareOfOwnEntryWindowByProduct;
  assert.equal(stats.vigiles, 0);
  assert.equal(stats.ignis, null);
  assert.equal(stats.sanitas, null);
});

test("a single failure inside a nonzero own entry window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOwnEntryWindowByProduct.vigiles, 0);
});

test("an unknown-product failure moves no bucket and no product denominator, unlike DETAIL-57", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:10:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  const stats = log.stats();
  // Vigiles recorded no failures, so its own-window
  // share is 0 even though the session's product-blind
  // DETAIL-57 share is moved by the mystery failures.
  assert.equal(stats.failedSpanShareOfOwnEntryWindowByProduct.vigiles, 0);
  assert.equal(stats.failedSpanShareOfEntryWindow, 600000 / 7200000);
});

test("a missing-product failure moves no bucket and no product denominator, unlike DETAIL-57", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:10:00.000Z", null);
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "ignis");
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOwnEntryWindowByProduct.ignis, 0);
  assert.equal(stats.failedSpanShareOfEntryWindow, 600000 / 7200000);
});

test("failures with no usable timestamp pair read null, distinct from a no-failure product's 0", () => {
  const log = new SessionLog();
  recordAt(log, "", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  const stats = log.stats().failedSpanShareOfOwnEntryWindowByProduct;
  // A Vigiles failure was recorded but its failed
  // window is unknown — null, never a fabricated 0 —
  // while Ignis, with no failures at all, reads 0.
  assert.equal(stats.vigiles, null);
  assert.equal(stats.ignis, 0);
});

test("out-of-order timestamps stay raw: the share can go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  // Vigiles own window: first recorded entry 12:10 to
  // last recorded entry 12:20 = 600000 ms. Vigiles
  // failed span: 12:10 back to 12:00 = -600000 (-1 of
  // its own window).
  assert.equal(log.stats().failedSpanShareOfOwnEntryWindowByProduct.vigiles, -1);
});

test("out-of-order timestamps stay raw: the share can exceed 1, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Vigiles own window: first recorded entry 12:00 to
  // last recorded entry 12:10 = 600000 ms, but the
  // Vigiles failed span runs 12:00 to 12:30 =
  // 1800000 ms, so the share reads 3 — the honest
  // reading of a window whose last recorded entry
  // carries an earlier timestamp.
  assert.equal(log.stats().failedSpanShareOfOwnEntryWindowByProduct.vigiles, 3);
});

test("the share equals the DETAIL-20 span over the DETAIL-17 span, per product", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.failedSpanShareOfOwnEntryWindowByProduct.vigiles,
    stats.failedSpanMsByProduct.vigiles / stats.entrySpanMsByProduct.vigiles,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedSpanShareOfOwnEntryWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the failed-span-share-of-own-entry-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareOfOwnEntryWindowByProduct: \$\("log-stats-failed-span-share-of-own-entry-window-by-product"\)/);
  assert.match(
    app,
    /Failure-span share of that product's own entry window by product: Vigiles \$\{stats\.failedSpanShareOfOwnEntryWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareOfOwnEntryWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the failed-span-share-of-own-entry-window line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-span-share-of-own-entry-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-share-of-own-entry-window-by-product" class="note mono">Failure-span share of that product's own entry window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
