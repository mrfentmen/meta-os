// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-count-by-product.test.mjs
//
// Rowan DETAIL-34: the session-log panel gains a per-product
// failed-count line, computed only from entries the log actually
// recorded. DETAIL-1's line buckets successes per product and
// lumps all failures into one global total, and DETAIL-14's line
// counts entries per product without splitting them by outcome,
// so a session where Vigiles failed twice and Ignis never failed
// reads that nowhere as counts — DETAIL-12's failed shares imply
// it, but only as shares of each product's own entries. This
// exposes the counts behind those shares: the failure mirror of
// DETAIL-1's ok counts. Always plain counts, never null: a
// product with no failures reads 0. A failure with an unknown or
// missing product still counts in the global failed total but
// moves no bucket, exactly as DETAIL-9's cause buckets do.
// Successes never move a bucket. No sampling, no model, no
// invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordFailed(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

function recordOk(log, product) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

test("empty log: every product reads 0", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedCountByProduct, { vigiles: 0, ignis: 0, medicus: 0 });
});

test("failures bucket by their own product, successes never move a bucket", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "vigiles", "http_error");
  recordFailed(log, "ignis");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordOk(log, "medicus");
  assert.deepEqual(log.stats().failedCountByProduct, { vigiles: 2, ignis: 1, medicus: 0 });
});

test("a success-only log reads 0 per product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "medicus");
  assert.deepEqual(log.stats().failedCountByProduct, { vigiles: 0, ignis: 0, medicus: 0 });
});

test("buckets plus unbucketed failures equal the global failed total", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "mystery", "invalid_response");
  const stats = log.stats();
  assert.equal(stats.failed, 3);
  const bucketed = Object.values(stats.failedCountByProduct).reduce((a, b) => a + b, 0);
  assert.equal(bucketed, 2);
});

test("a failure with an unknown product moves no bucket but counts globally", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "mystery", "http_error");
  const stats = log.stats();
  assert.deepEqual(stats.failedCountByProduct, { vigiles: 1, ignis: 0, medicus: 0 });
  assert.equal(stats.failed, 2);
});

test("a failure with a missing product moves no bucket but counts globally", () => {
  const log = new SessionLog();
  recordFailed(log, "medicus", "invalid_response");
  recordFailed(log, null, "http_error");
  const stats = log.stats();
  assert.deepEqual(stats.failedCountByProduct, { vigiles: 0, ignis: 0, medicus: 1 });
  assert.equal(stats.failed, 2);
});

test("failed counts agree with the per-product entry and ok counts", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles");
  recordFailed(log, "vigiles", "http_error");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  const stats = log.stats();
  for (const product of ["vigiles", "ignis", "medicus"]) {
    assert.equal(
      stats.entryCountByProduct[product],
      stats.byProduct[product] + stats.failedCountByProduct[product],
    );
  }
});

test("counts follow clear: back to zero", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedCountByProduct, { vigiles: 0, ignis: 0, medicus: 0 });
});

test("web wiring: updateLogStats renders the failed-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedByProduct: \$\("log-stats-failed-by-product"\)/);
  assert.match(
    app,
    /Failed by product: Vigiles \$\{stats\.failedCountByProduct\.vigiles\} · Ignis \$\{stats\.failedCountByProduct\.ignis\} · Medicus \$\{stats\.failedCountByProduct\.medicus\}/,
    "updateLogStats sets the failed-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-by-product" class="note mono">Failed by product: Vigiles 0 · Ignis 0 · Medicus 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
