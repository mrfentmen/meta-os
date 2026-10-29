// Node built-in test runner, no dependencies:
//   node --test tests/session-failures-by-product.test.mjs
//
// Rowan DETAIL-9 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// failures-by-cause line, computed only from failures the log
// actually recorded. DETAIL-2 named the cause breakdown over all
// failures; this splits it per product, so a session where Ignis
// failures are all network errors but Vigiles failures are all
// HTTP errors reads differently from one where both fail the same
// way. Successes never move a bucket, a failure with an unknown
// product moves no bucket (but still counts in the session failed
// total and the global cause breakdown), and an empty bucket reads
// zero — no sampling, no model, no invented failures.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, product = "ignis") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: 100,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, status = "network_error", product = "ignis") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: null,
    status,
    error: "boom",
  });
}

const ZERO = { network_error: 0, http_error: 0, invalid_response: 0 };

test("empty log: every product bucket is all zeros", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().failedByStatusByProduct, {
    vigiles: { ...ZERO },
    ignis: { ...ZERO },
    sanitas: { ...ZERO },
  });
});

test("failures bucket by their own product and cause", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", "ignis");
  recordFailed(log, "network_error", "ignis");
  recordFailed(log, "http_error", "vigiles");
  recordFailed(log, "invalid_response", "sanitas");
  assert.deepEqual(log.stats().failedByStatusByProduct, {
    vigiles: { network_error: 0, http_error: 1, invalid_response: 0 },
    ignis: { network_error: 2, http_error: 0, invalid_response: 0 },
    sanitas: { network_error: 0, http_error: 0, invalid_response: 1 },
  });
});

test("successes never move a bucket", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  recordFailed(log, "http_error", "ignis");
  assert.deepEqual(log.stats().failedByStatusByProduct, {
    vigiles: { ...ZERO },
    ignis: { network_error: 0, http_error: 1, invalid_response: 0 },
    sanitas: { ...ZERO },
  });
});

test("failures alone still bucket, successes alone leave zeros", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", "sanitas");
  assert.equal(log.stats().failedByStatusByProduct.sanitas.network_error, 1);
  assert.equal(log.stats().failedByStatusByProduct.vigiles.network_error, 0);
  assert.equal(log.stats().failedByStatusByProduct.ignis.network_error, 0);
});

test("a failure with an unknown product moves no bucket but still counts globally", () => {
  const log = new SessionLog();
  recordFailed(log, "http_error", "mystery");
  assert.deepEqual(log.stats().failedByStatusByProduct, {
    vigiles: { ...ZERO },
    ignis: { ...ZERO },
    sanitas: { ...ZERO },
  });
  assert.equal(log.stats().failed, 1);
  assert.equal(log.stats().failedByStatus.http_error, 1);
});

test("a failure with a missing product moves no bucket but still counts globally", () => {
  const log = new SessionLog();
  log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: null,
    latencyMs: null,
    status: "network_error",
    error: "boom",
  });
  assert.deepEqual(log.stats().failedByStatusByProduct, {
    vigiles: { ...ZERO },
    ignis: { ...ZERO },
    sanitas: { ...ZERO },
  });
  assert.equal(log.stats().failed, 1);
  assert.equal(log.stats().failedByStatus.network_error, 1);
});

test("all three causes accumulate independently within one product", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", "ignis");
  recordFailed(log, "http_error", "ignis");
  recordFailed(log, "invalid_response", "ignis");
  recordFailed(log, "invalid_response", "ignis");
  assert.deepEqual(log.stats().failedByStatusByProduct.ignis, {
    network_error: 1,
    http_error: 1,
    invalid_response: 2,
  });
});

test("failedByStatusByProduct follows clear: back to zeros", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", "ignis");
  log.clear();
  assert.deepEqual(log.stats().failedByStatusByProduct, {
    vigiles: { ...ZERO },
    ignis: { ...ZERO },
    sanitas: { ...ZERO },
  });
});

test("web wiring: updateLogStats renders the per-product failures-by-cause line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsFailuresByProduct: \$\("log-stats-failures-by-product"\)/);
  assert.match(
    app,
    /Failures by cause by product: Vigiles Network \$\{stats\.failedByStatusByProduct\.vigiles\.network_error\}, HTTP \$\{stats\.failedByStatusByProduct\.vigiles\.http_error\}, Invalid response \$\{stats\.failedByStatusByProduct\.vigiles\.invalid_response\} · Ignis Network \$\{stats\.failedByStatusByProduct\.ignis\.network_error\}, HTTP \$\{stats\.failedByStatusByProduct\.ignis\.http_error\}, Invalid response \$\{stats\.failedByStatusByProduct\.ignis\.invalid_response\} · Sanitas Network \$\{stats\.failedByStatusByProduct\.sanitas\.network_error\}, HTTP \$\{stats\.failedByStatusByProduct\.sanitas\.http_error\}, Invalid response \$\{stats\.failedByStatusByProduct\.sanitas\.invalid_response\}/,
    "updateLogStats sets the per-product failures-by-cause line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product failures-by-cause stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-failures-by-product" class="note mono">Failures by cause by product: Vigiles Network 0, HTTP 0, Invalid response 0 · Ignis Network 0, HTTP 0, Invalid response 0 · Sanitas Network 0, HTTP 0, Invalid response 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
