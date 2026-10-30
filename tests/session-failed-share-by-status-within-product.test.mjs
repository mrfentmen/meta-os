// Node built-in test runner, no dependencies:
//   node --test tests/session-failed-share-by-status-within-product.test.mjs
//
// Rowan DETAIL-33: the session-log panel gains a per-product
// failure-cause share of that product's own failures line,
// computed only from entries the log actually recorded.
// DETAIL-29 split the DETAIL-9 counts per product over all
// failures and DETAIL-31 collapsed them globally; this re-bases
// each product's counts on that product's own failed total, so a
// session where all of Vigiles' failures are network errors
// reads that at a glance even when Vigiles is a small slice of
// all failures. The denominator is per product: a product with
// no failures of its own reads null per cause (an empty log, a
// success-only log, and a product with successes but no
// failures alike), but once that product holds any failure, a
// cause with no failures of that cause for that product reads
// 0, never "none". A product's cells sum to 1 once it holds
// any failure: failedCountByProduct counts exactly the bucketed
// failures, so a failure with an unknown or missing product
// moves no bucket and no denominator here, unlike DETAIL-31's
// product-blind cells. Successes never move a cell. No
// sampling, no model, no invented measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

const NULL_CAUSES = { network_error: null, http_error: null, invalid_response: null };
const NULL_WITHIN = { vigiles: NULL_CAUSES, ignis: NULL_CAUSES, medicus: NULL_CAUSES };

function recordFailed(log, product, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

function recordOk(log, product) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

test("empty log: every product-cause is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, NULL_WITHIN);
});

test("a single failure reads 1 in its own cause and 0 elsewhere for that product only", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, {
    vigiles: NULL_CAUSES,
    ignis: { network_error: 0, http_error: 1, invalid_response: 0 },
    medicus: NULL_CAUSES,
  });
});

test("mixed causes within one product divide by that product's failed total, not all failures", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "vigiles", "http_error");
  recordFailed(log, "vigiles", "invalid_response");
  recordFailed(log, "ignis", "network_error");
  recordFailed(log, "ignis", "network_error");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, {
    vigiles: { network_error: 0.5, http_error: 0.25, invalid_response: 0.25 },
    ignis: { network_error: 1, http_error: 0, invalid_response: 0 },
    medicus: NULL_CAUSES,
  });
});

test("all three causes read thirds of that product's failures", () => {
  const log = new SessionLog();
  recordFailed(log, "medicus", "network_error");
  recordFailed(log, "medicus", "http_error");
  recordFailed(log, "medicus", "invalid_response");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, {
    vigiles: NULL_CAUSES,
    ignis: NULL_CAUSES,
    medicus: { network_error: 1 / 3, http_error: 1 / 3, invalid_response: 1 / 3 },
  });
});

test("a product's causes sum to 1 whenever that product has failures", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "ignis", "http_error");
  recordFailed(log, "ignis", "invalid_response");
  const shares = log.stats().failedShareByStatusWithinProduct;
  for (const product of ["vigiles", "ignis"]) {
    const sum = Object.values(shares[product]).reduce((a, b) => a + b, 0);
    assert.equal(sum, 1);
  }
});

test("a failure with an unknown product moves no cell and no denominator", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", "network_error");
  recordFailed(log, "mystery", "http_error");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, {
    vigiles: { network_error: 1, http_error: 0, invalid_response: 0 },
    ignis: NULL_CAUSES,
    medicus: NULL_CAUSES,
  });
});

test("a failure with a missing product moves no cell and no denominator", () => {
  const log = new SessionLog();
  recordFailed(log, "medicus", "invalid_response");
  recordFailed(log, null, "http_error");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, {
    vigiles: NULL_CAUSES,
    ignis: NULL_CAUSES,
    medicus: { network_error: 0, http_error: 0, invalid_response: 1 },
  });
});

test("successes never move a cell, and a success-only log reads null", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles");
  recordOk(log, "ignis");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, NULL_WITHIN);
  recordFailed(log, "ignis", "network_error");
  recordOk(log, "vigiles");
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, {
    vigiles: NULL_CAUSES,
    ignis: { network_error: 1, http_error: 0, invalid_response: 0 },
    medicus: NULL_CAUSES,
  });
});

test("a cause with no failures reads 0 for a failing product but null for a failure-free product", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "http_error");
  const shares = log.stats().failedShareByStatusWithinProduct;
  assert.equal(shares.ignis.network_error, 0);
  assert.equal(shares.ignis.invalid_response, 0);
  assert.deepEqual(shares.vigiles, NULL_CAUSES);
  assert.deepEqual(shares.medicus, NULL_CAUSES);
});

test("shares follow clear: back to null", () => {
  const log = new SessionLog();
  recordFailed(log, "ignis", "network_error");
  log.clear();
  assert.deepEqual(log.stats().failedShareByStatusWithinProduct, NULL_WITHIN);
});

test("web wiring: updateLogStats renders the failed-share-by-status-within-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailedShareByStatusWithinProduct: \$\("log-stats-failed-share-by-status-within-product"\)/);
  assert.match(
    app,
    /Failure-cause share of that product's failures: Vigiles Network \$\{stats\.failedShareByStatusWithinProduct\.vigiles\.network_error === null \? "none" : `\$\{Math\.round\(stats\.failedShareByStatusWithinProduct\.vigiles\.network_error \* 100\)\}%`\}/,
    "updateLogStats sets the failed-share-by-status-within-product line from stats()",
  );
});

test("web wiring: session-log panel holds the failed-share-by-status-within-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failed-share-by-status-within-product" class="note mono">Failure-cause share of that product's failures: Vigiles Network none, HTTP none, Invalid response none · Ignis Network none, HTTP none, Invalid response none · Medicus Network none, HTTP none, Invalid response none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
