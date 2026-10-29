// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-latency-count-share-of-ok.test.mjs
//
// Hana DETAIL-51: the session-log panel gains a global
// usable-latency-count share of ok successes line,
// computed only from entries the log actually recorded.
// DETAIL-49 split the measurement count over the entry
// total, but an entry-total share cannot say in one
// number what slice of the successes themselves carry a
// usable latency: a session where three of four
// successes are measurements reads differently from one
// where the same three measurements sit in a log full
// of failures. This re-bases the DETAIL-36 global count
// on the session's ok total, reusing DETAIL-37's
// shareOfAllOk helper. The denominator is the ok total,
// not the entry total and not the measurement count, so
// the null rule differs from DETAIL-49 on purpose: an
// empty log and a failure-only log alike read null
// (nothing to divide by), but once the session holds
// any success, a session with no usable latency reads
// 0, never "none" — a success-only log with no finite
// latency reads 0. Failures sit in neither side: they
// are not in the ok total and never count as
// measurements, even a failure carrying a latency value.
// An ok entry with no finite latency sits in the
// denominator but moves no measurement, and an unknown-
// or missing-product success still moves this share,
// since the global count is product-blind. A 0 ms
// latency still counts as a measurement, exactly as in
// DETAIL-45/47/49. No sampling, no model, no invented
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
  assert.equal(log.stats().okLatencyCountShareOfOk, null);
});

test("a single success reads 1", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 250);
  assert.equal(log.stats().okLatencyCountShareOfOk, 1);
});

test("the share divides by the ok total, not the entry total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 100);
  recordOk(log, "ignis", null);
  recordFailed(log, "vigiles");
  recordFailed(log, "ignis", "http_error");
  // Two measurements over three successes — DETAIL-49's
  // entry-total share for the same log would be 2/5,
  // and DETAIL-45's measurement-total global share
  // would be 1.
  assert.equal(log.stats().okLatencyCountShareOfOk, 2 / 3);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 2 / 5);
});

test("a latency-less success sits in the denominator but moves no measurement", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", 200);
  recordFailed(log, "sanitas");
  assert.equal(log.stats().okLatencyCountShareOfOk, 2 / 3);
});

test("the share equals the DETAIL-36 count over the ok total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 40);
  recordOk(log, "ignis", 60);
  recordOk(log, "sanitas", null);
  recordFailed(log, "sanitas");
  const stats = log.stats();
  assert.equal(stats.okLatencyCountShareOfOk, 2 / 3);
  assert.equal(stats.okLatencyCountShareOfOk, stats.okLatencyCount / stats.ok);
});

test("an unknown-product success moves the global share", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 100);
  recordOk(log, "mystery", 100);
  assert.equal(log.stats().okLatencyCountShareOfOk, 1);
});

test("a missing-product success moves the global share", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas", 100);
  recordOk(log, null, null);
  // One measurement over two successes.
  assert.equal(log.stats().okLatencyCountShareOfOk, 0.5);
});

test("a failure-only log reads null, not 0 — unlike DETAIL-49", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.equal(log.stats().okLatencyCountShareOfOk, null);
  assert.equal(log.stats().okLatencyCountShareOfEntries, 0);
  recordOk(log, "ignis", 200);
  assert.equal(log.stats().okLatencyCountShareOfOk, 1);
});

test("a failure carrying a latency value never counts as a measurement", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error", 500);
  recordOk(log, "ignis", 100);
  assert.equal(log.stats().okLatencyCountShareOfOk, 1);
});

test("an ok entry with no finite latency is skipped as a measurement but counts as a success", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", Number.NaN);
  recordOk(log, "ignis", 200);
  recordOk(log, "sanitas", null);
  // DETAIL-45 for the same log would read 1; here the
  // ok total is 3, so the share is 1/3.
  assert.equal(log.stats().okLatencyCountShareOfOk, 1 / 3);
});

test("a success-only log with no finite latency reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", null);
  recordOk(log, "ignis", Number.NaN);
  assert.equal(log.stats().okLatencyCountShareOfOk, 0);
});

test("zero-millisecond successes still count as measurements", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 0);
  recordOk(log, "ignis", 0);
  const share = log.stats().okLatencyCountShareOfOk;
  assert.equal(share, 1);
  assert.equal(Number.isNaN(share), false);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 200);
  log.clear();
  assert.equal(log.stats().okLatencyCountShareOfOk, null);
});

test("web wiring: updateLogStats renders the ok-latency-count-share-of-ok line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkLatencyCountShareOfOk: \$\("log-stats-ok-latency-count-share-of-ok"\)/);
  assert.match(
    app,
    /Successful latency-measurement share of successes: \$\{stats\.okLatencyCountShareOfOk === null \? "none" : `\$\{Math\.round\(stats\.okLatencyCountShareOfOk \* 100\)\}%`\}/,
    "updateLogStats sets the ok-latency-count-share-of-ok line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-latency-count-share-of-ok stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-latency-count-share-of-ok" class="note mono">Successful latency-measurement share of successes: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
