// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-share-of-own-entries-by-product.test.mjs
//
// Hana DETAIL-61: the session-log panel gains a
// per-product ok-count-share-of-that-product's-own-
// entries line, computed only from entries the
// log actually recorded. DETAIL-41's per-product
// shares say how much of everything recorded each
// product's successes are, but not how often that
// product itself succeeded: a product that is a
// small slice of the session can still succeed on
// three of its own four entries. This re-bases
// DETAIL-1's per-product ok counts on each
// product's own entry total, so a session where
// Vigiles succeeded on three of its own four
// entries reads 3/4 at a glance — the product's
// own success rate, the within-product re-base
// DETAIL-41's entry-total shares imply but do not
// state, continuing DETAIL-54/56/59/60's
// within-product line. Only that product's entries
// move its denominator, so other products' entries
// dilute DETAIL-41's shares without touching
// these. Null per product with no entries of that
// product at all, empty log alike — nothing to
// divide by, never NaN; 0 per product with
// entries but no successes; 1 when every entry
// of that product succeeded. Failures sit in the
// denominator but move no bucket. An unknown- or
// missing-product entry moves no bucket and no
// product denominator, unlike DETAIL-41 where it
// sits in the global denominator. Unlike the span
// shares, a single entry still divides: a single
// success reads 1, a single failure reads 0.
// No sampling, no model, no invented measurements.

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
  assert.deepEqual(log.stats().okShareOfOwnEntriesByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a failure-only product reads 0, other products stay null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats().okShareOfOwnEntriesByProduct;
  assert.equal(stats.vigiles, 0);
  assert.equal(stats.ignis, null);
  assert.equal(stats.medicus, null);
});

test("a successes-only product reads 1", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().okShareOfOwnEntriesByProduct.vigiles, 1);
});

test("mixed products read their own fractions, not their session shares", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:03:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:04:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles succeeded on 3 of its own 4 entries,
  // Ignis on 1 of its own 2 — while DETAIL-41's
  // entry-total shares read 3/6 and 1/6.
  assert.equal(stats.okShareOfOwnEntriesByProduct.vigiles, 3 / 4);
  assert.equal(stats.okShareOfOwnEntriesByProduct.ignis, 1 / 2);
  assert.equal(stats.okShareOfTotalByProduct.vigiles, 3 / 6);
  assert.equal(stats.okShareOfTotalByProduct.ignis, 1 / 6);
});

test("a single success reads 1: a count denominator is never a zero window", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().okShareOfOwnEntriesByProduct.vigiles, 1);
});

test("a single failure reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().okShareOfOwnEntriesByProduct.vigiles, 0);
});

test("an unknown-product success moves no bucket and no product denominator, unlike DETAIL-41", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:03:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles still reads 1/2: the mystery successes
  // sit in DETAIL-41's global denominator (Vigiles
  // reads 1/4 there) but move no Vigiles bucket.
  assert.equal(stats.okShareOfOwnEntriesByProduct.vigiles, 1 / 2);
  assert.equal(stats.okShareOfTotalByProduct.vigiles, 1 / 4);
});

test("a missing-product success moves no bucket and no product denominator, unlike DETAIL-41", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:03:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.okShareOfOwnEntriesByProduct.ignis, 1 / 2);
  assert.equal(stats.okShareOfTotalByProduct.ignis, 1 / 4);
});

test("an unknown-product failure moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:02:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles reads 1: the mystery failures sit in no
  // Vigiles denominator, so they cannot dilute it.
  assert.equal(stats.okShareOfOwnEntriesByProduct.vigiles, 1);
});

test("a missing-product failure moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:01:00.000Z", null);
  recordAt(log, "2026-10-29T12:02:00.000Z", null);
  assert.equal(log.stats().okShareOfOwnEntriesByProduct.ignis, 1);
});

test("the share equals the DETAIL-1 ok count over the product entry total", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:03:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.okShareOfOwnEntriesByProduct.vigiles,
    stats.byProduct.vigiles / stats.entryCountByProduct.vigiles,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().okShareOfOwnEntriesByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the ok-share-of-own-entries line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkShareOfOwnEntriesByProduct: \$\("log-stats-ok-share-of-own-entries-by-product"\)/);
  assert.match(
    app,
    /Success share of that product's own entries by product: Vigiles \$\{stats\.okShareOfOwnEntriesByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okShareOfOwnEntriesByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-share-of-own-entries line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-share-of-own-entries stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-share-of-own-entries-by-product" class="note mono">Success share of that product's own entries by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
