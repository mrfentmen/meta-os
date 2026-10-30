// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-span.test.mjs
//
// Rowan DETAIL-22 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a global success-span
// line, computed only from entries the log actually recorded. The
// span is the milliseconds between the session's first and last
// recorded success timestamps, across products — how long the
// session's successes stretch, where the per-product DETAIL-21
// spans alone do not say it at a glance. Derived only from the
// global firstOkAt/lastOkAt endpoints, so the same endpoint rules
// apply: failures never move an endpoint, a success with an unknown
// or missing product still opens and closes the global span (the
// per-product buckets stay product-gated), and a success without a
// usable timestamp leaves both endpoints in place. A session with
// exactly one usable success reads 0, not null — one success spans
// no time. An unparseable endpoint reads null, never NaN, and the
// difference is kept raw, not clamped: a negative span means
// successes were recorded out of timestamp order, which the
// insertion-order endpoints preserve honestly. Null with no usable
// success pair, never a fabricated span. No sampling, no model, no
// invented products.

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

test("empty log: global success span is null, not a fabricated span", () => {
  const log = new SessionLog();
  assert.equal(log.stats().okSpanMs, null);
  assert.equal(log.stats().firstOkAt, null);
  assert.equal(log.stats().lastOkAt, null);
});

test("span is last minus first success across products, in whole milliseconds", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.500Z", "ignis");
  assert.equal(log.stats().okSpanMs, 390500);
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastOkAt, "2026-10-29T12:06:30.500Z");
});

test("a session with exactly one usable success reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  assert.equal(log.stats().okSpanMs, 0);
});

test("failures between successes never move the span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis", "network_error");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanMs, 240000);
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastOkAt, "2026-10-29T12:04:00.000Z");
});

test("a session with no success reads null even when failures exist", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles", "network_error");
  recordAt(log, "2026-10-29T12:03:00.000Z", "medicus", "http_error");
  assert.equal(log.stats().okSpanMs, null);
});

test("successes with an unknown product still open and close the global span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.equal(log.stats().okSpanMs, 300000);
  assert.deepEqual(log.stats().okSpanMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
  assert.equal(log.stats().total, 2);
});

test("successes with a missing product still open and close the global span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", null);
  assert.equal(log.stats().okSpanMs, 300000);
});

test("a success without a usable timestamp leaves the span in place", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: { product: "ignis" },
  });
  assert.equal(log.stats().okSpanMs, 300000);
});

test("a timestamp-less first success leaves the span open for a later usable success", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().okSpanMs, 300000);
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:00:00.000Z");
});

test("an unparseable endpoint timestamp reads null, never NaN", () => {
  const log = new SessionLog();
  recordAt(log, "not-a-timestamp", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().okSpanMs, null);
  assert.equal(log.stats().firstOkAt, "not-a-timestamp");
});

test("out-of-order successes keep a raw negative span, not a clamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  assert.equal(log.stats().okSpanMs, -300000);
});

test("success spans follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().okSpanMs, null);
  assert.equal(log.stats().firstOkAt, null);
});

test("web wiring: updateLogStats renders the global success-span line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkSpan: \$\("log-stats-ok-span"\)/);
  assert.match(
    app,
    /Success span: \$\{stats\.okSpanMs === null \? "none" : `\$\{stats\.okSpanMs\} ms`\}/,
    "updateLogStats sets the global success-span line from stats()",
  );
});

test("web wiring: session-log panel holds the global success-span stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-span" class="note mono">Success span: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
