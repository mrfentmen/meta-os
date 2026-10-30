// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-of-ok-by-product.test.mjs
//
// Hana DETAIL-52: the session-log panel gains a per-product
// usable-latency-count share of ok successes line,
// computed only from entries the log actually recorded.
// DETAIL-51 collapsed the measurement count over the ok
// total into one global share, but a global share cannot
// say which product supplied the measurements: a session
// where Vigiles measurements are half of all successes
// reads differently from one where Ignis supplied them.
// This splits DETAIL-51's share by product, reusing
// DETAIL-37's shareOfAllOk helper. The denominator is the
// session ok total, not the entry total and not the
// measurement count, so the null rule differs from
// DETAIL-47 on purpose: an empty log and a failure-only
// log alike read null per product (nothing to divide
// by), but once the session holds any success, a product
// with no usable latency reads 0, never "none" — a
// success-only log with no finite latency reads 0 per
// product. Failures sit in neither side: they are not in
// the ok total and never count as measurements, even a
// failure carrying a latency value. An ok entry with no
// finite latency sits in the denominator but moves no
// bucket, and an unknown- or missing-product success
// sits in the denominator but moves no bucket either, so
// the three shares sum to DETAIL-51's global share only
// when every usable-latency success carries a known
// product. A 0 ms latency still counts as a measurement,
// exactly as in DETAIL-45/47/49/51. No sampling, no
// model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

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

test("empty log: the per-product shares are null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a single success reads 1 for its product, 0 for the others", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("the shares divide by the ok total, not the entry total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", null);
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  // Two Vigiles measurements over three successes — DETAIL-47's
  // entry-total shares for the same log would be 2/5 and 0,
  // and DETAIL-45's measurement-total shares would be 1 and 0.
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 2 / 3,
    ignis: 0,
    medicus: 0,
  });
  assert.equal(log.stats().okLatencyCountShareOfOk, 2 / 3);
});

test("a latency-less success sits in the denominator but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", 200);
  recordFailed(log, "medicus");
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 1 / 3,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("the shares equal the DETAIL-36 counts over the ok total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordOk(log, "medicus", null);
  recordFailed(log, "medicus");
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountShareOfOkByProduct, {
    vigiles: 1 / 3,
    ignis: 1 / 3,
    medicus: 0,
  });
  assert.equal(
    stats.okLatencyCountShareOfOkByProduct.vigiles,
    stats.okLatencyCountByProduct.vigiles / stats.ok,
  );
  assert.equal(
    stats.okLatencyCountShareOfOkByProduct.ignis,
    stats.okLatencyCountByProduct.ignis / stats.ok,
  );
});

test("an unknown-product success moves the denominator but no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  // The global DETAIL-51 share reads 1, but the buckets sum
  // to only 1/2: the mystery measurement sits in the ok
  // total and moves no bucket.
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountShareOfOkByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
  assert.equal(stats.okLatencyCountShareOfOk, 1);
});

test("a missing-product success moves the denominator but no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "medicus", 100);
  recordOk(log, null, null);
  // One Medicus measurement over two successes.
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0.5,
  });
});

test("a failure-only log reads null, not 0 — unlike DETAIL-47", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("an ok entry with no finite latency is skipped as a measurement but counts as a success", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "medicus", null);
  // DETAIL-45 for the same log would read 1 for Ignis;
  // here the ok total is 3, so Ignis reads 1/3.
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 0,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("a success-only log with no finite latency reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0,
  });
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const shares = log.stats().okLatencyCountShareOfOkByProduct;
  assert.deepEqual(shares, { vigiles: 0.5, ignis: 0.5, medicus: 0 });
  assert.equal(Number.isNaN(shares.vigiles), false);
});

test("the shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().okLatencyCountShareOfOkByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the ok-latency-count-share-of-ok-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareOfOkByProduct: \$\("log-stats-ok-latency-count-share-of-ok-by-product"\)/);
  assert.match(
    app,
    /Successful latency-measurement share of successes by product: Vigiles \$\{stats\.okLatencyCountShareOfOkByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOkByProduct\.vigiles \* 100\)\}%`\} · Ignis \$\{stats\.okLatencyCountShareOfOkByProduct\.ignis === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOkByProduct\.ignis \* 100\)\}%`\} · Medicus \$\{stats\.okLatencyCountShareOfOkByProduct\.medicus === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOkByProduct\.medicus \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-of-ok-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-of-ok-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-of-ok-by-product" class="note mono">Successful latency-measurement share of successes by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
