// Node built-in test runner, no dependencies:
//   node --test tests/session-latency-count.test.mjs
//
// HANA DETAIL-36: the session-log panel gains usable-latency
// count lines, computed only from entries the log actually
// recorded. DETAIL-4's mean and DETAIL-8's per-product means
// say how slow successes were, but never how many measurements
// the mean stands on — a mean over one success reads the same
// as a mean over a hundred. This exposes the counts behind
// those means: no new counting rule, the stats loop already
// counts usable latencies for the means. Always plain counts,
// never null: a session or product with no usable latency
// reads 0. Failures never contribute, even a failure carrying
// a latency value; an ok entry with no finite latency is
// skipped rather than counted as zero; and an ok entry with
// an unknown or missing product counts globally but moves no
// bucket, exactly as DETAIL-4/8's means do. No sampling, no
// model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

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

test("empty log: the global count is 0 and every product reads 0", () => {
  const log = new SessionLog();
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 0);
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 0, ignis: 0, sanitas: 0 });
});

test("ok entries with a usable latency count globally and per product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 200);
  recordOk(log, "ignis", 150);
  recordOk(log, "sanitas", 120);
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 4);
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 2, ignis: 1, sanitas: 1 });
});

test("an ok entry with no usable latency is skipped, never counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  recordOk(log, "sanitas", Number.POSITIVE_INFINITY);
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 1);
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 1, ignis: 0, sanitas: 0 });
  assert.equal(stats.avgOkLatencyMs, 100);
});

test("failures never contribute, even a failure carrying a latency value", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordFailed(log, "vigiles", "network_error", 50);
  recordFailed(log, "ignis", "http_error", 75);
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 1);
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 1, ignis: 0, sanitas: 0 });
});

test("a success-only log with no usable latency reads 0 everywhere", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "sanitas", null);
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 0);
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 0, ignis: 0, sanitas: 0 });
  assert.equal(stats.avgOkLatencyMs, null);
});

test("buckets plus unbucketed measurements equal the global count", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 200);
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 2);
  const bucketed = Object.values(stats.okLatencyCountByProduct).reduce((a, b) => a + b, 0);
  assert.equal(bucketed, 1);
});

test("an ok entry with an unknown product counts globally but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 200);
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 1, ignis: 0, sanitas: 0 });
  assert.equal(stats.okLatencyCount, 2);
  assert.equal(stats.avgOkLatencyMs, 150);
});

test("an ok entry with a missing product counts globally but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 100);
  recordOk(log, null, 300);
  const stats = log.stats();
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 0, ignis: 0, sanitas: 1 });
  assert.equal(stats.okLatencyCount, 2);
});

test("counts agree with the means they stand behind", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 200);
  recordOk(log, "ignis", 50);
  recordOk(log, "ignis", null);
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 3);
  assert.equal(stats.avgOkLatencyMs, (100 + 200 + 50) / 3);
  assert.equal(stats.avgOkLatencyMsByProduct.vigiles, 150);
  assert.equal(stats.avgOkLatencyMsByProduct.ignis, 50);
  assert.equal(stats.avgOkLatencyMsByProduct.sanitas, null);
  assert.equal(stats.okLatencyCountByProduct.sanitas, 0);
});

test("counts follow clear: back to zero", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 100);
  log.clear();
  const stats = log.stats();
  assert.equal(stats.okLatencyCount, 0);
  assert.deepEqual(stats.okLatencyCountByProduct, { vigiles: 0, ignis: 0, sanitas: 0 });
});

test("web wiring: updateLogStats renders the latency-count lines from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCount: \$\("log-stats-ok-latency-count"\)/);
  assert.match(app, /logStatsOkLatencyCountByProduct: \$\("log-stats-ok-latency-count-by-product"\)/);
  assert.match(
    app,
    /Successful latencies measured: \$\{stats\.okLatencyCount\}/,
    "updateLogStats sets the global latency-count line from stats()",
  );
  assert.match(
    app,
    /Successful latencies measured by product: Vigiles \$\{stats\.okLatencyCountByProduct\.vigiles\} · Ignis \$\{stats\.okLatencyCountByProduct\.ignis\} · Sanitas \$\{stats\.okLatencyCountByProduct\.sanitas\}/,
    "updateLogStats sets the per-product latency-count line from stats()",
  );
});

test("web wiring: session-log panel holds the latency-count stats elements", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count" class="note mono">Successful latencies measured: 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-by-product" class="note mono">Successful latencies measured by product: Vigiles 0 · Ignis 0 · Sanitas 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
