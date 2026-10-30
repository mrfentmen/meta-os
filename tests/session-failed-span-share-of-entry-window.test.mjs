// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-of-entry-window.test.mjs
//
// Hana DETAIL-57: the session-log panel gains a global
// failed-span-share-of-entry-window line, computed only
// from entries the log actually recorded. DETAIL-55's
// per-product shares say how much of the session's whole
// recording window each product's failures cover, but not
// how much of the window failures covered in total: three
// product shares that overlap cannot just be added. This
// re-bases DETAIL-23's global failed span on the session's
// global entry span (DETAIL-24), so a session where
// failures stretch across half the whole recording window
// reads that at a glance — the collapsed form of
// DETAIL-55's shares, and the failed mirror of the
// global entry-window share the ok-span family still
// lacks. The denominator is the global first-to-last entry
// window, not a sum of product failed windows, so this is
// a raw ratio, never clamped, and it is NOT the sum of
// DETAIL-55's shares: product failed windows overlap, and
// a share above 1 or below 0 means timestamps ran out of
// insertion order, exactly as DETAIL-23's raw span does.
// Any entry moves the denominator's endpoints, so
// successes stretch the window without moving the
// numerator. The numerator is product-blind, unlike
// DETAIL-55: a failure with an unknown or missing product
// still opens and closes the global failed span, so it
// moves this share where it moves no DETAIL-55 bucket.
// Null when the session holds no usable entry window at
// all — an empty log, a single entry, or all entries at
// one timestamp — because a zero global entry span has no
// share to divide, never NaN; null when failures were
// recorded but the global failed span is unknown (no
// usable timestamp pair — never a fabricated window); 0
// with no failures once a nonzero entry window exists,
// because failures covered none of the window, and 0 for
// a single-failure session, whose zero-length failed
// window covers none of a nonzero window. No sampling,
// no model, no invented measurements.

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
  assert.equal(log.stats().failedSpanShareOfEntryWindow, null);
});

test("a single entry reads null: a zero global entry span has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfEntryWindow, null);
});

test("all entries at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  assert.equal(log.stats().failedSpanShareOfEntryWindow, null);
});

test("successes stretch the denominator without moving the numerator", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "ignis");
  // Global entry window is 7200000 ms (11:00 to 13:00);
  // the global failed span covers 600000 of it. Under
  // DETAIL-50 the denominator would be the 600000 ms
  // failed window and the share would read 1; here the
  // successes stretch it.
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 600000 / 7200000);
});

test("a failures-only session reads 1: the failed span is the whole window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 1);
});

test("no failures once a nonzero entry window exists reads 0, not null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 0);
});

test("a single failure inside a nonzero entry window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "medicus");
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 0);
});

test("an unknown-product failure moves the product-blind numerator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "medicus");
  // Global entry window is 1200000 ms; the global failed
  // span covers 600000 of it, and the mystery failure
  // opened that span where it moves no DETAIL-55 bucket.
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 0.5);
});

test("a missing-product failure moves the product-blind numerator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "medicus");
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 0.5);
});

test("failures with no usable timestamp pair read null, distinct from a no-failure session's 0", () => {
  const log = new SessionLog();
  recordAt(log, "", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  // A failure was recorded but the global failed window
  // is unknown — null, never a fabricated 0 — while a
  // session with no failures at all reads 0 here.
  assert.equal(log.stats().failedSpanShareOfEntryWindow, null);
});

test("out-of-order timestamps stay raw: the share can go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  // Global entry window: first recorded entry 12:10 to
  // last recorded entry 12:20 = 600000 ms. Global failed
  // span: 12:10 back to 12:00 = -600000 (-1 of the window).
  assert.equal(log.stats().failedSpanShareOfEntryWindow, -1);
});

test("out-of-order timestamps stay raw: the share can exceed 1, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  // Global entry window: first recorded entry 12:00 to
  // last recorded entry 12:10 = 600000 ms, but the global
  // failed span runs 12:00 to 12:30 = 1800000 ms, so the
  // share reads 3 — the honest reading of a window whose
  // last recorded entry carries an earlier timestamp.
  assert.equal(log.stats().failedSpanShareOfEntryWindow, 3);
});

test("the share equals the DETAIL-23 span over the DETAIL-24 span", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "medicus");
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfEntryWindow, stats.failedSpanMs / stats.entrySpanMs);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().failedSpanShareOfEntryWindow, null);
});

test("web wiring: updateLogStats renders the failed-span-share-of-entry-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareOfEntryWindow: \$\("log-stats-failed-span-share-of-entry-window"\)/);
  assert.match(
    app,
    /Failure-span share of entry window: \$\{stats\.failedSpanShareOfEntryWindow === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareOfEntryWindow \* 100\)\}%`\}/,
    "updateLogStats sets the failed-span-share-of-entry-window line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-span-share-of-entry-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-span-share-of-entry-window" class="note mono">Failure-span share of entry window: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
