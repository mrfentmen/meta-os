// Node built-in test runner, no dependencies:
//   node --test tests/session-first-entry-by-product.test.mjs
//
// Rowan DETAIL-15 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// first-entry line, computed only from entries the log actually
// recorded. Each product's bucket holds the request timestamp of
// its FIRST recorded entry, any status — the opening counterpart
// to DETAIL-5's last success and DETAIL-7's last failure. Set once
// by insertion order, never overwritten: a later entry never moves
// the bucket, even one carrying an earlier timestamp string, so
// the line reads when recording for a product started, not the
// minimum timestamp seen. An entry with an unknown or missing
// product moves no bucket, and an entry without a usable
// timestamp leaves its bucket open for a later usable entry.
// Null per product with no usable entry, never a fabricated
// timestamp. No sampling, no model, no invented products.

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

const NULLS = { vigiles: null, ignis: null, medicus: null };

test("empty log: every product first entry is null, not a fabricated timestamp", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().firstEntryAtByProduct, { ...NULLS });
});

test("first recorded entry per product wins; later entries never move the bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordAt(log, "2026-10-29T12:01:00.000Z", "ignis");
  recordAt(log, "2026-10-29T12:06:00.000Z", "ignis");
  assert.deepEqual(log.stats().firstEntryAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: "2026-10-29T12:01:00.000Z",
    medicus: null,
  });
});

test("a failed first entry counts: any status opens the bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis", "network_error");
  recordAt(log, "2026-10-29T12:05:00.000Z", "ignis");
  assert.equal(log.stats().firstEntryAtByProduct.ignis, "2026-10-29T12:00:00.000Z");
});

test("a product with no entries in a non-empty session reads null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.deepEqual(log.stats().firstEntryAtByProduct, {
    vigiles: "2026-10-29T12:00:00.000Z",
    ignis: null,
    medicus: null,
  });
});

test("insertion order, not minimum timestamp: a later entry with an earlier timestamp string does not move the bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:05:00.000Z", "medicus");
  recordAt(log, "2026-10-29T12:00:00.000Z", "medicus");
  assert.equal(log.stats().firstEntryAtByProduct.medicus, "2026-10-29T12:05:00.000Z");
});

test("an entry with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "mystery");
  assert.deepEqual(log.stats().firstEntryAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 1);
});

test("entries with a missing product move no bucket", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", null);
  recordAt(log, "2026-10-29T12:01:00.000Z", null, "network_error");
  assert.deepEqual(log.stats().firstEntryAtByProduct, { ...NULLS });
  assert.equal(log.stats().total, 2);
});

test("an entry without a usable timestamp leaves the bucket open for a later usable entry", () => {
  const log = new SessionLog();
  recordAt(log, "", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: {},
  });
  recordAt(log, "2026-10-29T12:03:00.000Z", "ignis");
  assert.equal(log.stats().firstEntryAtByProduct.ignis, "2026-10-29T12:03:00.000Z");
});

test("first entries follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "2026-10-29T12:00:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().firstEntryAtByProduct, { ...NULLS });
});

test("web wiring: updateLogStats renders the per-product first-entry line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFirstEntryByProduct: \$\("log-stats-first-entry-by-product"\)/);
  assert.match(
    app,
    /First entry by product: Vigiles \$\{stats\.firstEntryAtByProduct\.vigiles \?\? "none"\} · Ignis \$\{stats\.firstEntryAtByProduct\.ignis \?\? "none"\} · Medicus \$\{stats\.firstEntryAtByProduct\.medicus \?\? "none"\}/,
    "updateLogStats sets the per-product first-entry line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product first-entry stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-first-entry-by-product" class="note mono">First entry by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
