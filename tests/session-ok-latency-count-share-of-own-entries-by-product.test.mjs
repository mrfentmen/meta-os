// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-of-own-entries-by-product.test.mjs
//
// Hana DETAIL-56 (renumbered after Rowan's distinct DETAIL-55 landed first, both sides kept in the merge):
// the session-log panel gains a per-product
// usable-latency-count share of that product's own entries
// line, computed only from entries the log actually
// recorded. DETAIL-47 divided each product's measurement
// count by the session's global entry total, but a global
// denominator cannot say how well each product measures
// its own recorded entries: a session where half of
// everything Vigiles recorded carries a latency reads
// differently from one where Vigiles supplies half of all
// entries yet measures none of its own, and a product
// whose every entry is a measured success reads 1
// whatever its share of the session. This re-bases each
// DETAIL-36 product count on that product's own entry
// total (DETAIL-14). The null rule differs from DETAIL-54
// on purpose: a product with entries but no usable
// latency reads 0, never "none" — a failure-only product
// reads 0 here, where DETAIL-54 reads null because its
// denominator is the ok count. Failures sit in the
// denominator but move no bucket: they are entries of
// the product but never measurements, even a failure
// carrying a latency value. An ok entry with no finite
// latency sits in its own product's denominator but
// moves no bucket, and an unknown- or missing-product
// entry moves no bucket and no product denominator,
// unlike DETAIL-47 where it dilutes every share. A 0 ms
// latency still counts as a measurement, exactly as in
// DETAIL-45/47/49/51/52/54. No sampling, no model, no
// invented measurements.

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
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a single success reads 1 for its product, null for the others", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: null,
    ignis: 1,
    sanitas: null,
  });
});

test("the shares divide by each product's own entry total, not the global entry total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "ignis");
  recordOk(log, "sanitas");
  recordFailed(log, "sanitas");
  recordFailed(log, "sanitas");
  // DETAIL-47 for the same log would read 1/7, 2/7, 1/7;
  // here each share divides by its own product's entries,
  // so Vigiles reads 1/2, Ignis 1, and Sanitas 1/3.
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 1 / 2,
    ignis: 1,
    sanitas: 1 / 3,
  });
});

test("a latency-less success sits in its own denominator but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordFailed(log, "vigiles");
  recordOk(log, "ignis", 200);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: null,
  });
});

test("the shares equal the DETAIL-36 counts over each product's own entry count", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordFailed(log, "vigiles");
  recordOk(log, "ignis");
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: stats.okLatencyCountByProduct.vigiles / stats.entryCountByProduct.vigiles,
    ignis: stats.okLatencyCountByProduct.ignis / stats.entryCountByProduct.ignis,
    sanitas: null,
  });
});

test("an unknown-product success moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  recordOk(log, "vigiles");
  // DETAIL-47 for the same log would read 1/2 for Vigiles;
  // here the mystery entry moves no product denominator,
  // so Vigiles still reads 1.
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 1,
    ignis: null,
    sanitas: null,
  });
});

test("a missing-product success moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordOk(log, null);
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: null,
    ignis: 1,
    sanitas: null,
  });
});

test("a failure-only product reads 0, not null", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  // DETAIL-54 for the same log would read null per product;
  // here failures are entries, so each failed product reads 0.
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: null,
  });
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: null,
  });
});

test("an ok entry with no finite latency is skipped as a measurement but counts as an entry", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "sanitas", null);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("a success-only log with no finite latency reads 0 per product with entries, null otherwise", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: null,
  });
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const shares = log.stats().okLatencyCountShareOfOwnEntriesByProduct;
  assert.deepEqual(shares, { vigiles: 1, ignis: 1, sanitas: null });
  assert.equal(Number.isNaN(shares.vigiles), false);
});

test("the shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnEntriesByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the ok-latency-count-share-of-own-entries-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareOfOwnEntriesByProduct: \$\("log-stats-ok-latency-count-share-of-own-entries-by-product"\)/);
  assert.match(
    app,
    /Successful latency-measurement share of that product's own entries by product: Vigiles \$\{stats\.okLatencyCountShareOfOwnEntriesByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOwnEntriesByProduct\.vigiles \* 100\)\}%`\} · Ignis \$\{stats\.okLatencyCountShareOfOwnEntriesByProduct\.ignis === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOwnEntriesByProduct\.ignis \* 100\)\}%`\} · Sanitas \$\{stats\.okLatencyCountShareOfOwnEntriesByProduct\.sanitas === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOwnEntriesByProduct\.sanitas \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-of-own-entries-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-of-own-entries-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-of-own-entries-by-product" class="note mono">Successful latency-measurement share of that product's own entries by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
