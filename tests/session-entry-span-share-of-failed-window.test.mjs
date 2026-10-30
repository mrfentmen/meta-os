// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-share-of-failed-window.test.mjs
//
// Hana DETAIL-67: the session-log panel gains a
// global entry-span-share-of-failed-window line,
// computed only from entries the log actually
// recorded. DETAIL-66 reads the recording window
// against the success window; its mirror reads
// the same recording window against the failure
// window, so a session whose recording ran four
// times as long as its failures reads that at a
// glance, where DETAIL-57's failed-span share of
// the entry window states the same relation from
// the other side. This re-bases DETAIL-24's global
// entry span on DETAIL-23's global failed span.
// Both spans are product-blind: any entry, of any
// status and any product, opens and closes the
// global entry span, and an unknown- or
// missing-product failure still opens and closes
// the global failed span, unlike DETAIL-53's and
// DETAIL-55's by-product buckets. This is a raw
// ratio, never clamped: a share above 1 is the
// normal case, since successes and latency-less
// entries stretch the recording window without
// moving the failed span, and a share below 1 or
// below 0 means timestamps ran out of insertion
// order, exactly as DETAIL-23's and DETAIL-24's
// raw spans do. Null with no usable failed window
// at all — an empty log, a single failure, or all
// failures at one timestamp — because a zero
// failed span has no share to divide, never NaN;
// null when failures were recorded but the global
// entry span is unknown (no usable timestamp pair
// — never a fabricated window); 0 when the first
// and last entries share one timestamp while
// failures stretch across a nonzero failed window.
// No sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOkAt(log, timestamp, product) {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

function recordAt(log, timestamp, product, status = "network_error") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: the share is null", () => {
  const log = new SessionLog();
  assert.equal(log.stats().entrySpanShareOfFailedWindow, null);
});

test("a single failure reads null: a zero failed span has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfFailedWindow, null);
});

test("all failures at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfFailedWindow, null);
});

test("a success-only log reads null: no failed window exists at all", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfFailedWindow, null);
});

test("the share is the entry span over the failed span, above 1 included", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "medicus");
  recordAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  // Entry span 11:00 to 13:00 = 7200000 ms; failed
  // span 12:00 to 13:00 = 3600000 ms, so the share
  // is 2 — the recording stretches twice as long
  // as its failures, and DETAIL-57's inverse share
  // reads 1/2 for the same session.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 7200000 / 3600000);
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 3600000 / 7200000);
});

test("exactly 1 when every entry is a failure spanning the whole recording", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T13:00:00.000Z", "ignis");
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 1);
});

test("an unknown-product success moves the numerator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T14:00:00.000Z", "mystery");
  // The mystery successes open and close the global
  // entry span (10800000 ms) and the Vigiles
  // failures open and close the global failed span
  // (3600000 ms), so the product-blind share reads
  // 3 even though no by-product bucket moved.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 10800000 / 3600000);
});

test("an unknown-product failure moves the denominator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T13:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T14:00:00.000Z", "vigiles");
  // Entry span 12:00 to 14:00 = 7200000 ms over the
  // mystery-driven failed span 12:00 to 13:00 =
  // 3600000 ms, so the share reads 2 even though
  // no by-product failed bucket moved.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 7200000 / 3600000);
});

test("a missing-product failure and success both move the product-blind spans", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T11:00:00.000Z", null);
  recordAt(log, "2026-10-29T13:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T14:00:00.000Z", null);
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 7200000 / 3600000);
});

test("failures with no usable timestamp pair read null, even with a spanning entry log", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "", "vigiles");
  // A Vigiles failure was recorded but its failed
  // window is unknown — null, never a fabricated
  // ratio against the successes' entry span.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, null);
});

test("first and last entries at one timestamp read 0 against a nonzero failed window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  // First entry 12:00, last entry 12:00: a
  // zero-length entry span over a 600000 ms failed
  // window reads 0 — the out-of-order reading,
  // kept raw.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 0);
});

test("out-of-order timestamps stay raw: the share can go below 1, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Entry span 12:00 to 12:10 = 600000 ms; failed
  // span 12:00 to 12:30 = 1800000 ms, so the share
  // reads 1/3 — the recording's last entry carries
  // an earlier timestamp than the last failure.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, 600000 / 1800000);
});

test("out-of-order timestamps stay raw: the share can go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  // Entry span 12:00 back to 11:00 = -3600000 ms
  // over failed span 1800000 ms, so the share
  // reads -2.
  assert.equal(log.stats().entrySpanShareOfFailedWindow, -3600000 / 1800000);
});

test("the share equals the DETAIL-24 span over the DETAIL-23 span", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "medicus");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfFailedWindow, stats.entrySpanMs / stats.failedSpanMs);
});

test("the share is the inverse of DETAIL-57 wherever both are nonzero", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfFailedWindow * stats.failedSpanShareOfEntryWindow, 1);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().entrySpanShareOfFailedWindow, null);
});

test("web wiring: updateLogStats renders the entry-span-share-of-failed-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanShareOfFailedWindow: \$\("log-stats-entry-span-share-of-failed-window"\)/);
  assert.match(
    app,
    /Entry-span share of failure window: \$\{stats\.entrySpanShareOfFailedWindow === null \? "none" : `\$\{Math\.round\(stats\.entrySpanShareOfFailedWindow \* 100\)\}%`}/,
    "updateLogStats sets the entry-span-share-of-failed-window line from stats()",
  );
});

test("web wiring: session-log panel holds the entry-span-share-of-failed-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-share-of-failed-window" class="note mono">Entry-span share of failure window: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
