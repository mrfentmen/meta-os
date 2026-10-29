// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-by-product.test.mjs
//
// Rowan DETAIL-17 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// entry-span line, computed only from entries the log actually
// recorded. Each product's bucket holds the milliseconds between
// its DETAIL-15 first and DETAIL-16 last recorded entry
// timestamps, any status — how long that product's recording
// stretches. Derived only from those two endpoint buckets, so the
// same bucket rules apply: an entry with an unknown or missing
// product moves no bucket, and an entry without a usable timestamp
// leaves both endpoints in place. A product with exactly one
// usable entry reads 0, not null. A bucket timestamp that does not
// parse reads null, never NaN. The difference is kept raw, not
// clamped: a negative span means entries were recorded out of
// timestamp order. Null per product with no usable entry pair,
// never a fabricated span. No sampling, no model, no invented
// products.

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

const NULLS = { vigiles: null, ignis: null, sanitas: null };

test("empty log: every product entry span is null, not a fabricated span", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().entrySpanMsByProduct, { ...NULLS });
});

test("span is last minus first per product, in whole milliseconds", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.500Z", "ignis");
  assert.deepEqual(log.stats().entrySpanMsByProduct, {
    vigiles: 300000,
    ignis: 330500,
    sanitas: null,
  });
});

test("a product with exactly one usable entry reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.deepEqual(log.stats().entrySpanMsByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: 0,
  });
});

test("a failed last entry counts: any status moves the endpoints", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis", "network_error");
  assert.equal(log.stats().entrySpanMsByProduct.ignis, 120000);
});

test("a product with no entries in a non-empty session reads null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:03:00.000Z", "vigiles");
  assert.deepEqual(log.stats().entrySpanMsByProduct, {
    vigiles: 180000,
    ignis: null,
    sanitas: null,
  });
});

test("insertion order, not min/max: a later entry with an earlier timestamp reads a negative span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.equal(log.stats().entrySpanMsByProduct.sanitas, -300000);
});

test("an entry with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.deepEqual(log.stats().entrySpanMsByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("entries with a missing product move no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", null, "network_error");
  assert.deepEqual(log.stats().entrySpanMsByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("an entry without a usable timestamp leaves the span in place", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  assert.equal(log.stats().entrySpanMsByProduct.ignis, 300000);
});

test("an unparseable endpoint timestamp reads null, never NaN", () => {
  const log = new SessionLog();
  recordAt(log, "not-a-timestamp", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().entrySpanMsByProduct.ignis, null);
  assert.equal(log.stats().firstEntryAtByProduct.ignis, "not-a-timestamp");
});

test("entry spans follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().entrySpanMsByProduct, { ...NULLS });
});

test("web wiring: updateLogStats renders the per-product entry-span line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanByProduct: \$\("log-stats-entry-span-by-product"\)/);
  assert.match(
    app,
    /Entry span by product: Vigiles \$\{stats\.entrySpanMsByProduct\.vigiles === null \? "none" : `\$\{stats\.entrySpanMsByProduct\.vigiles\} ms`\}/,
    "updateLogStats sets the per-product entry-span line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product entry-span stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-by-product" class="note mono">Entry span by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
