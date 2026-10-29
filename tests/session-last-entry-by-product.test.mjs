// Node built-in test runner, no dependencies:
//   node --test tests/session-last-entry-by-product.test.mjs
//
// Rowan DETAIL-16 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// last-entry line, computed only from entries the log actually
// recorded. Each product's bucket holds the request timestamp of
// its MOST RECENT recorded entry, any status — the closing
// counterpart to DETAIL-15's first entry. Overwritten on every
// usable entry, so it reads when recording for a product last
// happened, not when it last succeeded (DETAIL-5) or last failed
// (DETAIL-7). An entry with an unknown or missing product moves
// no bucket, and an entry without a usable timestamp leaves its
// bucket's previous value in place. Null per product with no
// usable entry, never a fabricated timestamp. No sampling, no
// model, no invented products.

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

test("empty log: every product last entry is null, not a fabricated timestamp", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().lastEntryAtByProduct, { ...NULLS });
});

test("last recorded entry per product wins; later entries always move the bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:00.000Z", "ignis");
  assert.deepEqual(log.stats().lastEntryAtByProduct, {
    vigiles: "2026-10-29T12:05:00.000Z",
    ignis: "2026-10-29T12:06:00.000Z",
    sanitas: null,
  });
});

test("a failed last entry counts: any status moves the bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis", "network_error");
  assert.equal(log.stats().lastEntryAtByProduct.ignis, "2026-10-29T12:05:00.000Z");
});

test("a product with no entries in a non-empty session reads null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().lastEntryAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: null,
    sanitas: null,
  });
});

test("insertion order, not maximum timestamp: a later entry with an earlier timestamp string still moves the bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.equal(log.stats().lastEntryAtByProduct.sanitas, "2026-10-29T12:00:00.000Z");
});

test("an entry with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  assert.deepEqual(log.stats().lastEntryAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 1);
});

test("entries with a missing product move no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:01:00.000Z", null, "network_error");
  assert.deepEqual(log.stats().lastEntryAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("an entry without a usable timestamp leaves the previous value in place", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  assert.equal(log.stats().lastEntryAtByProduct.ignis, "2026-10-29T12:00:00.000Z");
});

test("an entry without a usable timestamp leaves the bucket open for a later usable entry", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  recordAt(log, "2026-10-29T12:03:00.000Z", "ignis");
  assert.equal(log.stats().lastEntryAtByProduct.ignis, "2026-10-29T12:03:00.000Z");
});

test("last entries follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().lastEntryAtByProduct, { ...NULLS });
});

test("web wiring: updateLogStats renders the per-product last-entry line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsLastEntryByProduct: \$\("log-stats-last-entry-by-product"\)/);
  assert.match(
    app,
    /Last entry by product: Vigiles \$\{stats\.lastEntryAtByProduct\.vigiles \?\? "none"\} · Ignis \$\{stats\.lastEntryAtByProduct\.ignis \?\? "none"\} · Sanitas \$\{stats\.lastEntryAtByProduct\.sanitas \?\? "none"\}/,
    "updateLogStats sets the per-product last-entry line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product last-entry stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-last-entry-by-product" class="note mono">Last entry by product: Vigiles none · Ignis none · Sanitas none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
