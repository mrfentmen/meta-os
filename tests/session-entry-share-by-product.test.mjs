// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-share-by-product.test.mjs
//
// Rowan DETAIL-13 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// session-share line, computed only from entries the log actually
// recorded. Each share is that product's entries over the session's
// total entries, so a session split 2/1/1 across the products reads
// differently from one where a single product dominates, and the raw
// counts alone do not say that at a glance. The denominator is the
// session total, not the product's own entries, so the null rule
// differs from DETAIL-11/12 on purpose: an empty log reads null per
// product (no total to divide by), but once the log holds any entry
// a product with no entries reads 0 — it genuinely holds 0% of the
// session — never "none". The shares sum to 1 when every entry
// carries a known product, and to less than 1 when unknown-product
// entries sit in the total but in no bucket. An entry with an
// unknown or missing product moves no bucket (though it still
// counts in the total) — no sampling, no model, no invented
// products.

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

const NONE = { vigiles: null, ignis: null, sanitas: null };

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().entryShareByProduct, { ...NONE });
});

test("shares bucket by their own product over the session total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordOk(log, "sanitas");
  assert.deepEqual(log.stats().entryShareByProduct, {
    vigiles: 1 / 3,
    ignis: 0.5,
    sanitas: 1 / 6,
  });
});

test("ok and failed entries both count: the numerator is all of a product's entries", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordFailed(log, "ignis", "http_error");
  assert.equal(log.stats().entryShareByProduct.ignis, 3 / 4);
  assert.equal(log.stats().entryShareByProduct.vigiles, 1 / 4);
  assert.equal(log.stats().entryShareByProduct.sanitas, 0);
});

test("a product with no entries in a non-empty session reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().entryShareByProduct, {
    vigiles: 1,
    ignis: 0,
    sanitas: 0,
  });
});

test("shares sum to 1 when every entry carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis");
  recordOk(log, "sanitas");
  const shares = log.stats().entryShareByProduct;
  assert.equal(shares.vigiles + shares.ignis + shares.sanitas, 1);
});

test("an ok entry with an unknown product moves no bucket but still counts in the total", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  assert.deepEqual(log.stats().entryShareByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: 0,
  });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().total, 1);
});

test("a failed entry with an unknown product moves no bucket but still counts in the total", () => {
  const log = new SessionLog();
  recordFailed(log, "mystery");
  assert.deepEqual(log.stats().entryShareByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: 0,
  });
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
  assert.deepEqual(log.stats().entryShareByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: 0,
  });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().failed, 1);
});

test("shares follow clear: back to nulls", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().entryShareByProduct, { ...NONE });
});

test("web wiring: updateLogStats renders the per-product session-share line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntryShareByProduct: \$\("log-stats-entry-share-by-product"\)/);
  assert.match(
    app,
    /Session share by product: Vigiles \$\{stats\.entryShareByProduct\.vigiles/,
    "updateLogStats sets the per-product session-share line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product session-share stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-share-by-product" class="note mono">Session share by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
