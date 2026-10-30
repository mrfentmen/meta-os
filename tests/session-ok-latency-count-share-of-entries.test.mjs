// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-of-entries.test.mjs
//
// Hana DETAIL-49: the session-log panel gains a global
// (renumbered after Rowan's distinct DETAIL-48, ok-span
// shares, landed first; both sides kept in the merge)
// usable-latency-count share of all entries line, computed
// only from entries the log actually recorded. DETAIL-47
// split the measurement count per product over the
// entry total, but three product shares cannot say in one
// number what slice of everything recorded carries a
// usable latency: a session where half of everything
// recorded is a measurement reads differently from one
// where measurements are a thin slice of a noisy log.
// This collapses DETAIL-47's shares into the DETAIL-36
// global count over the session's total entry count.
// The denominator is the entry total, not the measurement
// count, so the null rule matches DETAIL-47 on purpose:
// an empty log reads null (nothing to divide by), but
// once the log holds any entry, a session with no usable
// latency reads 0, never "none" — a failure-only log and
// a success-only log with no finite latency alike read 0.
// Unlike DETAIL-47, an unknown- or missing-product
// success still moves this share, since the global count
// is product-blind: it equals the sum of DETAIL-47's
// shares only when every usable-latency success carries
// a known product. Failures never move the share, even
// a failure carrying a latency value, and an ok entry
// with no finite latency is skipped as a measurement but
// still sits in the denominator as an entry. A 0 ms
// latency still counts as a measurement, exactly as in
// DETAIL-45/47. No sampling, no model, no invented
// measurements.

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

test("empty log: the global share is null", () => {
  const log = new SessionLog();
  assert.equal(log.stats().okLatencyCountShareOfEntries, null);
});

test("a single success reads 1", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 1);
});

test("the share divides by the entry total, not the measurement count", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", 300);
  recordOk(log, "medicus", 100);
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  // Four measurements over 6 entries — DETAIL-45's
  // measurement-total global share for the same log
  // would be 1, and DETAIL-47's product shares would
  // be 1/3, 1/6, 1/6.
  assert.equal(log.stats().okLatencyCountShareOfEntries, 2 / 3);
});

test("a latency-less success sits in the denominator but moves no measurement", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", 200);
  recordFailed(log, "medicus");
  // DETAIL-41's global ok share here would be 3/4;
  // the latency-count share is 2/4.
  assert.equal(log.stats().okLatencyCountShareOfEntries, 0.5);
});

test("the share equals the sum of DETAIL-47's shares when every usable-latency success carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordFailed(log, "medicus");
  const stats = log.stats();
  const sum = Object.values(stats.okLatencyCountShareOfEntriesByProduct).reduce((a, b) => a + b, 0);
  assert.equal(stats.okLatencyCountShareOfEntries, 2 / 3);
  assert.equal(stats.okLatencyCountShareOfEntries, sum);
  assert.equal(stats.okLatencyCountShareOfEntries, stats.okLatencyCount / stats.total);
});

test("an unknown-product success moves the global share but no DETAIL-47 bucket", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 1);
  const shares = log.stats().okLatencyCountShareOfEntriesByProduct;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, 0.5);
});

test("a missing-product success moves the global share but no DETAIL-47 bucket", () => {
  const log = new SessionLog();
  recordOk(log, "medicus", 100);
  recordOk(log, null, 300);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 1);
  assert.deepEqual(log.stats().okLatencyCountShareOfEntriesByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0.5,
  });
});

test("failures never move the share, and a failure-only log reads 0, not null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.equal(log.stats().okLatencyCountShareOfEntries, 0);
  recordOk(log, "ignis", 200);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 1 / 3);
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 0.5);
});

test("an ok entry with no finite latency is skipped as a measurement but counts as an entry", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "medicus", null);
  // DETAIL-45 for the same log would read 1; here the
  // entry total is 3, so the share is 1/3.
  assert.equal(log.stats().okLatencyCountShareOfEntries, 1 / 3);
});

test("a success-only log with no finite latency reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 0);
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const share = log.stats().okLatencyCountShareOfEntries;
  assert.equal(share, 1);
  assert.equal(Number.isNaN(share), false);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.equal(log.stats().okLatencyCountShareOfEntries, null);
});

test("web wiring: updateLogStats renders the ok-latency-count-share-of-entries line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareOfEntries: \$\("log-stats-ok-latency-count-share-of-entries"\)/);
  assert.match(
    app,
    /Successful latency-measurement share of all entries: \$\{stats\.okLatencyCountShareOfEntries === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfEntries \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-of-entries line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-of-entries stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-of-entries" class="note mono">Successful latency-measurement share of all entries: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
