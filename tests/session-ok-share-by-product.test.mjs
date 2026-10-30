// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-share-by-product.test.mjs
//
// Rowan DETAIL-11 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// successful-share line, computed only from entries the log
// actually recorded. Each share is that product's ok entries over
// that product's own entries (ok plus failed), so a session where
// Ignis succeeds 9 times in 10 but Vigiles succeeds 3 times in 10
// reads differently from one where both succeed at the same rate,
// and the raw counts alone do not say that at a glance. A product
// that only failed reads 0, not null; a product with no entries
// reads null; an entry with an unknown or missing product moves
// no bucket (though it still counts in the global ok/failed
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
  assert.deepEqual(log.stats().okShareByProduct, { ...NONE });
});

test("shares bucket by their own product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordOk(log, "medicus");
  assert.deepEqual(log.stats().okShareByProduct, {
    vigiles: 0.5,
    ignis: 2 / 3,
    medicus: 1,
  });
});

test("failures count in the denominator, never the numerator", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordFailed(log, "ignis", "http_error");
  assert.equal(log.stats().okShareByProduct.ignis, 1 / 3);
  assert.equal(log.stats().okShareByProduct.vigiles, null);
  assert.equal(log.stats().okShareByProduct.medicus, null);
});

test("a product that only failed reads 0, not null", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "vigiles", "http_error");
  assert.equal(log.stats().okShareByProduct.vigiles, 0);
  assert.equal(log.stats().okShareByProduct.ignis, null);
  assert.equal(log.stats().okShareByProduct.medicus, null);
});

test("an ok entry with an unknown product moves no bucket but still counts in the global ok total", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  assert.deepEqual(log.stats().okShareByProduct, { ...NONE });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().total, 1);
});

test("a failed entry with an unknown product moves no bucket but still counts in the global failed total", () => {
  const log = new SessionLog();
  recordFailed(log, "mystery");
  assert.deepEqual(log.stats().okShareByProduct, { ...NONE });
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
  assert.deepEqual(log.stats().okShareByProduct, { ...NONE });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().failed, 1);
});

test("shares follow clear: back to nulls", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().okShareByProduct, { ...NONE });
});

test("web wiring: updateLogStats renders the per-product successful-share line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkShareByProduct: \$\("log-stats-ok-share-by-product"\)/);
  assert.match(
    app,
    /Successful share by product: Vigiles \$\{stats\.okShareByProduct\.vigiles/,
    "updateLogStats sets the per-product successful-share line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product successful-share stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-share-by-product" class="note mono">Successful share by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
