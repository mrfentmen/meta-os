// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-count-by-product.test.mjs
//
// Rowan DETAIL-14 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// entry-count line, computed only from entries the log actually
// recorded. These are the counts behind DETAIL-13's shares: each
// product's entries, ok plus failed, as plain counts — the
// denominator DETAIL-11/12 already divide by, and the numerator
// DETAIL-13 divides by the session total. Unlike DETAIL-1's
// byProduct, which counts only successes, a product that only
// failed still reads its full count here, so the counts line and
// the assessments line disagree exactly where failures happened.
// Always-renders zeros, never null: an empty log reads 0 per
// product, and a product with no entries reads 0 in a non-empty
// session. An entry with an unknown or missing product moves no
// bucket (though it still counts in the total), so the three
// counts sum to the total only when every entry carries a known
// product. No sampling, no model, no invented products.

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

const ZEROS = { vigiles: 0, ignis: 0, sanitas: 0 };

test("empty log: every product count is zero, not null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().entryCountByProduct, { ...ZEROS });
});

test("counts bucket by their own product, ok plus failed", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  recordOk(log, "sanitas");
  assert.deepEqual(log.stats().entryCountByProduct, {
    vigiles: 2,
    ignis: 3,
    sanitas: 1,
  });
});

test("a product that only failed still reads its full count, unlike byProduct", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "ignis", "http_error");
  assert.equal(log.stats().entryCountByProduct.ignis, 2);
  assert.equal(log.stats().byProduct.ignis, 0);
});

test("a product with no entries in a non-empty session reads 0", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().entryCountByProduct, {
    vigiles: 1,
    ignis: 0,
    sanitas: 0,
  });
});

test("counts sum to the total when every entry carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis");
  recordOk(log, "sanitas");
  const counts = log.stats().entryCountByProduct;
  assert.equal(counts.vigiles + counts.ignis + counts.sanitas, log.stats().total);
});

test("an ok entry with an unknown product moves no bucket but still counts in the total", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  assert.deepEqual(log.stats().entryCountByProduct, { ...ZEROS });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().total, 1);
});

test("a failed entry with an unknown product moves no bucket but still counts in the total", () => {
  const log = new SessionLog();
  recordFailed(log, "mystery");
  assert.deepEqual(log.stats().entryCountByProduct, { ...ZEROS });
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
  assert.deepEqual(log.stats().entryCountByProduct, { ...ZEROS });
  assert.equal(log.stats().ok, 1);
  assert.equal(log.stats().failed, 1);
  assert.equal(log.stats().total, 2);
});

test("counts follow clear: back to zeros", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().entryCountByProduct, { ...ZEROS });
});

test("web wiring: updateLogStats renders the per-product entry-count line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntryCountByProduct: \$\("log-stats-entry-count-by-product"\)/);
  assert.match(
    app,
    /Entries by product: Vigiles \$\{stats\.entryCountByProduct\.vigiles\} · Ignis \$\{stats\.entryCountByProduct\.ignis\} · Sanitas \$\{stats\.entryCountByProduct\.sanitas\}/,
    "updateLogStats sets the per-product entry-count line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product entry-count stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-count-by-product" class="note mono">Entries by product: Vigiles 0 · Ignis 0 · Sanitas 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
