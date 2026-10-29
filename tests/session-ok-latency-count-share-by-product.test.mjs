// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-by-product.test.mjs
//
// Hana DETAIL-45: the session-log panel gains a per-product
// usable-latency-count share line, computed only from entries
// the log actually recorded. DETAIL-35 split the latency sum
// per product, but a sum share cannot say which product
// supplied most of the measurements: a product can be slow
// on average yet supply few measurements, or fast yet supply
// most of them. This re-bases each product's DETAIL-36 usable
// ok latency count on the session's total usable ok latency
// count. The denominator is a count, not a sum: a session
// with no usable ok latency at all reads null per product
// (an empty log, a failure-only log, and a success-only log
// with no finite latency alike), and once any measurement
// exists, a product with no usable latency reads 0, never
// "none". Unlike DETAIL-35, a zero total needs no special
// case: a 0 ms latency is still a finite measurement, so it
// counts here, and a session of only 0 ms successes reads
// real shares, never null and never NaN. A success with an
// unknown or missing product moves no bucket but still sits
// in the total, so the shares sum to 1 only when every
// usable-latency success carries a known product, exactly
// as DETAIL-35's shares do. Failures never move a share,
// even a failure carrying a latency value. No sampling, no
// model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, sanitas: null };

function recordOk(log, product, latencyMs = 100) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, status = "network_error", latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status,
    error: "boom",
  });
}

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, NULL_SHARES);
});

test("a single success reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("mixed counts divide by the measurement count, not the latency sum", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", 300);
  recordOk(log, "sanitas", 100);
  // Count shares 2/4, 1/4, 1/4 — DETAIL-35's sum shares for
  // the same log would be 1/3, 1/2, 1/6.
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0.5,
    ignis: 0.25,
    sanitas: 0.25,
  });
});

test("shares sum to 1 when every usable-latency success carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordOk(log, "sanitas", 100);
  const shares = log.stats().okLatencyCountShareByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a success with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0.5,
    ignis: 0,
    sanitas: 0,
  });
});

test("a success with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 100);
  recordOk(log, null, 300);
  // Count shares: sanitas supplied 1 of 2 measurements, so
  // 0.5 — DETAIL-35's sum share for the same log is 0.25.
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: 0.5,
  });
});

test("failures never move a share, and a failure-only log reads null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, NULL_SHARES);
  recordOk(log, "ignis", 200);
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("an ok entry with no finite latency is skipped, not counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "sanitas", null);
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("a success-only log with no finite latency reads null, not zero shares", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, NULL_SHARES);
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const shares = log.stats().okLatencyCountShareByProduct;
  assert.deepEqual(shares, { vigiles: 0.5, ignis: 0.5, sanitas: 0 });
  for (const value of Object.values(shares)) {
    assert.equal(Number.isNaN(value), false);
  }
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().okLatencyCountShareByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the ok-latency-count-share-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareByProduct: \$\("log-stats-ok-latency-count-share-by-product"\)/);
  assert.match(
    app,
    /Successful latency-measurement share by product: Vigiles \$\{stats\.okLatencyCountShareByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-by-product" class="note mono">Successful latency-measurement share by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
