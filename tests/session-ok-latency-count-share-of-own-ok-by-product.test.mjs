// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-of-own-ok-by-product.test.mjs
//
// Hana DETAIL-54: the session-log panel gains a per-product
// usable-latency-count share of that product's own ok
// successes line, computed only from entries the log
// actually recorded. DETAIL-52 divided each product's
// measurement count by the session's global ok total, but
// a global denominator cannot say how well each product
// measures its own successes: a session where half of
// Vigiles successes carry a latency reads differently
// from one where Vigiles supplies half of all successes
// yet measures none of its own. This re-bases each
// DETAIL-36 product count on that product's own ok
// count. The null rule differs from DETAIL-52 on
// purpose: a product with no successes of its own reads
// null, never 0 — an empty log and a failure-only log
// alike read null per product, but a product with
// successes and no finite latency reads 0. Failures sit
// in neither side: they are not in any product's ok
// total and never count as measurements, even a failure
// carrying a latency value. An ok entry with no finite
// latency sits in its own product's denominator but
// moves no bucket, and an unknown- or missing-product
// success moves no bucket and no product denominator,
// unlike DETAIL-52 where it dilutes every share. A 0 ms
// latency still counts as a measurement, exactly as in
// DETAIL-45/47/49/51/52. No sampling, no model, no
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
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a single success reads 1 for its product, null for the others", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: null,
    ignis: 1,
    sanitas: null,
  });
});

test("the shares divide by each product's own ok total, not the global ok total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", null);
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  // Vigiles measured both of its own successes, Ignis
  // measured none of its one — DETAIL-52 for the same
  // log would read 2/3 and 0, and DETAIL-45 would read
  // 1 and 0.
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: 1,
    ignis: 0,
    sanitas: null,
  });
});

test("a latency-less success sits in its own denominator but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", 200);
  recordFailed(log, "sanitas");
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: 0.5,
    ignis: 1,
    sanitas: null,
  });
});

test("the shares equal the DETAIL-36 counts over each product's own ok count", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordOk(log, "sanitas", null);
  recordFailed(log, "sanitas");
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountShareOfOwnOkByProduct, {
    vigiles: 1,
    ignis: 1,
    sanitas: 0,
  });
  assert.equal(
    stats.okLatencyCountShareOfOwnOkByProduct.vigiles,
    stats.okLatencyCountByProduct.vigiles / stats.byProduct.vigiles,
  );
  assert.equal(
    stats.okLatencyCountShareOfOwnOkByProduct.ignis,
    stats.okLatencyCountByProduct.ignis / stats.byProduct.ignis,
  );
});

test("an unknown-product success moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  // The mystery measurement sits in the global ok total
  // and moves DETAIL-52, but here Vigiles still reads 1
  // and the other products stay null: the mystery success
  // is in no product's denominator.
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountShareOfOwnOkByProduct, {
    vigiles: 1,
    ignis: null,
    sanitas: null,
  });
  assert.equal(stats.okLatencyCountShareOfOkByProduct.vigiles, 0.5);
});

test("a missing-product success moves no bucket and no denominator", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 100);
  recordOk(log, null, null);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: 1,
  });
});

test("a failure-only log reads null, not 0", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: null,
    ignis: 1,
    sanitas: null,
  });
});

test("an ok entry with no finite latency is skipped as a measurement but counts as a success", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "sanitas", null);
  // DETAIL-52 for the same log would read 0, 1/3, 0;
  // here each share divides by its own product's single
  // success, so Ignis reads 1 and the others read 0.
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: 0,
    ignis: 1,
    sanitas: 0,
  });
});

test("a success-only log with no finite latency reads 0 per product with successes, null otherwise", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: null,
  });
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const shares = log.stats().okLatencyCountShareOfOwnOkByProduct;
  assert.deepEqual(shares, { vigiles: 1, ignis: 1, sanitas: null });
  assert.equal(Number.isNaN(shares.vigiles), false);
});

test("the shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().okLatencyCountShareOfOwnOkByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
});

test("web wiring: updateLogStats renders the ok-latency-count-share-of-own-ok-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareOfOwnOkByProduct: \$\("log-stats-ok-latency-count-share-of-own-ok-by-product"\)/);
  assert.match(
    app,
    /Successful latency-measurement share of that product's own successes by product: Vigiles \$\{stats\.okLatencyCountShareOfOwnOkByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOwnOkByProduct\.vigiles \* 100\)\}%`\} · Ignis \$\{stats\.okLatencyCountShareOfOwnOkByProduct\.ignis === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOwnOkByProduct\.ignis \* 100\)\}%`\} · Sanitas \$\{stats\.okLatencyCountShareOfOwnOkByProduct\.sanitas === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOwnOkByProduct\.sanitas \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-of-own-ok-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-of-own-ok-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-of-own-ok-by-product" class="note mono">Successful latency-measurement share of that product's own successes by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
