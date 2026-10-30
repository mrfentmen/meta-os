// Node built-in test runner, no dependencies:
//   node --test tests/session-ok-span-share-of-failed-window.test.mjs
//
// Rowan DETAIL-64: the session-log panel gains a
// global ok-span-share-of-failure-window line,
// computed only from entries the log actually
// recorded. DETAIL-57's and DETAIL-58's shares say
// how much of the whole recording window failures
// and successes each cover, but not how the two
// windows compare to each other: a session where
// successes stretched twice as long as failures
// reads the same entry-window shares as one where
// the failure window is the longer of the two. This
// re-bases DETAIL-22's global ok span on DETAIL-23's
// global failed span, so the success window reads
// against the failure window directly — the
// cross-span re-base the entry-window shares imply
// but do not state. Both spans are product-blind:
// an unknown- or missing-product success still
// opens and closes the global ok span, and an
// unknown- or missing-product failure still opens
// and closes the global failed span, unlike
// DETAIL-53's and DETAIL-55's by-product buckets.
// This is a raw ratio, never clamped, and a share
// above 1 or below 0 means timestamps ran out of
// insertion order, exactly as DETAIL-22's and
// DETAIL-23's raw spans do. Null with no usable
// failed window at all — an empty log, a single
// failure, or all failures at one timestamp —
// because a zero failed span has no share to
// divide, never NaN; null when successes were
// recorded but the global ok span is unknown
// (no usable timestamp pair — never a fabricated
// window); 0 with no successes once a nonzero
// failed window exists, because successes covered
// none of the failure window, and 0 for a
// single-success session, whose zero-length ok
// window covers none of a nonzero failed window.
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
  assert.equal(log.stats().okSpanShareOfFailedWindow, null);
});

test("a single failure reads null: a zero failed span has no share to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindow, null);
});

test("all failures at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindow, null);
});

test("a success-only log reads null: no failed window exists at all", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindow, null);
});

test("no successes once a nonzero failed window exists reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.equal(log.stats().okSpanShareOfFailedWindow, 0);
});

test("a single success inside a nonzero failed window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "vigiles");
  assert.equal(log.stats().okSpanShareOfFailedWindow, 0);
});

test("the share is the ok span over the failed span, above 1 included", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "medicus");
  recordOkAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  // Ok span 11:00 to 13:00 = 7200000 ms; failed span
  // 12:00 to 12:30 = 1800000 ms, so the share is 4 —
  // successes stretched four times as long as
  // failures, and the entry-window shares alone do
  // not say that.
  assert.equal(log.stats().okSpanShareOfFailedWindow, 7200000 / 1800000);
});

test("the share below 1: a short ok span against a long failed window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T13:00:00.000Z", "medicus");
  // Ok span 600000 ms over failed span 7200000 ms.
  assert.equal(log.stats().okSpanShareOfFailedWindow, 600000 / 7200000);
});

test("an unknown-product success moves the numerator, unlike DETAIL-53", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  // The mystery successes open and close the global
  // ok span (600000 ms) and the Vigiles failures
  // open and close the global failed span
  // (1800000 ms), so the product-blind share reads
  // 1/3 even though no by-product bucket moved.
  assert.equal(log.stats().okSpanShareOfFailedWindow, 600000 / 1800000);
  // DETAIL-53 reads 0 per product with no successes
  // once a nonzero global entry window exists, so
  // Ignis and Medicus read 0 here, not null.
  assert.deepEqual(log.stats().okSpanShareOfEntryWindowByProduct, {
    vigiles: 0,
    ignis: 0,
    medicus: 0,
  });
});

test("an unknown-product failure moves the denominator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  // Ok span 600000 ms over the mystery-driven failed
  // span 1800000 ms, so the share reads 1/3 even
  // though no by-product failed bucket moved.
  assert.equal(log.stats().okSpanShareOfFailedWindow, 600000 / 1800000);
});

test("a missing-product success and failure both move the product-blind spans", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:10:00.000Z", null);
  recordAt(log, "2026-10-29T12:30:00.000Z", null);
  assert.equal(log.stats().okSpanShareOfFailedWindow, 600000 / 1800000);
});

test("successes with no usable timestamp pair read null, distinct from a no-success log's 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "", "vigiles");
  // A Vigiles success was recorded but its ok window
  // is unknown — null, never a fabricated 0.
  assert.equal(log.stats().okSpanShareOfFailedWindow, null);
});

test("out-of-order timestamps stay raw: the share can go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  // Failed span 12:00 to 12:30 = 1800000 ms; ok span
  // 12:10 back to 12:00 = -600000 ms, so the share
  // reads -1/3.
  assert.equal(log.stats().okSpanShareOfFailedWindow, -600000 / 1800000);
});

test("out-of-order timestamps stay raw: the share can exceed 1, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  // Failed span 600000 ms, but the ok span runs
  // 12:00 to 12:30 = 1800000 ms, so the share reads
  // 3 — the honest reading of a failure window whose
  // last recorded failure carries an earlier
  // timestamp than the last success.
  assert.equal(log.stats().okSpanShareOfFailedWindow, 3);
});

test("the share equals the DETAIL-22 span over the DETAIL-23 span", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "medicus");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.okSpanShareOfFailedWindow, stats.okSpanMs / stats.failedSpanMs);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().okSpanShareOfFailedWindow, null);
});

test("web wiring: updateLogStats renders the ok-span-share-of-failed-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkSpanShareOfFailedWindow: \$\("log-stats-ok-span-share-of-failed-window"\)/);
  assert.match(
    app,
    /Success-span share of failure window: \$\{stats\.okSpanShareOfFailedWindow === null \? "none" : `\$\{Math\.round\(stats\.okSpanShareOfFailedWindow \* 100\)\}%`}/,
    "updateLogStats sets the ok-span-share-of-failed-window line from stats()",
  );
});

test("web wiring: session-log panel holds the ok-span-share-of-failed-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-span-share-of-failed-window" class="note mono">Success-span share of failure window: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
