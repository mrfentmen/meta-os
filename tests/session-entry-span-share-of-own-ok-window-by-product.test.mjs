// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-share-of-own-ok-window-by-product.test.mjs
//
// Rowan DETAIL-68: the session-log panel gains a
// per-product entry-span-share-of-that-product's-own-
// success-window line, computed only from entries the
// log actually recorded. DETAIL-66 reads the whole
// recording window against the whole success window;
// its within-product re-base reads each product's own
// recording window against that product's own success
// window, so a session where Vigiles recording stretches
// twice as long as Vigiles successes alone reads that
// at a glance even when Vigiles successes are a small
// slice of the session, and a product whose every entry
// succeeded reads 1 whatever its share of the session.
// This re-bases DETAIL-17's per-product entry spans on
// each product's own DETAIL-21 ok span — the entry-side
// mirror of DETAIL-62's failed-span share of the same
// own success window. Only that product's entries move
// its numerator and only its successes move its
// denominator, so other products' entries stretch no
// share here. Null per product with no usable own
// success window at all (no successes, a single success,
// or all successes at one timestamp — a zero own ok
// span has no share to divide, never NaN); null per
// product whose own entry span is unknown (no usable
// timestamp pair — never a fabricated window); 0 per
// product whose own entry span is 0 once a nonzero own
// success window exists, reachable only when that
// product's entries were recorded out of timestamp
// order. Raw ratios, never clamped: above 1 is the
// normal case, since a product's recording outlasts its
// successes, and below 1 or below 0 means timestamps
// ran out of insertion order. An unknown- or
// missing-product entry moves no bucket and no product
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
  assert.deepEqual(log.stats().entrySpanShareOfOwnOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a single success reads null: a zero own ok span has no share to divide", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOwnOkWindowByProduct.vigiles, null);
});

test("all successes at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOwnOkWindowByProduct.vigiles, null);
});

test("a failure-only product reads null: no success window exists at all", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOwnOkWindowByProduct.vigiles, null);
});

test("mixed products read their own entry span over their own ok span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:03:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:04:00.000Z", "ignis");
  const stats = log.stats();
  // Vigiles recording stretches 10 minutes against a
  // 5-minute success window; Ignis recording stretches
  // 4 minutes against a 2-minute success window.
  assert.equal(stats.entrySpanShareOfOwnOkWindowByProduct.vigiles, 2);
  assert.equal(stats.entrySpanShareOfOwnOkWindowByProduct.ignis, 2);
  // Cross-check against the spans themselves.
  assert.equal(stats.entrySpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.vigiles, 5 * 60 * 1000);
});

test("exactly 1 when every entry of the product succeeded spanning its whole recording", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOwnOkWindowByProduct.vigiles, 1);
});

test("a negative share is kept raw when successes run out of order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:09:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "vigiles");
  // Entries run 12:00 to 12:01 (1 minute) while successes
  // inserted late-to-early span -8 minutes: -1/8.
  assert.equal(log.stats().entrySpanShareOfOwnOkWindowByProduct.vigiles, -1 / 8);
});

test("a zero entry span reads 0 once a nonzero own success window exists", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  // First entry 12:00, last recorded entry 12:00: the
  // entry span is 0 (insertion order, not timestamp
  // order) against a 10-minute success window.
  assert.equal(log.stats().entrySpanShareOfOwnOkWindowByProduct.vigiles, 0);
});

test("an unknown-product entry moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T14:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T13:30:00.000Z", "mystery");
  const stats = log.stats();
  // Vigiles still reads 2: the mystery entries stretch
  // no Vigiles window.
  assert.equal(stats.entrySpanShareOfOwnOkWindowByProduct.vigiles, 2);
  assert.equal(stats.entrySpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.okSpanMsByProduct.vigiles, 5 * 60 * 1000);
});

test("a missing-product entry moves no bucket and no product denominator", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T11:00:00.000Z", null);
  recordAt(log, "2026-10-29T14:00:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfOwnOkWindowByProduct.vigiles, 2);
  assert.equal(stats.entrySpanMsByProduct.vigiles, 10 * 60 * 1000);
});

test("an unparseable first entry timestamp reads null, never a fabricated span", () => {
  const log = new SessionLog();
  recordAt(log, "not-a-date", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  // The ok window is a real 10 minutes, but the entry
  // span is unknown: the unparseable first entry
  // timestamp poisons it alone.
  assert.equal(stats.okSpanMsByProduct.vigiles, 10 * 60 * 1000);
  assert.equal(stats.entrySpanMsByProduct.vigiles, null);
  assert.equal(stats.entrySpanShareOfOwnOkWindowByProduct.vigiles, null);
});

test("the share equals the DETAIL-17 span over the DETAIL-21 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:02:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:07:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(
    stats.entrySpanShareOfOwnOkWindowByProduct.vigiles,
    stats.entrySpanMsByProduct.vigiles / stats.okSpanMsByProduct.vigiles,
  );
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:09:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().entrySpanShareOfOwnOkWindowByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the entry-span-share-of-own-ok-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanShareOfOwnOkWindowByProduct: \$\("log-stats-entry-span-share-of-own-ok-window-by-product"\)/);
  assert.match(
    app,
    /Entry-span share of that product's own success window by product: Vigiles \$\{stats\.entrySpanShareOfOwnOkWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.entrySpanShareOfOwnOkWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the entry-span-share-of-own-ok-window line from stats()",
  );
});

test("web wiring: session-log panel holds the entry-span-share-of-own-ok-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-share-of-own-ok-window-by-product" class="note mono">Entry-span share of that product's own success window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
