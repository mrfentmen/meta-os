// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-share-of-ok-window.test.mjs
//
// Rowan DETAIL-66: the session-log panel gains a
// global entry-span-share-of-success-window line,
// computed only from entries the log actually
// recorded. DETAIL-57's ok-span share of the entry
// window states how much of the recording the
// successes cover; this states the same relation
// from the other side — the whole recording read
// against the success window, so a session whose
// recording ran four times as long as its
// successes reads that at a glance. Both spans are
// product-blind: an entry of any status with an
// unknown or missing product still opens and
// closes the global entry span, and an unknown-
// or missing-product success still opens and
// closes the global ok span, unlike DETAIL-53's
// and DETAIL-55's by-product buckets. This is a
// raw ratio, never clamped: above 1 is the normal
// case (the recording outlasts its successes),
// exactly 1 means every entry was a success
// spanning the whole recording, and below 1 or
// below 0 means timestamps ran out of insertion
// order, exactly as DETAIL-22's and DETAIL-24's
// raw spans do. Null with no usable ok window at
// all — an empty log, a single success, or all
// successes at one timestamp — because a zero ok
// span has no share to divide, never NaN; null
// when successes were recorded but the global ok
// span is unknown (no usable timestamp pair —
// never a fabricated window). No 0 case exists:
// once a nonzero ok window exists, the entries
// carrying it already stretch the entry span to
// at least that window, so a 0 would mean a
// fabricated entry span, and this field never
// fabricates one.
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
  assert.equal(log.stats().entrySpanShareOfOkWindow, null);
});

test("a single success reads null: a zero ok span has no share to divide", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOkWindow, null);
});

test("all successes at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOkWindow, null);
});

test("a failure-only log reads null: no ok window exists at all", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.equal(log.stats().entrySpanShareOfOkWindow, null);
});

test("the share is the entry span over the ok span, above 1 included", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T13:00:00.000Z", "vigiles");
  // Entry span 11:00 to 13:00 = 7200000 ms; ok span
  // 12:00 to 12:30 = 1800000 ms, so the share is 4 —
  // the recording ran four times as long as its
  // successes, and DETAIL-57's share alone states
  // that only as 1/4 from the other side.
  assert.equal(log.stats().entrySpanShareOfOkWindow, 7200000 / 1800000);
});

test("exactly 1 when every entry is a success spanning the whole recording", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  // Entry span and ok span are both 1800000 ms.
  assert.equal(log.stats().entrySpanShareOfOkWindow, 1);
});

test("an unknown-product failure moves the numerator, unlike DETAIL-55", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  // The mystery failures stretch the global entry
  // span to 1800000 ms while the Vigiles successes
  // hold the ok span at 600000 ms, so the
  // product-blind share reads 3 even though no
  // by-product bucket moved.
  assert.equal(log.stats().entrySpanShareOfOkWindow, 1800000 / 600000);
});

test("an unknown-product success moves the denominator, unlike DETAIL-53", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "mystery");
  // Entry span 1800000 ms over the mystery-driven ok
  // span 1800000 ms, so the share reads 1 even
  // though no by-product ok bucket moved.
  assert.equal(log.stats().entrySpanShareOfOkWindow, 1);
});

test("a missing-product success and failure both move the product-blind spans", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:00:00.000Z", null);
  recordOkAt(log, "2026-10-29T12:10:00.000Z", null);
  recordAt(log, "2026-10-29T12:30:00.000Z", null);
  // Endpoints follow insertion order, not timestamp
  // order: the last recorded entry (the 12:30 failure)
  // closes the entry span at 1800000 ms, while the
  // successes close the ok span at 600000 ms.
  assert.equal(log.stats().entrySpanShareOfOkWindow, 1800000 / 600000);
});

test("successes with no usable timestamp pair read null, even with a spanning entry log", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordOkAt(log, "", "vigiles");
  // A Vigiles success was recorded but its ok window
  // is unknown — null, never a fabricated ratio
  // against the failures' entry span.
  assert.equal(log.stats().entrySpanShareOfOkWindow, null);
});

test("out-of-order timestamps stay raw: the share can go below 1, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Entry span 12:00 to 12:10 = 600000 ms; ok span
  // 12:00 to 12:30 = 1800000 ms, so the share reads
  // 1/3 — the recording's last entry carries an
  // earlier timestamp than the last success.
  assert.equal(log.stats().entrySpanShareOfOkWindow, 600000 / 1800000);
});

test("out-of-order timestamps stay raw: the share can go negative, never clamped", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  // Entry span 12:00 back to 11:00 = -3600000 ms
  // over ok span 1800000 ms, so the share reads -2.
  assert.equal(log.stats().entrySpanShareOfOkWindow, -3600000 / 1800000);
});

test("the share equals the DETAIL-24 span over the DETAIL-22 span", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T11:00:00.000Z", "vigiles");
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "sanitas");
  recordAt(log, "2026-10-29T12:30:00.000Z", "vigiles");
  const stats = log.stats();
  assert.equal(stats.entrySpanShareOfOkWindow, stats.entrySpanMs / stats.okSpanMs);
});

test("the share follows clear: back to null", () => {
  const log = new SessionLog();
  recordOkAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOkAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:30:00.000Z", "ignis");
  log.clear();
  assert.equal(log.stats().entrySpanShareOfOkWindow, null);
});

test("web wiring: updateLogStats renders the entry-span-share-of-ok-window line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanShareOfOkWindow: \$\("log-stats-entry-span-share-of-ok-window"\)/);
  assert.match(
    app,
    /Entry-span share of success window: \$\{stats\.entrySpanShareOfOkWindow === null \? "none" : `\$\{Math\.round\(stats\.entrySpanShareOfOkWindow \* 100\)\}%`}/,
    "updateLogStats sets the entry-span-share-of-ok-window line from stats()",
  );
});

test("web wiring: session-log panel holds the entry-span-share-of-ok-window stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-share-of-ok-window" class="note mono">Entry-span share of success window: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
