// Node built-in test runner, no dependencies:
//   node --test tests/session-latency-range-by-product.test.mjs
//
// Rowan DETAIL-10 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// fastest/slowest-successful-latency line, computed only from
// successes the log actually recorded. DETAIL-6 named the range over
// all successes; this splits it per product, so a session where Ignis
// successes span 50-900 ms but Vigiles successes are all near 100 ms
// reads differently from one where all three span the same range.
// Failures never contribute, an ok entry with an unknown or missing
// product moves no bucket (but still moves the global range), an ok
// entry with no finite latency is skipped rather than counted as
// zero, and a product with no usable success reads "none" — no
// sampling, no model, no invented latencies.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, product, latencyMs) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "network_error",
    error: "boom",
  });
}

const NONE = { vigiles: null, ignis: null, sanitas: null };

test("empty log: every product range is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, { ...NONE });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, { ...NONE });
});

test("ranges bucket by their own product", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 50);
  recordOk(log, "ignis", 900);
  recordOk(log, "ignis", 200);
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, {
    vigiles: 100,
    ignis: 50,
    sanitas: null,
  });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, {
    vigiles: 100,
    ignis: 900,
    sanitas: null,
  });
});

test("failures never move a bucket, even with a latency recorded", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", 5);
  recordFailed(log, "vigiles", 5000);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, {
    vigiles: null,
    ignis: 100,
    sanitas: null,
  });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, {
    vigiles: null,
    ignis: 100,
    sanitas: null,
  });
});

test("ok entries with no usable latency are skipped, not zeroed", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", null);
  recordOk(log, "ignis", Number.NaN);
  recordOk(log, "ignis", Number.POSITIVE_INFINITY);
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, { ...NONE });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, { ...NONE });
  recordOk(log, "ignis", 80);
  assert.equal(log.stats().minOkLatencyMsByProduct.ignis, 80);
  assert.equal(log.stats().maxOkLatencyMsByProduct.ignis, 80);
});

test("an ok entry with an unknown product moves no bucket but still moves the global range", () => {
  const log = new SessionLog();
  recordOk(log, "mystery", 100);
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, { ...NONE });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, { ...NONE });
  assert.equal(log.stats().minOkLatencyMs, 100);
  assert.equal(log.stats().maxOkLatencyMs, 100);
});

test("an ok entry with a missing product moves no bucket but still moves the global range", () => {
  const log = new SessionLog();
  log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: null,
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, { ...NONE });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, { ...NONE });
  assert.equal(log.stats().minOkLatencyMs, 100);
  assert.equal(log.stats().maxOkLatencyMs, 100);
});

test("a single ok entry per product gives min equal to max", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 250);
  assert.equal(log.stats().minOkLatencyMsByProduct.sanitas, 250);
  assert.equal(log.stats().maxOkLatencyMsByProduct.sanitas, 250);
  assert.equal(log.stats().minOkLatencyMsByProduct.vigiles, null);
  assert.equal(log.stats().maxOkLatencyMsByProduct.ignis, null);
});

test("ranges follow clear: back to nulls", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 50);
  recordOk(log, "ignis", 900);
  log.clear();
  assert.deepEqual(log.stats().minOkLatencyMsByProduct, { ...NONE });
  assert.deepEqual(log.stats().maxOkLatencyMsByProduct, { ...NONE });
});

test("web wiring: updateLogStats renders the per-product latency-range line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsLatencyRangeByProduct: \$\("log-stats-latency-range-by-product"\)/);
  assert.match(
    app,
    /Fastest\/slowest successful latency by product: Vigiles \$\{stats\.minOkLatencyMsByProduct\.vigiles/,
    "updateLogStats sets the per-product latency-range line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product latency-range stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-latency-range-by-product" class="note mono">Fastest\/slowest successful latency by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
