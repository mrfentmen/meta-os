// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span.test.mjs
//
// Rowan DETAIL-24 (mirroring Hana DETAIL-23 / Rowan DETAIL-22): the
// session-log panel gains a global entry-span line, computed
// only from entries the log actually recorded. The span is the
// milliseconds between the session's first and last recorded
// entry timestamps, across products and across statuses — how
// long the session's recorded activity stretches, where the
// per-product DETAIL-17 spans alone do not say it at a glance.
// It introduces the global firstEntryAt/lastEntryAt endpoints,
// mirroring DETAIL-22's firstOkAt/lastOkAt: an entry of any
// status, with an unknown or missing product, still opens and
// closes the global span (the per-product buckets stay
// product-gated), and an entry without a usable timestamp
// leaves both endpoints in place. A session with exactly one
// usable entry reads 0, not null — one entry spans no time.
// An unparseable endpoint reads null, never NaN, and the
// difference is kept raw, not clamped: a negative span means
// entries were recorded out of timestamp order, which the
// insertion-order endpoints preserve honestly. Null with no
// usable entry pair, never a fabricated span. No sampling, no
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

test("empty log: global entry span is null, not a fabricated span", () => {
  const log = new SessionLog();
  assert.equal(log.stats().entrySpanMs, null);
  assert.equal(log.stats().firstEntryAt, null);
  assert.equal(log.stats().lastEntryAt, null);
});

test("span is last minus first entry across products, in whole milliseconds", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.500Z", "ignis");
  assert.equal(log.stats().entrySpanMs, 390500);
  assert.equal(log.stats().firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastEntryAt, "2026-10-29T12:06:30.500Z");
});

test("a session with exactly one usable entry reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  assert.equal(log.stats().entrySpanMs, 0);
});

test("entries of either status move the span: successes and failures both count", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "ok");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles", "ok");
  assert.equal(log.stats().entrySpanMs, 240000);
  assert.equal(log.stats().firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastEntryAt, "2026-10-29T12:04:00.000Z");
});

test("entries with an unknown product still open and close the global span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  assert.equal(log.stats().entrySpanMs, 300000);
  assert.deepEqual(log.stats().entrySpanMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
  assert.equal(log.stats().total, 2);
});

test("entries with a missing product still open and close the global span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", null);
  assert.equal(log.stats().entrySpanMs, 300000);
});

test("an entry without a usable timestamp leaves the span in place", () => {
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
  assert.equal(log.stats().entrySpanMs, 300000);
});

test("a timestamp-less first entry leaves the span open for a later usable entry", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().entrySpanMs, 300000);
  assert.equal(log.stats().firstEntryAt, "2026-10-29T12:00:00.000Z");
});

test("an unparseable endpoint timestamp reads null, never NaN", () => {
  const log = new SessionLog();
  recordAt(log, "not-a-timestamp", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().entrySpanMs, null);
  assert.equal(log.stats().firstEntryAt, "not-a-timestamp");
});

test("out-of-order entries keep a raw negative span, not a clamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  assert.equal(log.stats().entrySpanMs, -300000);
});

test("entry spans follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().entrySpanMs, null);
  assert.equal(log.stats().firstEntryAt, null);
});

test("global entry span covers the per-product spans: it is at least as wide as each", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles", "ok");
  recordAt(log, "2026-10-29T12:03:00.000Z", "vigiles", "ok");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:00.000Z", "ignis");
  const stats = log.stats();
  assert.equal(stats.entrySpanMs, 360000);
  assert.equal(stats.entrySpanMsByProduct.vigiles, 180000);
  assert.equal(stats.entrySpanMsByProduct.ignis, 300000);
});

test("web wiring: updateLogStats renders the global entry-span line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpan: \$\("log-stats-entry-span"\)/);
  assert.match(
    app,
    /Entry span: \$\{stats\.entrySpanMs === null \? "none" : `\$\{stats\.entrySpanMs\} ms`\}/,
    "updateLogStats sets the global entry-span line from stats()",
  );
});

test("web wiring: session-log panel holds the global entry-span stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span" class="note mono">Entry span: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
