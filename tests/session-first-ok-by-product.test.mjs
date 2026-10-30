// Node built-in test runner, no dependencies:
//   node --test tests/session-first-ok-by-product.test.mjs
//
// Rowan DETAIL-18 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// first-success line, computed only from entries the log actually
// recorded. Each product's bucket holds the request timestamp of
// its FIRST recorded ok entry, by insertion order — set once,
// never overwritten, so a later success (even one carrying an
// earlier timestamp string) never moves the bucket. It is the
// opening counterpart to DETAIL-5's last success: the pair says
// when a product's successes began and when they last happened.
// Same bucket rules as DETAIL-5: failures never move a bucket,
// an ok entry with an unknown or missing product moves no bucket,
// and an ok entry without a usable timestamp leaves its bucket
// open for a later usable success. Null per product with no
// success, never a fabricated timestamp. No sampling, no model,
// no invented products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordAt(log, timestamp, product, status = "ok") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

const NULLS = { vigiles: null, ignis: null, medicus: null };

test("empty log: every product first success is null, not a fabricated timestamp", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().firstOkAtByProduct, { ...NULLS });
});

test("first success per product is the earliest recorded ok entry, by insertion order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:00.000Z", "ignis");
  assert.deepEqual(log.stats().firstOkAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: "2026-10-29T12:01:00.000Z",
    medicus: null,
  });
});

test("a later ok entry never overwrites the first, even with an earlier timestamp string", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "medicus");
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  assert.equal(log.stats().firstOkAtByProduct.medicus, "2026-10-29T12:05:00.000Z");
  assert.equal(log.stats().lastOkAtByProduct.medicus, "2026-10-29T12:00:00.000Z");
});

test("failures never move a first-success bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "network_error");
  recordAt(log, "2026-10-29T12:03:00.000Z", "ignis", "http_error");
  assert.deepEqual(log.stats().firstOkAtByProduct, { ...NULLS });
  assert.equal(log.stats().lastFailedAtByProduct.ignis, "2026-10-29T12:03:00.000Z");
});

test("a failure before the first success leaves the bucket open for that success", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles", "network_error");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles");
  assert.equal(log.stats().firstOkAtByProduct.vigiles, "2026-10-29T12:04:00.000Z");
});

test("an ok entry with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.deepEqual(log.stats().firstOkAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("ok entries with a missing product move no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  assert.deepEqual(log.stats().firstOkAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 1);
});

test("an ok entry without a usable timestamp leaves the bucket open for a later usable success", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  assert.equal(log.stats().firstOkAtByProduct.ignis, null);
  recordAt(log, "2026-10-29T12:07:00.000Z", "ignis");
  assert.equal(log.stats().firstOkAtByProduct.ignis, "2026-10-29T12:07:00.000Z");
});

test("a product with no success in a non-empty session reads null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:03:00.000Z", "medicus", "network_error");
  assert.deepEqual(log.stats().firstOkAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: null,
    medicus: null,
  });
});

test("first success follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().firstOkAtByProduct, { ...NULLS });
});

test("web wiring: updateLogStats renders the per-product first-success line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFirstOkByProduct: \$\("log-stats-first-ok-by-product"\)/);
  assert.match(
    app,
    /First success by product: Vigiles \$\{stats\.firstOkAtByProduct\.vigiles \?\? "none"\} · Ignis \$\{stats\.firstOkAtByProduct\.ignis \?\? "none"\} · Medicus \$\{stats\.firstOkAtByProduct\.medicus \?\? "none"\}/,
    "updateLogStats sets the per-product first-success line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product first-success stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-first-ok-by-product" class="note mono">First success by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
