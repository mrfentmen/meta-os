// Node built-in test runner, no dependencies:
//   node --test tests/session-first-last-entry.test.mjs
//
// Hana DETAIL-27: the session-log panel gains global first- and
// last-entry lines, naming the endpoints DETAIL-24's global
// entry span already spans — the first and last recorded entry
// timestamps, any status, across products — where the
// per-product DETAIL-15/16 lines alone do not say it at a
// glance. No new stats fields: stats() already exposes
// firstEntryAt/lastEntryAt, set by insertion order, so an
// entry of any status, with an unknown or missing product,
// still opens and closes these endpoints (the per-product
// buckets stay product-gated), and an entry without a usable
// timestamp leaves both endpoints in place. Each line renders
// "none" per endpoint with no usable entry, same
// always-renders shape as the other stats lines. No sampling,
// no model, no invented products.

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

test("empty log: both global entry endpoints are null, not fabricated timestamps", () => {
  const log = new SessionLog();
  assert.equal(log.stats().firstEntryAt, null);
  assert.equal(log.stats().lastEntryAt, null);
});

test("endpoints follow insertion order across products, not timestamp order", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:03:00.000Z", "sanitas");
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:05:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:03:00.000Z");
});

test("entries of either status move the endpoints: successes and failures both count", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "ok");
  recordAt(log, "2026-10-29T12:02:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:04:00.000Z", "vigiles", "ok");
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:04:00.000Z");
});

test("entries with an unknown product still open and close the global endpoints", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:05:00.000Z", "mystery");
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:05:00.000Z");
  assert.deepEqual(stats.firstEntryAtByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
  assert.deepEqual(stats.lastEntryAtByProduct, {
    vigiles: null,
    ignis: null,
    sanitas: null,
  });
  assert.equal(stats.total, 2);
});

test("entries with a missing product still open and close the global endpoints", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:05:00.000Z", null);
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:05:00.000Z");
});

test("an entry without a usable timestamp leaves the endpoints in place", () => {
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
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:05:00.000Z");
});

test("a timestamp-less first entry leaves the endpoints open for a later usable entry", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:05:00.000Z");
});

test("a single usable entry opens and closes both endpoints at the same timestamp", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "sanitas");
  const stats = log.stats();
  assert.equal(stats.firstEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.lastEntryAt, "2026-10-29T12:00:00.000Z");
  assert.equal(stats.entrySpanMs, 0);
});

test("endpoints follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().firstEntryAt, null);
  assert.equal(log.stats().lastEntryAt, null);
});

test("web wiring: updateLogStats renders the global first- and last-entry lines from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFirstEntry: \$\("log-stats-first-entry"\)/);
  assert.match(app, /logStatsLastEntry: \$\("log-stats-last-entry"\)/);
  assert.match(
    app,
    /First entry: \$\{stats\.firstEntryAt \?\? "none"\}/,
    "updateLogStats sets the global first-entry line from stats()",
  );
  assert.match(
    app,
    /Last entry: \$\{stats\.lastEntryAt \?\? "none"\}/,
    "updateLogStats sets the global last-entry line from stats()",
  );
});

test("web wiring: session-log panel holds the global first- and last-entry stats elements", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-first-entry" class="note mono">First entry: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
  assert.match(
    html,
    /<p id="log-stats-last-entry" class="note mono">Last entry: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
