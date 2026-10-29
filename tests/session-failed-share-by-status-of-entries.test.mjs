// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-status-of-entries.test.mjs
//
// HANA DETAIL-43: the session-log panel gains a global
// failure-cause-share-of-all-entries line, computed only from
// entries the log actually recorded. DETAIL-9 bucketed failed
// counts per cause, and DETAIL-31 re-based those counts on
// the failed total, but failed-total shares alone cannot say
// what slice of everything recorded network errors are: this
// re-bases each global cause count on the session's entry
// total. It is the collapsed form of DETAIL-42's nine
// product-cause cells: where DETAIL-42 splits by product,
// this adds the causes across products. The denominator is
// the entry total, not the failed total: successes sit in
// the denominator but move no cell, and a session with no
// entries at all reads null per cause (an empty log). Once
// the session holds any entry, a cause with no failures
// reads 0, never "none" — including a success-only log,
// unlike DETAIL-31, whose denominator is the failed total
// and which reads null until the first failure. Unlike
// DETAIL-42's cells, these always sum to the global failed
// share: failedByStatus is product-blind, so a failure with
// an unknown or missing product still moves its cause cell.
// No sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_SHARES = { network_error: null, http_error: null, invalid_response: null };
const ZERO_SHARES = { network_error: 0, http_error: 0, invalid_response: 0 };

function recordOk(log, product, latencyMs = 100) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: every cause is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, NULL_SHARES);
});

test("a single failure reads 1 in its own cause and 0 elsewhere", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, {
    network_error: 0,
    http_error: 1,
    invalid_response: 0,
  });
});

test("mixed counts divide by the entry total, not the failed total", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "ignis", "invalid_response");
  // 6 entries, not 3 failures: successes sit in the denominator only.
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, {
    network_error: 1 / 6,
    http_error: 1 / 6,
    invalid_response: 1 / 6,
  });
});

test("cells always sum to the global failed share", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "sanitas", "http_error");
  const shares = log.stats().failedShareByStatusOfEntries;
  const sum = Object.values(shares).reduce((a, b) => a + b, 0);
  assert.equal(sum, log.stats().failedShare);
});

test("a failure with an unknown product still moves its cause cell", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "mystery", "network_error");
  // Unlike DETAIL-42's product cells, the global cause cell counts it:
  // the cells sum to the global failed share, 0.5, not 0.
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, {
    network_error: 0.5,
    http_error: 0,
    invalid_response: 0,
  });
  assert.equal(log.stats().failedShare, 0.5);
});

test("a failure with a missing product still moves its cause cell", () => {
  const log = new SessionLog();
  recordOk(log, "sanitas");
  recordFailed(log, null, "http_error");
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, {
    network_error: 0,
    http_error: 0.5,
    invalid_response: 0,
  });
  assert.equal(log.stats().failedShare, 0.5);
});

test("successes never move a cell, and a success-only log reads 0, not null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, ZERO_SHARES);
});

test("the three cause cells sum to the global failed share even with unknown-product failures", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "mystery", "network_error");
  recordFailed(log, "ignis", "http_error");
  const stats = log.stats();
  const shares = stats.failedShareByStatusOfEntries;
  const sum = shares.network_error + shares.http_error + shares.invalid_response;
  assert.equal(sum, stats.failedShare);
});

test("the global cells equal the DETAIL-42 cells summed across products when every failure carries a known product", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "sanitas", "invalid_response");
  const stats = log.stats();
  const byProduct = stats.failedShareByStatusOfEntriesByProduct;
  for (const cause of ["network_error", "http_error", "invalid_response"]) {
    const summed = byProduct.vigiles[cause] + byProduct.ignis[cause] + byProduct.sanitas[cause];
    assert.equal(summed, stats.failedShareByStatusOfEntries[cause]);
  }
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  log.clear();
  assert.deepEqual(log.stats().failedShareByStatusOfEntries, NULL_SHARES);
});

test("web wiring: updateLogStats renders the failure-cause-share-of-entries line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByStatusOfEntries: \$\("log-stats-failed-share-by-status-of-entries"\)/);
  assert.match(
    app,
    /Failure-cause share of all entries: Network \$\{stats\.failedShareByStatusOfEntries\.network_error === null \? "none" : `\$\{Math\.round\(stats\.failedShareByStatusOfEntries\.network_error \* 100\)\}%`\}/,
    "updateLogStats sets the failure-cause-share-of-entries line from stats()",
  );
});

test("web wiring: session-log panel holds the failure-cause-share-of-entries stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-status-of-entries" class="note mono">Failure-cause share of all entries: Network none, HTTP none, Invalid response none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
