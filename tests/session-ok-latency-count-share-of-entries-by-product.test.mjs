// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-of-entries-by-product.test.mjs
//
// Hana DETAIL-47: the session-log panel gains a per-product
// usable-latency-count share of all entries line, computed
// only from entries the log actually recorded. DETAIL-45
// split the measurement count per product over the
// measurement total, but a measurement-total share cannot
// say what slice of everything recorded a product's
// measurements are: a product supplying most measurements
// in a quiet session reads differently from one supplying
// most measurements in a session full of failures and
// latency-less successes. This re-bases each product's
// DETAIL-36 usable ok latency count on the session's total
// entry count. The denominator is the entry total, not the
// measurement count, so the null rule differs from
// DETAIL-45 on purpose: an empty log reads null per
// product (nothing to divide by), but once the log holds
// any entry, a product with no usable latency reads 0,
// never "none" — a failure-only log and a success-only
// log with no finite latency alike read 0% per product,
// where DETAIL-45 reads null for both. A success with an
// unknown or missing product moves no bucket but still
// sits in the total, so the shares sum to the global
// usable-latency-count share of entries only when every
// usable-latency success carries a known product.
// Failures never move a share, even a failure carrying a
// latency value, and an ok entry with no finite latency
// is skipped as a measurement but still sits in the
// denominator as an entry. A 0 ms latency still counts
// as a measurement, exactly as in DETAIL-45. No sampling,
// no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, medicus: null };

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
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, NULL_SHARES);
});

test("a single success reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("shares divide by the entry total, not the measurement count", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", 300);
  recordOk(log, "medicus", 100);
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  // Measurement counts 2/1/1 over 6 entries — DETAIL-45's
  // measurement-total shares for the same log would be
  // 1/2, 1/4, 1/4.
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 1 / 3,
    ignis: 1 / 6,
    medicus: 1 / 6,
  });
});

test("a latency-less success sits in the denominator but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", 200);
  recordFailed(log, "medicus");
  // DETAIL-41's ok-count shares here would be vigiles 1/2;
  // the latency-count shares are vigiles 1/4, ignis 1/4.
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0.25,
    ignis: 0.25,
    medicus: 0,
  });
});

test("shares sum to the global usable-latency-count share when every usable-latency success carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordFailed(log, "medicus");
  const shares = log.stats().okLatencyCountShareOfEntriesByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 2 / 3);
  assert.equal(sum, log.stats().okLatencyCount / log.stats().total);
});

test("a success with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
});

test("a success with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "medicus", 100);
  recordOk(log, null, 300);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0.5,
  });
});

test("failures never move a share, and a failure-only log reads 0, not null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0,
  });
  recordOk(log, "ignis", 200);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 0.5,
    medicus: 0,
  });
});

test("an ok entry with no finite latency is skipped as a measurement but counts as an entry", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "medicus", null);
  // DETAIL-45 for the same log would read ignis 1; here
  // the entry total is 3, so ignis reads 1/3.
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("a success-only log with no finite latency reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0,
  });
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const shares = log.stats().okLatencyCountShareOfEntriesByProduct;
  assert.deepEqual(shares, { vigiles: 0.5, ignis: 0.5, medicus: 0 });
  for (const value of Object.values(shares)) {
    assert.equal(Number.isNaN(value), false);
  }
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the ok-latency-count-share-of-entries-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareOfEntriesByProduct: \$\("log-stats-ok-latency-count-share-of-entries-by-product"\)/);
  assert.match(
    app,
    /Successful latency-measurement share of all entries by product: Vigiles \$\{stats\.okLatencyCountShareOfEntriesByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfEntriesByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-of-entries-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-of-entries-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-of-entries-by-product" class="note mono">Successful latency-measurement share of all entries by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
