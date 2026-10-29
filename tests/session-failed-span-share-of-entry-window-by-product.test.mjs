// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-of-entry-window-by-product.test.mjs
//
// ROWAN DETAIL-55: the session-log panel gains a per-product
// failed-span-share-of-entry-window line, computed only from
// entries the log actually recorded. DETAIL-20's per-product
// failed spans say how long each product's failures stretch,
// but not how much of the session's whole recording window
// each product covers: a product can fail twice in a
// one-minute burst inside an hour-long session. This
// re-bases DETAIL-20's per-product failed spans on the
// session's global entry span (DETAIL-24), so each product's
// failure-window coverage of the whole session reads at a
// glance — the failed mirror of DETAIL-53's ok-span shares,
// and the entry-window re-basing of DETAIL-50's
// failed-window shares. The denominator is the global
// first-to-last entry window, not a sum of product failed
// windows, so these are raw ratios, never clamped, and they
// do NOT sum to 1: product failed windows overlap, and a
// share above 1 or below 0 means timestamps ran out of
// insertion order, exactly as DETAIL-20's raw spans do. Any
// entry moves the denominator's endpoints, so successes and
// unknown- or missing-product entries stretch the global
// window without moving any bucket, diluting every share,
// while only failures move a bucket. Null per product when
// the session holds no usable entry window at all — an empty
// log, a single entry, or all entries at one timestamp —
// because a zero global entry span has no shares to divide,
// never NaN; null per product whose own failed span is
// unknown (failures recorded but no usable timestamp pair —
// never a fabricated window); 0 per product with no
// failures once a nonzero entry window exists, because it
// covered none of the window, and 0 per single-failure
// product, whose zero-length window covers none of a
// nonzero window. No sampling, no model, no invented
// measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, sanitas: null };

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

test("empty log: every share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, NULL_SHARES);
});

test("a single entry reads null: a zero global entry span has no shares to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, NULL_SHARES);
});

test("all entries at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, NULL_SHARES);
});

test("mixed windows divide by the global entry window, and a product with no failures reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "sanitas");
  // Global entry window is 1200000 ms (first recorded
  // entry 12:00 to last recorded entry 12:20); vigiles
  // failed span covers 600000 of it, ignis a single
  // failure covers none. Sanitas recorded no failure, so
  // it covered none of the window — 0, not "none".
  // Unlike DETAIL-50, the denominator here is the entry
  // window, so the success at 12:20 stretches it.
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: 0.5,
    ignis: 0,
    sanitas: 0,
  });
});

test("a single-failure product inside a nonzero entry window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: 1,
    ignis: 0,
    sanitas: 0,
  });
});

test("an unknown-product entry stretches the global entry window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "mystery");
  // Global entry window is now 1200000 ms; vigiles still
  // spans 600000 of it, and no product bucket moved.
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: 0.5,
    ignis: 0,
    sanitas: 0,
  });
});

test("a missing-product entry stretches the global entry window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", null);
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: 0,
    ignis: 0.5,
    sanitas: 0,
  });
});

test("out-of-order timestamps stay raw: shares can exceed 1 and go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  // Global entry window: first recorded entry 12:10 to
  // last recorded entry 12:20 = 600000 ms. Vigiles spans
  // 12:10 back to 12:00 = -600000 (-1 of the window); ignis
  // has no failures, so 0. The shares do not sum to 1,
  // and that is the honest reading.
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: -1,
    ignis: 0,
    sanitas: 0,
  });
});

test("a product with failures but no usable timestamp pair reads null, distinct from a no-failure product's 0", () => {
  const log = new SessionLog();
  recordAt(log, "", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  // Vigiles recorded a failure but no usable timestamps, so
  // its failed window is unknown — null, never a fabricated
  // 0 — while ignis and sanitas, with no failures at all,
  // covered none of the window and read 0.
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: null,
    ignis: 0,
    sanitas: 0,
  });
});

test("successes stretch the denominator without moving any bucket, unlike DETAIL-50", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "ignis");
  // Global entry window is 7200000 ms (11:00 to 13:00);
  // vigiles failed span covers 600000 of it. Under
  // DETAIL-50 the denominator would be the 600000 ms
  // failed window and vigiles would read 1; here the
  // successes stretch it.
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: 600000 / 7200000,
    ignis: 0,
    sanitas: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failed-span-share-of-entry-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareOfEntryWindowByProduct: \$\("log-stats-failed-span-share-of-entry-window-by-product"\)/);
  assert.match(
    app,
    /Failure-span share of entry window by product: Vigiles \$\{stats\.failedSpanShareOfEntryWindowByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareOfEntryWindowByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the failed-span-share-of-entry-window line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-span-share-of-entry-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-share-of-entry-window-by-product" class="note mono">Failure-span share of entry window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
