// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-product.test.mjs
//
// Rowan DETAIL-12 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// failed-share line, the mirror of DETAIL-11's successful share,
// computed only from entries the log actually recorded. Each share
// is that product's failed entries over that product's own entries
// (ok plus failed), so a session where Ignis fails 7 times in 10
// but Vigiles fails 1 time in 10 reads differently from one where
// both fail at the same rate, and the raw counts alone do not say
// that at a glance. A product that only succeeded reads 0, not
// null; a product that only failed reads 1; a product with no
// entries reads null; an entry with an unknown or missing product
// moves no bucket (though it still counts in the global ok/failed
// totals) — no sampling, no model, no invented products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, product) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: 100,
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

const NONE = { vigiles: null, ignis: null, medicus: null };

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareByProduct, { ...NONE });
});

test("shares bucket by their own product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordOk(log, "medicus");
  assert.deepEqual(log.stats().failedShareByProduct, {
    vigiles: 0.5,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("ok entries count in the denominator, never the numerator", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordFailed(log, "ignis", "http_error");
  assert.equal(log.stats().failedShareByProduct.ignis, 2 / 3);
  assert.equal(log.stats().failedShareByProduct.vigiles, null);
  assert.equal(log.stats().failedShareByProduct.medicus, null);
});

test("a product that only succeeded reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  assert.equal(log.stats().failedShareByProduct.vigiles, 0);
  assert.equal(log.stats().failedShareByProduct.ignis, null);
  assert.equal(log.stats().failedShareByProduct.medicus, null);
});

test("a product that only failed reads 1, not null", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "vigiles", "http_error");
  assert.equal(log.stats().failedShareByProduct.vigiles, 1);
  assert.equal(log.stats().failedShareByProduct.ignis, null);
  assert.equal(log.stats().failedShareByProduct.medicus, null);
});

test("an ok entry with an unknown product moves no bucket but still counts in the global ok total", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  assert.deepEqual(log.stats().failedShareByProduct, { ...NONE });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().total, 1);
});

test("a failed entry with an unknown product moves no bucket but still counts in the global failed total", () => {
  const log = new SessionLog();
  recordFailed(log, "mystery");
  assert.deepEqual(log.stats().failedShareByProduct, { ...NONE });
  assert.equal(log.stats().failed, 1);
  assert.equal(log.stats().total, 1);
});

test("entries with a missing product move no bucket", () => {
  const log = new SessionLog();
  log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: null,
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: null,
    latencyMs: null,
    status: "network_error",
    error: "boom",
  });
  assert.deepEqual(log.stats().failedShareByProduct, { ...NONE });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().failed, 1);
});

test("shares follow clear: back to nulls", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedShareByProduct, { ...NONE });
});

test("web wiring: updateLogStats renders the per-product failed-share line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByProduct: \$\("log-stats-failed-share-by-product"\)/);
  assert.match(
    app,
    /Failed share by product: Vigiles \$\{stats\.failedShareByProduct\.vigiles/,
    "updateLogStats sets the per-product failed-share line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product failed-share stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-product" class="note mono">Failed share by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
