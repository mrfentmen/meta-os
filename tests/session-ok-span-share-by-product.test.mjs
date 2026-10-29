// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-span-share-by-product.test.mjs
//
// ROWAN DETAIL-48: the session-log panel gains a per-product
// ok-span-share-of-ok-window line, computed only from
// entries the log actually recorded. DETAIL-21's per-product
// ok spans say how long each product's successes stretch,
// but not how much of the session's whole ok window each
// product covers: a product can succeed twice in a
// one-minute burst inside an hour-long ok window. This
// re-bases DETAIL-21's per-product ok spans on the session's
// global ok span (DETAIL-22), so each product's ok-window
// coverage reads at a glance — the ok-only companion to
// DETAIL-46's any-status entry-span shares. The denominator
// is the global first-to-last ok window, not a sum of
// product ok windows, so these are raw ratios, never
// clamped, and they do NOT sum to 1: product ok windows
// overlap, and a share above 1 or below 0 means timestamps
// ran out of insertion order, exactly as DETAIL-21's raw
// spans do. Only successes move the endpoints, so failures
// move neither a bucket nor the global ok window, and an ok
// entry with an unknown or missing product moves no product
// bucket but still stretches the global window, so it
// dilutes every share without moving any bucket. Null per
// product when the session holds no usable ok window at
// all — an empty log, a failure-only log, a single success,
// or all successes at one timestamp — because a zero
// global ok span has no shares to divide, never NaN; null
// per product whose own ok span is unknown (successes
// recorded but no usable timestamp pair — never a
// fabricated window); 0 per product with no successes once
// a nonzero ok window exists, because it covered none of
// the window, and 0 per single-success product, whose
// zero-length window covers none of a nonzero window. No
// sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, sanitas: null };

function recordAt(log, timestamp, product, status = "ok") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

test("empty log: every share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().okSpanShareByProduct, NULL_SHARES);
});

test("a single success reads null: a zero global ok span has no shares to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().okSpanShareByProduct, NULL_SHARES);
});

test("all successes at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.deepEqual(log.stats().okSpanShareByProduct, NULL_SHARES);
});

test("a failure-only log reads null: no ok window exists at all", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles", "network_error");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis", "http_error");
  assert.deepEqual(log.stats().okSpanShareByProduct, NULL_SHARES);
});

test("mixed windows divide by the global ok window, and a product with no successes reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Global ok window is 600000 ms (first recorded success
  // 12:00 to last recorded success 12:10); ignis covers
  // 330000 of it. Sanitas recorded no success, so it
  // covered none of the window — 0, not "none".
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: 1,
    ignis: 0.55,
    sanitas: 0,
  });
});

test("a single-success product inside a nonzero ok window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: 1,
    ignis: 0,
    sanitas: 0,
  });
});

test("an unknown-product success stretches the global ok window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "mystery");
  // Global ok window is now 1200000 ms; vigiles still spans
  // 600000 of it, and no product bucket moved.
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: 0.5,
    ignis: 0,
    sanitas: 0,
  });
});

test("a missing-product success stretches the global ok window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:20:00.000Z", null);
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: 0,
    ignis: 0.5,
    sanitas: 0,
  });
});

test("out-of-order timestamps stay raw: shares can exceed 1 and go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  // Global ok window: first recorded success 12:10 to last
  // recorded success 12:20 = 600000 ms. Vigiles spans 12:10
  // back to 12:00 = -600000 (-1 of the window); ignis spans
  // 12:20 alone = 0. The shares do not sum to 1, and that
  // is the honest reading.
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: -1,
    ignis: 0,
    sanitas: 0,
  });
});

test("a product with successes but no usable timestamp pair reads null, distinct from a no-success product's 0", () => {
  const log = new SessionLog();
  recordAt(log, "", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  // Vigiles recorded successes but no usable timestamps, so
  // its ok window is unknown — null, never a fabricated 0 —
  // while sanitas, with no successes at all, covered none
  // of the window and reads 0.
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: null,
    ignis: 1,
    sanitas: 0,
  });
});

test("failures never move a share, even outside the ok window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T11:00:00.000Z", "ignis", "network_error");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T13:00:00.000Z", "ignis", "http_error");
  // Unlike DETAIL-46, failures do not stretch the window:
  // the global ok window stays 600000 ms, vigiles covers
  // all of it, and failure-only ignis reads 0, not null.
  assert.deepEqual(log.stats().okSpanShareByProduct, {
    vigiles: 1,
    ignis: 0,
    sanitas: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().okSpanShareByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the ok-span-share line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkSpanShareByProduct: \$\("log-stats-ok-span-share-by-product"\)/);
  assert.match(
    app,
    /Success-span share of ok window by product: Vigiles \$\{stats\.okSpanShareByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okSpanShareByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-span-share line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-span-share stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-span-share-by-product" class="note mono">Success-span share of ok window by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
