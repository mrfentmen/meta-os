// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-of-entries-by-product.test.mjs
//
// HANA DETAIL-40: the session-log panel gains a per-product
// failed-share-of-all-entries line, computed only from entries
// the log actually recorded. DETAIL-34 bucketed failed counts
// per product, but raw counts alone cannot say which product's
// failures dominate the whole session: this re-bases each
// product's failed count on the session's entry total. The
// denominator is the entry total, not the failed total:
// successes sit in the denominator but move no bucket, and a
// session with no entries at all reads null per product (an
// empty log). Once the session holds any entry, a product
// with no failures reads 0, never "none" — including a
// success-only log, unlike DETAIL-37, whose denominator is
// the ok total and which reads null until the first success.
// A failure with an unknown or missing product moves no
// bucket but still sits in the denominator, so the shares
// sum to the global failed share only when every failure
// carries a known product. The failure's cause never matters
// here. No sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, medicus: null };
const ZERO_SHARES = { vigiles: 0, ignis: 0, medicus: 0 };

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
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, NULL_SHARES);
});

test("a single failure reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("mixed counts divide by the entry total, not the failed total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis");
  recordFailed(log, "ignis");
  // 6 entries, not 3 failures: successes sit in the denominator only.
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, {
    vigiles: 1 / 6,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("shares sum to the global failed share when every failure carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis");
  recordFailed(log, "medicus");
  const shares = log.stats().failedShareOfEntriesByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, log.stats().failedShare);
});

test("a failure with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "mystery");
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, ZERO_SHARES);
  // The shares sum to 0 while the global failed share is 0.5.
  assert.equal(log.stats().failedShare, 0.5);
});

test("a failure with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordFailed(log, null);
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, ZERO_SHARES);
  assert.equal(log.stats().failedShare, 0.5);
});

test("successes never move a share, and a success-only log reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, ZERO_SHARES);
});

test("failures for one product read their slice beside successes of other products", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, {
    vigiles: 1 / 3,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("the failure cause never matters, only the product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "ignis", "invalid_response");
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 3 / 4,
    medicus: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedShareOfEntriesByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failed-share-of-entries-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareOfEntriesByProduct: \$\("log-stats-failed-share-of-entries-by-product"\)/);
  assert.match(
    app,
    /Failed share of all entries by product: Vigiles \$\{stats\.failedShareOfEntriesByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.failedShareOfEntriesByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the failed-share-of-entries-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-share-of-entries-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-of-entries-by-product" class="note mono">Failed share of all entries by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
