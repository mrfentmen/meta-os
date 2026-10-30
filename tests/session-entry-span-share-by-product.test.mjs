// Node built-in test runner, no dependencies:
//   node --test tests/session-entry-span-share-by-product.test.mjs
//
// ROWAN DETAIL-46: the session-log panel gains a per-product
// entry-span-share-of-session-window line, computed only from
// entries the log actually recorded. DETAIL-13's entry-count
// shares say how many entries each product supplied, but not
// how long each product was actually recording: a product can
// supply half the entries in a one-minute burst inside an
// hour-long session. This re-bases DETAIL-17's per-product
// entry spans on the session's global entry span (DETAIL-24),
// so each product's window coverage reads at a glance. The
// denominator is the global first-to-last window, not a sum of
// product windows, so these are raw ratios, never clamped,
// and they do NOT sum to 1: product windows overlap, and a
// share above 1 or below 0 means timestamps ran out of
// insertion order, exactly as DETAIL-17's raw spans do. Any
// status moves the endpoints, and an entry with an unknown or
// missing product moves no product bucket but still stretches
// the global window, so it dilutes every share without moving
// any bucket. Null per product when the session holds no
// usable window at all — an empty log, a single entry, or all
// entries at one timestamp — because a zero global span has
// no shares to divide, never NaN; null per product whose own
// span is unknown (entries recorded but no usable timestamp
// pair — never a fabricated window); 0 per product with no
// entries once a nonzero window exists, because it covered
// none of the window, and 0 per single-entry product, whose
// zero-length window covers none of a nonzero window. No
// sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { vigiles: null, ignis: null, medicus: null };

function recordAt(log, timestamp, product, status = "ok") {
  return log.record({
    requestTimestamp: timestamp,
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

test("empty log: every share is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().entrySpanShareByProduct, NULL_SHARES);
});

test("a single entry reads null: a zero global span has no shares to divide", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().entrySpanShareByProduct, NULL_SHARES);
});

test("all entries at one timestamp read null, not 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  assert.deepEqual(log.stats().entrySpanShareByProduct, NULL_SHARES);
});

test("mixed windows divide by the global window, and a product with no entries reads 0, not null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:30.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  // Global window is 600000 ms (first recorded 12:00 to last
  // recorded 12:10); ignis covers 330000 of it. Medicus
  // recorded nothing, so it covered none of the window — 0,
  // not "none".
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: 1,
    ignis: 0.55,
    medicus: 0,
  });
});

test("a single-entry product inside a nonzero window reads 0", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "medicus");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: 1,
    ignis: 0,
    medicus: 0,
  });
});

test("an unknown-product entry stretches the global window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "mystery");
  // Global window is now 1200000 ms; vigiles still spans
  // 600000 of it, and no product bucket moved.
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: 0.5,
    ignis: 0,
    medicus: 0,
  });
});

test("a missing-product entry stretches the global window but moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:20:00.000Z", null);
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: 0,
    ignis: 0.5,
    medicus: 0,
  });
});

test("out-of-order timestamps stay raw: shares can exceed 1 and go negative, never clamped", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:10:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:20:00.000Z", "ignis");
  // Global window: first recorded 12:10 to last recorded 12:20
  // = 600000 ms. Vigiles spans 12:10 back to 12:00 = -600000
  // (-1 of the window); ignis spans 12:20 alone = 0. The
  // shares do not sum to 1, and that is the honest reading.
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: -1,
    ignis: 0,
    medicus: 0,
  });
});

test("a product with entries but no usable timestamp pair reads null, distinct from a no-entry product's 0", () => {
  const log = new SessionLog();
  recordAt(log, "", "vigiles");
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  // Vigiles recorded entries but no usable timestamps, so its
  // window is unknown — null, never a fabricated 0 — while
  // medicus, with no entries at all, covered none of the
  // window and reads 0.
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: null,
    ignis: 1,
    medicus: 0,
  });
});

test("failures move the endpoints: any status stretches the window", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis", "network_error");
  assert.deepEqual(log.stats().entrySpanShareByProduct, {
    vigiles: 0,
    ignis: 1,
    medicus: 0,
  });
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:10:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().entrySpanShareByProduct, NULL_SHARES);
});

test("web wiring: updateLogStats renders the entry-span-share line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsEntrySpanShareByProduct: \$\("log-stats-entry-span-share-by-product"\)/);
  assert.match(
    app,
    /Entry-span share of session window by product: Vigiles \$\{stats\.entrySpanShareByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.entrySpanShareByProduct\.vigiles \* 100\)\}%`\}/,
    "updateLogStats sets the entry-span-share line from stats()",
  );
});

test("web wiring: session-log panel holds the entry-span-share stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-entry-span-share-by-product" class="note mono">Entry-span share of session window by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
