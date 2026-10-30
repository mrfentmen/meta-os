// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-share-of-ok-by-product.test.mjs
//
// Rowan DETAIL-37: the session-log panel gains a per-product
// successful-count share line, computed only from entries the
// log actually recorded. DETAIL-1 bucketed ok counts per
// product, but raw counts alone cannot say which product's
// successes dominate the session's successes: this re-bases
// each product's ok count on the session's ok total. The
// denominator is the ok total, not the entry total: failures
// are not successes, so they sit in neither a bucket nor the
// denominator, and a session with no successes at all reads
// null per product (an empty log and a failure-only log
// alike). Once the session holds any success, a product with
// no successes reads 0, never "none". A success with an
// unknown or missing product moves no bucket but still sits
// in the denominator, so the shares sum to 1 only when every
// success carries a known product, exactly as DETAIL-13's and
// DETAIL-35's shares do. Unlike DETAIL-35's latency shares,
// this is a count share: an ok entry with no finite latency
// still counts, and a zero latency is still a success.
// No sampling, no model, no invented measurements.

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
  assert.deepEqual(log.stats().okShareOfOkByProduct, NULL_SHARES);
});

test("a single success reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("mixed counts divide by the ok total, not the entry total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "medicus");
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  // 4 successes, not 6 entries: failures move neither bucket nor denominator.
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0.5,
    ignis: 0.25,
    medicus: 0.25,
  });
});

test("shares sum to 1 when every success carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "medicus");
  const shares = log.stats().okShareOfOkByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
});

test("a success with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "mystery");
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
});

test("a success with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordOk(log, null);
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0.5,
  });
});

test("failures never move a share, and a failure-only log reads null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats().okShareOfOkByProduct, NULL_SHARES);
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("successes for one product read 1 even beside failures of other products", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 1,
  });
});

test("an ok entry with no finite latency still counts, unlike DETAIL-35", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "medicus", null);
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 1 / 3,
    ignis: 1 / 3,
    medicus: 1 / 3,
  });
});

test("a success-only log with zero latencies still divides, unlike DETAIL-35", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  assert.deepEqual(log.stats().okShareOfOkByProduct, {
    vigiles: 0.5,
    ignis: 0.5,
    medicus: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().okShareOfOkByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the ok-share-of-ok-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkShareOfOkByProduct: \$\("log-stats-ok-share-of-ok-by-product"\)/);
  assert.match(
    app,
    /Successful share of successes by product: Vigiles \$\{stats\.okShareOfOkByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okShareOfOkByProduct\.vigiles \* 100\)\}%`\} /,
    "updateLogStats sets the ok-share-of-ok-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-share-of-ok-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-share-of-ok-by-product" class="note mono">Successful share of successes by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
