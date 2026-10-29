// Node built-in test runner, no dependencies:
//   node --test tests/session-latency-sum.test.mjs
//
// HANA DETAIL-38: the session-log panel gains usable-latency
// sum lines, computed only from entries the log actually
// recorded. DETAIL-4's mean and DETAIL-8's per-product means
// say how slow successes were on average, and DETAIL-35's
// shares say what slice of the total each product ate, but
// never the total itself — a share of half the total reads
// differently against 200 ms than against 20,000 ms. This
// exposes the sums behind those means and shares: no new
// summing rule, the stats loop already sums usable latencies
// for the means and shares. Always plain sums, never null:
// a session or product with no usable latency reads 0.
// Failures never contribute, even a failure carrying a
// latency value; an ok entry with no finite latency is
// skipped rather than summed as zero; and an ok entry with
// an unknown or missing product sums globally but moves no
// bucket, exactly as DETAIL-4/8/35 do. No sampling, no
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

test("empty log: the global sum is 0 and every product reads 0", () => {
  const log = new SessionLog();
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 0);
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 0, ignis: 0, sanitas: 0 });
});

test("ok entries with a usable latency sum globally and per product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 200);
  recordOk(log, "ignis", 150);
  recordOk(log, "sanitas", 120);
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 570);
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 300, ignis: 150, sanitas: 120 });
});

test("an ok entry with no usable latency is skipped, never summed as zero", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  recordOk(log, "sanitas", Number.POSITIVE_INFINITY);
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 100);
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 100, ignis: 0, sanitas: 0 });
  assert.equal(stats.avgOkLatencyMs, 100);
});

test("failures never contribute, even a failure carrying a latency value", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordFailed(log, "vigiles", "network_error", 50);
  recordFailed(log, "ignis", "http_error", 75);
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 100);
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 100, ignis: 0, sanitas: 0 });
});

test("a success-only log with no usable latency reads 0 everywhere", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "sanitas", null);
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 0);
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 0, ignis: 0, sanitas: 0 });
  assert.equal(stats.avgOkLatencyMs, null);
});

test("buckets plus unbucketed measurements equal the global sum", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 200);
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 300);
  const bucketed = Object.values(stats.okLatencySumByProduct).reduce((a, b) => a + b, 0);
  assert.equal(bucketed, 100);
});

test("an ok entry with an unknown product sums globally but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 200);
  const stats = log.stats();
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 100, ignis: 0, sanitas: 0 });
  assert.equal(stats.okLatencySum, 300);
  assert.equal(stats.avgOkLatencyMs, 150);
});

test("an ok entry with a missing product sums globally but moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 100);
  recordOk(log, null, 300);
  const stats = log.stats();
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 0, ignis: 0, sanitas: 100 });
  assert.equal(stats.okLatencySum, 400);
});

test("sums agree with the means and shares they stand behind", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 200);
  recordOk(log, "ignis", 50);
  recordOk(log, "ignis", null);
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 350);
  assert.equal(stats.avgOkLatencyMs, 350 / 3);
  assert.equal(stats.avgOkLatencyMsByProduct.vigiles, 150);
  assert.equal(stats.avgOkLatencyMsByProduct.ignis, 50);
  assert.equal(stats.okLatencySumByProduct.sanitas, 0);
  assert.equal(stats.okLatencyShareByProduct.vigiles, 300 / 350);
  assert.equal(stats.okLatencyShareByProduct.ignis, 50 / 350);
  assert.equal(stats.okLatencyShareByProduct.sanitas, 0);
});

test("sums follow clear: back to zero", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 100);
  log.clear();
  const stats = log.stats();
  assert.equal(stats.okLatencySum, 0);
  assert.deepEqual(stats.okLatencySumByProduct, { vigiles: 0, ignis: 0, sanitas: 0 });
});

test("web wiring: updateLogStats renders the latency-sum lines from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencySum: \$\("log-stats-ok-latency-sum"\)/);
  assert.match(app, /logStatsOkLatencySumByProduct: \$\("log-stats-ok-latency-sum-by-product"\)/);
  assert.match(
    app,
    /Total successful latency: \$\{Math\.round\(stats\.okLatencySum\)\} ms/,
    "updateLogStats sets the global latency-sum line from stats()",
  );
  assert.match(
    app,
    /Total successful latency by product: Vigiles \$\{Math\.round\(stats\.okLatencySumByProduct\.vigiles\)\} ms · Ignis \$\{Math\.round\(stats\.okLatencySumByProduct\.ignis\)\} ms · Sanitas \$\{Math\.round\(stats\.okLatencySumByProduct\.sanitas\)\} ms/,
    "updateLogStats sets the per-product latency-sum line from stats()",
  );
});

test("web wiring: session-log panel holds the latency-sum stats elements", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-sum" class="note mono">Total successful latency: 0 ms<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
  assert.match(
    html,
    /<p id="log-stats-ok-latency-sum-by-product" class="note mono">Total successful latency by product: Vigiles 0 ms · Ignis 0 ms · Sanitas 0 ms<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
