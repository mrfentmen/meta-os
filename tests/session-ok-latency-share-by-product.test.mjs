// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-share-by-product.test.mjs
//
// Rowan DETAIL-35: the session-log panel gains a per-product
// successful-latency share line, computed only from entries the
// log actually recorded. DETAIL-8 split the mean latency per
// product, but a mean alone cannot say which product ate most
// of the session's measured round-trip time: this re-bases
// each product's usable ok latency sum on the session's total
// usable ok latency sum. The denominator is the latency total,
// not a count: a session with no usable ok latency at all
// reads null per product (an empty log, a failure-only log,
// and a success-only log with no finite latency alike), and a
// session whose usable latencies sum to zero reads null too —
// a zero total has no shares to divide, never NaN. Once a
// nonzero total exists, a product with no usable latency
// reads 0, never "none". A success with an unknown or missing
// product moves no bucket but still sits in the total, so the
// shares sum to 1 only when every usable-latency success
// carries a known product, exactly as DETAIL-13's shares do.
// Failures never move a share. No sampling, no model, no
// invented measurements.

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

function recordFailed(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().okLatencyShareByProduct, NULL_SHARES);
});

test("a single success reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.deepEqual(log.stats().okLatencyShareByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("mixed latencies divide by the total latency sum, not the count", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", 300);
  recordOk(log, "sanitas", 100);
  assert.deepEqual(log.stats().okLatencyShareByProduct, {
    vigiles: 1 / 3,
    ignis: 0.5,
    sanitas: 1 / 6,
  });
});

test("shares sum to 1 when every usable-latency success carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordOk(log, "sanitas", 100);
  const shares = log.stats().okLatencyShareByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a success with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  assert.deepEqual(log.stats().okLatencyShareByProduct, {
    vigiles: 0.5,
    ignis: 0,
    sanitas: 0,
  });
});

test("a success with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 100);
  recordOk(log, null, 300);
  assert.deepEqual(log.stats().okLatencyShareByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: 0.25,
  });
});

test("failures never move a share, and a failure-only log reads null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats().okLatencyShareByProduct, NULL_SHARES);
  recordOk(log, "ignis", 200);
  assert.deepEqual(log.stats().okLatencyShareByProduct, {
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
  assert.deepEqual(log.stats().okLatencyShareByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("a success-only log with no finite latency reads null, not zero shares", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.deepEqual(log.stats().okLatencyShareByProduct, NULL_SHARES);
});

test("usable latencies summing to zero read null, never NaN", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const shares = log.stats().okLatencyShareByProduct;
  assert.deepEqual(shares, NULL_SHARES);
  for (const value of Object.values(shares)) {
    assert.equal(Number.isNaN(value), false);
  }
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().okLatencyShareByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the ok-latency-share-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyShareByProduct: \$\("log-stats-ok-latency-share-by-product"\)/);
  assert.match(
    app,
    /Successful latency share by product: Vigiles \$\{stats\.okLatencyShareByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okLatencyShareByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-share-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-share-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-share-by-product" class="note mono">Successful latency share by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
