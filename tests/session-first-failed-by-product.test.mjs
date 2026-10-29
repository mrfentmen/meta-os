// Node built-in test runner, no dependencies:
//   node --test tests/session-first-failed-by-product.test.mjs
//
// Rowan DETAIL-19 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// first-failure line, computed only from entries the log actually
// recorded. Each product's bucket holds the request timestamp of
// its FIRST recorded failure, by insertion order — set once,
// never overwritten, so a later failure (even one carrying an
// earlier timestamp string) never moves the bucket. It is the
// opening counterpart to DETAIL-7's last failure: the pair says
// when a product's failures began and when they last happened.
// Same bucket rules as DETAIL-7: successes never move a bucket,
// a failure with an unknown or missing product moves no bucket,
// and a failure without a usable timestamp leaves its bucket
// open for a later usable failure. Null per product with no
// failure, never a fabricated timestamp. No sampling, no model,
// no invented products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordAt(log, timestamp, product, status = "network_error") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

const NULLS = { vigiles: null, ignis: null, sanitas: null };

test("empty log: every product first failure is null, not a fabricated timestamp", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().firstFailedAtByProduct, { ...NULLS });
});

test("first failure per product is the earliest recorded failure, by insertion order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:00.000Z", "ignis");
  assert.deepEqual(log.stats().firstFailedAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: "2026-10-29T12:01:00.000Z",
    sanitas: null,
  });
});

test("a later failure never overwrites the first, even with an earlier timestamp string", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.equal(log.stats().firstFailedAtByProduct.sanitas, "2026-10-29T12:05:00.000Z");
  assert.equal(log.stats().lastFailedAtByProduct.sanitas, "2026-10-29T12:00:00.000Z");
});

test("successes never move a first-failure bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "ok");
  recordAt(log, "2026-10-29T12:03:00.000Z", "ignis", "ok");
  assert.deepEqual(log.stats().firstFailedAtByProduct, { ...NULLS });
  assert.equal(log.stats().lastOkAtByProduct.ignis, "2026-10-29T12:03:00.000Z");
});

test("a success before the first failure leaves the bucket open for that failure", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles", "ok");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles");
  assert.equal(log.stats().firstFailedAtByProduct.vigiles, "2026-10-29T12:04:00.000Z");
});

test("a failure with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.deepEqual(log.stats().firstFailedAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("failures with a missing product move no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  assert.deepEqual(log.stats().firstFailedAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 1);
});

test("a failure without a usable timestamp leaves the bucket open for a later usable failure", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: null,
    status: "network_error",
    error: "boom",
  });
  assert.equal(log.stats().firstFailedAtByProduct.ignis, null);
  recordAt(log, "2026-10-29T12:07:00.000Z", "ignis");
  assert.equal(log.stats().firstFailedAtByProduct.ignis, "2026-10-29T12:07:00.000Z");
});

test("a product with no failure in a non-empty session reads null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:03:00.000Z", "sanitas", "ok");
  assert.deepEqual(log.stats().firstFailedAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: null,
    sanitas: null,
  });
});

test("first failure follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().firstFailedAtByProduct, { ...NULLS });
});

test("web wiring: updateLogStats renders the per-product first-failure line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFirstFailedByProduct: \$\("log-stats-first-failed-by-product"\)/);
  assert.match(
    app,
    /First failure by product: Vigiles \$\{stats\.firstFailedAtByProduct\.vigiles \?\? "none"\} · Ignis \$\{stats\.firstFailedAtByProduct\.ignis \?\? "none"\} · Sanitas \$\{stats\.firstFailedAtByProduct\.sanitas \?\? "none"\}/,
    "updateLogStats sets the per-product first-failure line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product first-failure stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-first-failed-by-product" class="note mono">First failure by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
