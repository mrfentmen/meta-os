// Node built-in test runner, no dependencies:
//   node --test tests/session-first-ok.test.mjs
//
// Hana DETAIL-30: the session-log panel gains a global
// first-success line, naming the endpoint DETAIL-22's global
// success span already spans — the session's first recorded
// success timestamp, across products — where the per-product
// DETAIL-18 line alone does not say it at a glance, and where
// DETAIL-3's last-success line alone does not say when the
// session's successes began. No new stats fields: stats()
// already exposes firstOkAt, set once by insertion order, so
// a success with an unknown or missing product still opens it
// (the per-product buckets stay product-gated), a
// timestamp-less success leaves it open for a later usable
// success, and failures never move it. The line renders
// "none" with no usable success, same always-renders shape as
// the other stats lines. No sampling, no model, no invented
// products.

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

test("empty log: the global first success is null, not a fabricated timestamp", () => {
  const log = new SessionLog();
  assert.equal(log.stats().firstOkAt, null);
});

test("first success follows insertion order across products, not timestamp order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:03:00.000Z", "medicus");
  const stats = log.stats();
  assert.equal(stats.firstOkAt, "2026-10-29T12:05:00.000Z");
  assert.equal(stats.lastOkAt, "2026-10-29T12:03:00.000Z");
});

test("failures never move the first success, before or after it", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "network_error");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles", "http_error");
  const stats = log.stats();
  assert.equal(stats.firstOkAt, "2026-10-29T12:02:00.000Z");
  assert.equal(stats.lastOkAt, "2026-10-29T12:02:00.000Z");
});

test("a success with an unknown product still opens the global first success", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  const stats = log.stats();
  assert.equal(stats.firstOkAt, "2026-10-29T12:00:00.000Z");
  assert.deepEqual(stats.firstOkAtByProduct, {
    vigiles: null,
    ignis: "2026-10-29T12:05:00.000Z",
    medicus: null,
  });
  assert.equal(stats.ok, 2);
});

test("a success with a missing product still opens the global first success", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:00:00.000Z");
});

test("a timestamp-less success leaves the first success in place", () => {
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
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:00:00.000Z");
});

test("a timestamp-less first success leaves the endpoint open for a later usable success", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:00:00.000Z");
});

test("a single usable success opens first and last at the same timestamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  const stats = log.stats();
  assert.equal(stats.firstOkAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastOkAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.okSpanMs, 0);
});

test("a later success never overwrites the first success, even with an earlier timestamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  assert.equal(log.stats().firstOkAt, "2026-10-29T12:05:00.000Z");
});

test("first success follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().firstOkAt, null);
});

test("web wiring: updateLogStats renders the global first-success line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFirstOk: \$\("log-stats-first-ok"\)/);
  assert.match(
    app,
    /First successful assessment: \$\{stats\.firstOkAt \?\? "none"\}/,
    "updateLogStats sets the global first-success line from stats()",
  );
});

test("web wiring: session-log panel holds the global first-success stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-first-ok" class="note mono">First successful assessment: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
