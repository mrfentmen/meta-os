// Node built-in test runner, no dependencies:
//   node --test tests/session-last-ok-by-product.test.mjs
//
// Rowan DETAIL-5 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product last-success
// line, computed only from entries the log actually recorded. DETAIL-3
// named the single most recent success; this splits it per product, so
// a session where Ignis went quiet but Vigiles just succeeded reads
// differently from one where all three went quiet together. Failures
// never move a bucket, an ok entry with an unknown product moves no
// bucket, and an empty bucket reads "none" — no sampling, no model, no
// invented timestamp.

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

function recordFailed(log, product = "ignis", status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: every product bucket is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().lastOkAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("each product's most recent ok entry wins, by record order", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOk(log, "2026-10-29T12:05:00.000Z", "vigiles");
  recordOk(log, "2026-10-29T12:10:00.000Z", "ignis");
  assert.deepEqual(log.stats().lastOkAtByProduct, {
    vigiles: "2026-10-29T12:05:00.000Z",
    ignis: "2026-10-29T12:10:00.000Z",
    medicus: null,
  });
});

test("a product with no ok entry stays null while other buckets move", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "vigiles");
  assert.equal(log.stats().lastOkAtByProduct.vigiles, "2026-10-29T12:00:00.000Z");
  assert.equal(log.stats().lastOkAtByProduct.ignis, null);
  assert.equal(log.stats().lastOkAtByProduct.medicus, null);
});

test("failures after the last success never move any bucket", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "ignis");
  recordOk(log, "2026-10-29T12:05:00.000Z", "medicus");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "medicus", "invalid_response");
  assert.deepEqual(log.stats().lastOkAtByProduct, {
    vigiles: null,
    ignis: "2026-10-29T12:00:00.000Z",
    medicus: "2026-10-29T12:05:00.000Z",
  });
});

test("failures alone leave every bucket null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats().lastOkAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("ok entry with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "mystery");
  assert.deepEqual(log.stats().lastOkAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("ok entry with no usable request timestamp leaves its bucket's previous value", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "ignis");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: { product: "ignis" },
  });
  assert.equal(log.stats().lastOkAtByProduct.ignis, "2026-10-29T12:00:00.000Z");
});

test("lastOkAtByProduct follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z", "ignis");
  log.clear();
  assert.deepEqual(log.stats().lastOkAtByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the per-product last-success line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsLastOkByProduct: \$\("log-stats-last-ok-by-product"\)/);
  assert.match(
    app,
    /Last success by product: Vigiles \$\{stats\.lastOkAtByProduct\.vigiles \?\? "none"\} · Ignis \$\{stats\.lastOkAtByProduct\.ignis \?\? "none"\} · Medicus \$\{stats\.lastOkAtByProduct\.medicus \?\? "none"\}/,
    "updateLogStats sets the per-product last-success line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product last-success stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-last-ok-by-product" class="note mono">Last success by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
