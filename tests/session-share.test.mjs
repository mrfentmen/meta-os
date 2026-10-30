// Node built-in test runner, no dependencies:
//   node --test tests/session-share.test.mjs
//
// Hana DETAIL-25: the session-log panel gains global successful
// and failed share lines, computed only from entries the log
// actually recorded. Each share is that outcome's entries over
// the session total, so a session with 2 successes and 1 failure
// reads 2/3 successful and 1/3 failed, where the per-product
// DETAIL-11/12 shares alone do not say it at a glance — they
// divide by each product's own entries, and a product with no
// entries reads null there. The global denominator is the
// session total, so the null rule differs on purpose: an empty
// log reads null for both (no total to divide by), but once
// the log holds any entry, a session with no successes reads
// 0 for okShare and 1 for failedShare, never "none". The two
// shares sum to 1 wherever either is non-null, because every
// recorded entry is either ok or one of the three failure
// statuses. Unlike the per-product buckets, the global shares
// count unknown- or missing-product entries: they sit in the
// session total, so they count here just as they open and
// close the global spans. No sampling, no model, no invented
// products.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordAt(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: status === "ok" ? 100 : null,
    status,
    ...(status === "ok" ? { response: { product } } : { error: "boom" }),
  });
}

test("empty log: both global shares are null, not a fabricated share", () => {
  const log = new SessionLog();
  assert.equal(log.stats().okShare, null);
  assert.equal(log.stats().failedShare, null);
});

test("shares divide by the session total: 2 ok and 1 failure read 2/3 and 1/3", () => {
  const log = new SessionLog();
  recordAt(log, "vigiles", "ok");
  recordAt(log, "ignis", "ok");
  recordAt(log, "ignis");
  const stats = log.stats();
  assert.equal(stats.okShare, 2 / 3);
  assert.equal(stats.failedShare, 1 / 3);
  assert.equal(stats.okShare + stats.failedShare, 1);
});

test("a session with only successes reads 1 and 0, never none", () => {
  const log = new SessionLog();
  recordAt(log, "vigiles", "ok");
  recordAt(log, "medicus", "ok");
  const stats = log.stats();
  assert.equal(stats.okShare, 1);
  assert.equal(stats.failedShare, 0);
});

test("a session with only failures reads 0 and 1, never none", () => {
  const log = new SessionLog();
  recordAt(log, "vigiles");
  recordAt(log, "ignis", "http_error");
  const stats = log.stats();
  assert.equal(stats.okShare, 0);
  assert.equal(stats.failedShare, 1);
});

test("entries with an unknown product still count in the global shares", () => {
  const log = new SessionLog();
  recordAt(log, "mystery", "ok");
  recordAt(log, "mystery");
  const stats = log.stats();
  assert.equal(stats.okShare, 0.5);
  assert.equal(stats.failedShare, 0.5);
  assert.deepEqual(stats.okShareByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
  assert.equal(stats.total, 2);
});

test("entries with a missing product still count in the global shares", () => {
  const log = new SessionLog();
  recordAt(log, null, "ok");
  recordAt(log, null);
  recordAt(log, null);
  const stats = log.stats();
  assert.equal(stats.okShare, 1 / 3);
  assert.equal(stats.failedShare, 2 / 3);
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordAt(log, "ignis", "ok");
  recordAt(log, "ignis");
  log.clear();
  assert.equal(log.stats().okShare, null);
  assert.equal(log.stats().failedShare, null);
});

test("web wiring: updateLogStats renders the global share lines from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsOkShare: \$\("log-stats-ok-share"\)/);
  assert.match(app, /logStatsFailedShare: \$\("log-stats-failed-share"\)/);
  assert.match(
    app,
    /Successful share: \$\{stats\.okShare === null \? "none" : `\$\{Math\.round\(stats\.okShare \* 100\)\}%`\}/,
    "updateLogStats sets the global successful-share line from stats()",
  );
  assert.match(
    app,
    /Failed share: \$\{stats\.failedShare === null \? "none" : `\$\{Math\.round\(stats\.failedShare \* 100\)\}%`\}/,
    "updateLogStats sets the global failed-share line from stats()",
  );
});

test("web wiring: session-log panel holds the global share stats elements", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-ok-share" class="note mono">Successful share: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
  assert.match(
    html,
    /<p id="log-stats-failed-share" class="note mono">Failed share: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
