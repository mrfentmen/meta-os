// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-span-share-of-ok-window.test.mjs
//
// Hana DETAIL-65: the session-log panel gains a
// global failed-span-share-of-ok-window line,
// computed only from entries the log actually
// recorded. DETAIL-57's and DETAIL-58's shares say
// how much of the whole recording window failures
// and successes each cover, but not how the two
// windows compare to each other: a session where
// failures stretched twice as long as successes
// reads the same entry-window shares as one where
// the success window is the longer of the two. This
// re-bases DETAIL-23's global failed span on
// DETAIL-22's global ok span, so the failure window
// reads against the success window directly — the
// mirror of DETAIL-64, the cross-span re-base the
// entry-window shares imply but do not state from
// the other side. Both spans are product-blind:
// an unknown- or missing-product failure still
// opens and closes the global failed span, and an
// unknown- or missing-product success still opens
// and closes the global ok span, unlike
// DETAIL-53's and DETAIL-55's by-product buckets.
// This is a raw ratio, never clamped, and a share
// above 1 or below 0 means timestamps ran out of
// insertion order, exactly as DETAIL-22's and
// DETAIL-23's raw spans do. Null with no usable
// ok window at all — an empty log, a single
// success, or all successes at one timestamp —
// because a zero ok span has no share to divide,
// never NaN; null when failures were recorded but
// the global failed span is unknown (no usable
// timestamp pair — never a fabricated window);
// 0 with no failures once a nonzero ok window
// exists, because failures covered none of the
// success window, and 0 for a single-failure
// session, whose zero-length failed window covers
// none of a nonzero ok window.
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
  assert.equal(log.stats().failedSpanShareOfOkWindow, null);
});

test("a single success reads null: a zero ok span has no share to divide", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOkWindow, null);
});

test("all successes at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOkWindow, null);
});

test("a failure-only log reads null: no ok window exists at all", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOkWindow, null);
});

test("no failures once a nonzero ok window exists reads 0, not null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.equal(log.stats().failedSpanShareOfOkWindow, 0);
});

test("a single failure inside a nonzero ok window reads 0", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  assert.equal(log.stats().failedSpanShareOfOkWindow, 0);
});

test("the share is the failed span over the ok span, above 1 included", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "sanitas");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  // Failed span 11:00 to 12:30 = 5400000 ms; ok span
  // 12:00 to 13:00 = 3600000 ms, so the share is
  // 3/2 — failures stretched half again as long as
  // successes, and the entry-window shares alone do
  // not say that.
  assert.equal(log.stats().failedSpanShareOfOkWindow, 5400000 / 3600000);
});

test("the share below 1: a short failed span against a long ok window", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "sanitas");
  // Failed span 600000 ms over ok span 7200000 ms.
  assert.equal(log.stats().failedSpanShareOfOkWindow, 600000 / 7200000);
});

test("an unknown-product failure moves the numerator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  // The mystery failures open and close the global
  // failed span (1800000 ms) and the Vigiles
  // successes open and close the global ok span
  // (600000 ms), so the product-blind share reads
  // 3 even though no by-product bucket moved.
  assert.equal(log.stats().failedSpanShareOfOkWindow, 1800000 / 600000);
  // DETAIL-55 reads 0 per product with no failures
  // once a nonzero global entry window exists, so
  // Ignis and Sanitas read 0 here, not null.
  assert.deepEqual(log.stats().failedSpanShareOfEntryWindowByProduct, {
    vigiles: 0,
    ignis: 0,
    sanitas: 0,
  });
});

test("an unknown-product success moves the denominator, unlike DETAIL-53", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  // Failed span 600000 ms over the mystery-driven ok
  // span 1800000 ms, so the share reads 1/3 even
  // though no by-product ok bucket moved.
  assert.equal(log.stats().failedSpanShareOfOkWindow, 600000 / 1800000);
});

test("a missing-product failure and success both move the product-blind spans", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:10:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:30:00.000Z", null);
  assert.equal(log.stats().failedSpanShareOfOkWindow, 600000 / 1800000);
});

test("failures with no usable timestamp pair read null, distinct from a no-failure log's 0", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "", "vigiles");
  // A Vigiles failure was recorded but its failed
  // window is unknown — null, never a fabricated 0.
  assert.equal(log.stats().failedSpanShareOfOkWindow, null);
});

test("out-of-order timestamps stay raw: the share can go negative, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  // Ok span 12:00 to 12:30 = 1800000 ms; failed span
  // 12:10 back to 12:00 = -600000 ms, so the share
  // reads -1/3.
  assert.equal(log.stats().failedSpanShareOfOkWindow, -600000 / 1800000);
});

test("out-of-order timestamps stay raw: the share can exceed 1, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  // Ok span 600000 ms, but the failed span runs
  // 12:00 to 12:30 = 1800000 ms, so the share reads
  // 3 — the honest reading of a success window whose
  // last recorded success carries an earlier
  // timestamp than the last failure.
  assert.equal(log.stats().failedSpanShareOfOkWindow, 3);
});

test("the share equals the DETAIL-23 span over the DETAIL-22 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "sanitas");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.failedSpanShareOfOkWindow, stats.failedSpanMs / stats.okSpanMs);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().failedSpanShareOfOkWindow, null);
});

test("web wiring: updateLogStats renders the failed-span-share-of-ok-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedSpanShareOfOkWindow: \$\("log-stats-failed-span-share-of-ok-window"\)/);
  assert.match(
    app,
    /Failure-span share of success window: \$\{stats\.failedSpanShareOfOkWindow === null \? "none" : `\$\{Math\.round\(stats\.failedSpanShareOfOkWindow \* 100\)\}%`}/,
    "updateLogStats sets the failed-span-share-of-ok-window line from stats()",
  );
});
