// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-by-product.test.mjs
//
// Rowan DETAIL-20 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// failure-span line, computed only from entries the log actually
// recorded. Each product's span is the milliseconds between its
// DETAIL-19 first failure and its DETAIL-7 last failure — how long
// that product's failures stretch, where the two endpoint lines
// alone do not say it at a glance. Derived only from those two
// buckets, so the same bucket rules apply: successes never move a
// bucket, a failure with an unknown or missing product moves no
// bucket, and a failure without a usable timestamp leaves both
// endpoints in place. A product with exactly one usable failure
// reads 0, not null — one failure spans no time. An unparseable
// endpoint reads null, never NaN, and the difference is kept raw,
// not clamped: a negative span means failures were recorded out of
// timestamp order, which the insertion-order endpoints preserve
// honestly. Null per product with no usable failure pair, never a
// fabricated span. No sampling, no model, no invented products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordAt(log, timestamp, product, status = "network_error") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

const NULLS = { vigiles: null, ignis: null, sanitas: null };

test("empty log: every product failure span is null, not a fabricated span", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedSpanMsByProduct, { ...NULLS });
});

test("span is last minus first failure per product, in whole milliseconds", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.500Z", "ignis");
  assert.deepEqual(log.stats().failedSpanMsByProduct, {
    vigiles: 300000,
    ignis: 330500,
    sanitas: null,
  });
});

test("a product with exactly one usable failure reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.deepEqual(log.stats().failedSpanMsByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: 0,
  });
});

test("successes between failures never move the span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis", "ok");
  recordAt(log, "2026-10-29T12:04:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanMsByProduct.ignis, 240000);
  assert.equal(log.stats().firstFailedAtByProduct.ignis, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastFailedAtByProduct.ignis, "2026-10-29T12:04:00.000Z");
});

test("a product with no failure in a non-empty session reads null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:03:00.000Z", "sanitas", "ok");
  assert.deepEqual(log.stats().failedSpanMsByProduct, {
    vigiles: 0,
    ignis: null,
    sanitas: null,
  });
});

test("insertion order, not min/max: a later failure with an earlier timestamp reads a negative span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.equal(log.stats().failedSpanMsByProduct.sanitas, -300000);
});

test("a failure with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.deepEqual(log.stats().failedSpanMsByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("failures with a missing product move no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", null);
  assert.deepEqual(log.stats().failedSpanMsByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("a failure without a usable timestamp leaves the span in place", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: null,
    status: "network_error",
    error: "boom",
  });
  assert.equal(log.stats().failedSpanMsByProduct.ignis, 300000);
});

test("an unparseable endpoint timestamp reads null, never NaN", () => {
  const log = new SessionLog();
  recordAt(log, "not-a-timestamp", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanMsByProduct.ignis, null);
  assert.equal(log.stats().firstFailedAtByProduct.ignis, "not-a-timestamp");
});

test("failure spans follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedSpanMsByProduct, { ...NULLS });
});

test("web wiring: updateLogStats renders the per-product failure-span line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanByProduct: \$\("log-stats-failed-span-by-product"\)/);
  assert.match(
    app,
    /Failure span by product: Vigiles \$\{stats\.failedSpanMsByProduct\.vigiles === null \? "none" : `\$\{stats\.failedSpanMsByProduct\.vigiles\} ms`\}/,
    "updateLogStats sets the per-product failure-span line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product failure-span stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-by-product" class="note mono">Failure span by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
