// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span.test.mjs
//
// HANA Agent1 DETAIL-23 (mirroring Rowan DETAIL-22): the
// session-log panel gains a global failure-span line, computed
// only from entries the log actually recorded. The span is the
// milliseconds between the session's first and last recorded
// failure timestamps, across products — how long the session's
// failures stretch, where the per-product DETAIL-20 spans alone
// do not say it at a glance. It introduces the global
// firstFailedAt/lastFailedAt endpoints, mirroring DETAIL-22's
// firstOkAt/lastOkAt: successes never move an endpoint, a
// failure with an unknown or missing product still opens and
// closes the global span (the per-product buckets stay
// product-gated), and a failure without a usable timestamp
// leaves both endpoints in place. A session with exactly one
// usable failure reads 0, not null — one failure spans no time.
// An unparseable endpoint reads null, never NaN, and the
// difference is kept raw, not clamped: a negative span means
// failures were recorded out of timestamp order, which the
// insertion-order endpoints preserve honestly. Null with no
// usable failure pair, never a fabricated span. No sampling, no
// model, no invented products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordAt(log, timestamp, product, status = "network_error") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

test("empty log: global failure span is null, not a fabricated span", () => {
  const log = new SessionLog();
  assert.equal(log.stats().failedSpanMs, null);
  assert.equal(log.stats().firstFailedAt, null);
  assert.equal(log.stats().lastFailedAt, null);
});

test("span is last minus first failure across products, in whole milliseconds", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.500Z", "ignis");
  assert.equal(log.stats().failedSpanMs, 390500);
  assert.equal(log.stats().firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastFailedAt, "2026-10-29T12:06:30.500Z");
});

test("a session with exactly one usable failure reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  assert.equal(log.stats().failedSpanMs, 0);
});

test("successes between failures never move the span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis", "ok");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanMs, 240000);
  assert.equal(log.stats().firstFailedAt, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastFailedAt, "2026-10-29T12:04:00.000Z");
});

test("a session with no failure reads null even when successes exist", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles", "ok");
  recordAt(log, "2026-10-29T12:03:00.000Z", "sanitas", "ok");
  assert.equal(log.stats().failedSpanMs, null);
});

test("failures with an unknown product still open and close the global span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.equal(log.stats().failedSpanMs, 300000);
  assert.deepEqual(log.stats().failedSpanMsByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
  assert.equal(log.stats().total, 2);
});

test("failures with a missing product still open and close the global span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", null);
  assert.equal(log.stats().failedSpanMs, 300000);
});

test("a failure without a usable timestamp leaves the span in place", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: null,
    status: "network_error",
    error: "boom",
  });
  assert.equal(log.stats().failedSpanMs, 300000);
});

test("a timestamp-less first failure leaves the span open for a later usable failure", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanMs, 300000);
  assert.equal(log.stats().firstFailedAt, "2026-10-29T12:00:00.000Z");
});

test("an unparseable endpoint timestamp reads null, never NaN", () => {
  const log = new SessionLog();
  recordAt(log, "not-a-timestamp", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanMs, null);
  assert.equal(log.stats().firstFailedAt, "not-a-timestamp");
});

test("out-of-order failures keep a raw negative span, not a clamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanMs, -300000);
});

test("failure spans follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().failedSpanMs, null);
  assert.equal(log.stats().firstFailedAt, null);
});

test("web wiring: updateLogStats renders the global failure-span line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpan: \$\("log-stats-failed-span"\)/);
  assert.match(
    app,
    /Failure span: \$\{stats\.failedSpanMs === null \? "none" : `\$\{stats\.failedSpanMs\} ms`\}/,
    "updateLogStats sets the global failure-span line from stats()",
  );
});

test("web wiring: session-log panel holds the global failure-span stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span" class="note mono">Failure span: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
