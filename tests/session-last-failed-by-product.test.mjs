// Node built-in test runner, no dependencies:
//   node --test tests/session-last-failed-by-product.test.mjs
//
// Rowan DETAIL-7 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product last-failure
// line, computed only from entries the log actually recorded. DETAIL-5
// named the last success per product; this mirrors it on the failure
// side, so a session where Ignis just failed but Vigiles has not
// failed all day reads differently from one where all three failed
// together. Successes never move a bucket, a failure with an unknown
// product moves no bucket, and an empty bucket reads "none" — no
// sampling, no model, no invented timestamp.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, requestTimestamp, product = "ignis") {
  return log.record({
    requestTimestamp,
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, requestTimestamp, product = "ignis", status = "network_error") {
  return log.record({
    requestTimestamp,
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: every product bucket is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().lastFailedAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("each product's most recent failure wins, by record order", () => {
  const log = new SessionLog();
  recordFailed(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordFailed(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordFailed(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.deepEqual(log.stats().lastFailedAtByProduct, {
    vigiles: "2026-10-29T12:05:00.000Z",
    ignis: "2026-10-29T12:10:00.000Z",
    medicus: null,
  });
});

test("a product with no failure stays null while other buckets move", () => {
  const log = new SessionLog();
  recordFailed(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().lastFailedAtByProduct.vigiles, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastFailedAtByProduct.ignis, null);
  assert.equal(log.stats().lastFailedAtByProduct.medicus, null);
});

test("successes after the last failure never move any bucket", () => {
  const log = new SessionLog();
  recordFailed(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordFailed(log, "2026-10-29T12:05:00.000Z", "medicus");
  recordOk(log, "2026-10-29T12:10:00.000Z", "ignis");
  recordOk(log, "2026-10-29T12:15:00.000Z", "medicus");
  assert.deepEqual(log.stats().lastFailedAtByProduct, {
    vigiles: null,
    ignis: "2026-10-29T12:00:00.000Z",
    medicus: "2026-10-29T12:05:00.000Z",
  });
});

test("successes alone leave every bucket null", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOk(log, "2026-10-29T12:05:00.000Z", "vigiles");
  assert.deepEqual(log.stats().lastFailedAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("failure with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordFailed(log, "2026-10-29T12:00:00.000Z", "mystery");
  assert.deepEqual(log.stats().lastFailedAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("failure with no usable request timestamp leaves its bucket's previous value", () => {
  const log = new SessionLog();
  recordFailed(log, "2026-10-29T12:00:00.000Z", "ignis");
  log.record({
    product: "ignis",
    latencyMs: null,
    status: "http_error",
    error: "boom",
  });
  assert.equal(log.stats().lastFailedAtByProduct.ignis, "2026-10-29T12:00:00.000Z");
});

test("lastFailedAtByProduct follows clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "2026-10-29T12:00:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().lastFailedAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the per-product last-failure line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsLastFailedByProduct: \$\("log-stats-last-failed-by-product"\)/);
  assert.match(
    app,
    /Last failure by product: Vigiles \$\{stats\.lastFailedAtByProduct\.vigiles \?\? "none"\} · Ignis \$\{stats\.lastFailedAtByProduct\.ignis \?\? "none"\} · Medicus \$\{stats\.lastFailedAtByProduct\.medicus \?\? "none"\}/,
    "updateLogStats sets the per-product last-failure line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product last-failure stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-last-failed-by-product" class="note mono">Last failure by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
