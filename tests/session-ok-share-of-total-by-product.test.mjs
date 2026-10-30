// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-share-of-total-by-product.test.mjs
//
// Rowan DETAIL-41: the session-log panel gains a per-product
// successful-count share of all entries line, computed only
// from entries the log actually recorded. DETAIL-37 re-based
// each product's ok count on the ok total, but ok-total
// shares alone cannot say what slice of everything recorded
// a product's successes are: this re-bases each product's ok
// count on the session's total entry count. The denominator
// is the entry total, not the ok total: failures sit in the
// denominator but move no bucket, and a session with no
// entries at all reads null per product (an empty log).
// Once the session holds any entry, a product with no
// successes reads 0, never "none" — a failure-only log reads
// 0 per product, not null, because the denominator exists
// and the buckets are genuinely empty. A success with an
// unknown or missing product moves no bucket but still sits
// in the denominator, so the shares sum to the session ok
// share, and to 1 only when every entry is a known-product
// success, exactly as DETAIL-37's shares do within the ok
// total. An ok entry with no finite latency still counts:
// this is a count share, not a latency share, so DETAIL-35's
// skip rule does not apply. No sampling, no model, no
// invented counts.

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

function recordFailed(log, product, status = "network_error", latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status,
    error: "boom",
  });
}

test("empty log: every product share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().okShareOfTotalByProduct, NULL_SHARES);
});

test("a single success reads 1 for its product and 0 elsewhere", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("mixed counts divide by the entry total, not the ok total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordFailed(log, "medicus");
  recordFailed(log, "ignis");
  recordOk(log, "medicus");
  // 6 entries, 4 successes: failures sit in the denominator but move no bucket.
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 2 / 6,
    ignis: 1 / 6,
    medicus: 1 / 6,
  });
});

test("shares sum to the session ok share, and to 1 only for all-known successes", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "medicus");
  const shares = log.stats().okShareOfTotalByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 1);
  assert.equal(sum, log.stats().okShare);
  recordFailed(log, "vigiles");
  const mixed = log.stats().okShareOfTotalByProduct;
  const mixedSum = Object.values(mixed).reduce((a, b) => a + b, 0);
  assert.equal(mixedSum, 0.75);
  assert.equal(mixedSum, log.stats().okShare);
});

test("a success with an unknown product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "mystery");
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
});

test("a success with a missing product moves no bucket but sits in the total", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordOk(log, null);
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0.5,
  });
});

test("failures never move a bucket, and a failure-only log reads 0, not null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats().okShareOfTotalByProduct, ZERO_SHARES);
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0,
    ignis: 1 / 3,
    medicus: 0,
  });
});

test("successes for one product read their entry-total share beside other products' failures", () => {
  const log = new SessionLog();
  recordOk(log, "medicus");
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis");
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 1 / 3,
  });
});

test("an ok entry with no finite latency still counts, unlike the latency sums", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", null);
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0.5,
    ignis: 0.5,
    medicus: 0,
  });
});

test("a failure carrying a latency value still moves no bucket", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 250);
  assert.deepEqual(log.stats().okShareOfTotalByProduct, {
    vigiles: 0,
    ignis: 0.5,
    medicus: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().okShareOfTotalByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the ok-share-of-total-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkShareOfTotalByProduct: \$\("log-stats-ok-share-of-total-by-product"\)/);
  assert.match(
    app,
    /Successful share of all entries by product: Vigiles \$\{stats\.okShareOfTotalByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.okShareOfTotalByProduct\.vigiles \* 100\)\}%`\} /,
    "updateLogStats sets the ok-share-of-total-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-share-of-total-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-share-of-total-by-product" class="note mono">Successful share of all entries by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
