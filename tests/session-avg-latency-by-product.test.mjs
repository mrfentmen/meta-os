// Node built-in test runner, no dependencies:
//   node --test tests/session-avg-latency-by-product.test.mjs
//
// Rowan DETAIL-8 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product
// average-successful-latency line, computed only from measurements
// the log actually recorded. DETAIL-4 named the mean over all
// successes; this splits it per product, so a session where Ignis
// successes are slow but Vigiles successes are fast reads
// differently from one where all three are slow together. Failures
// never contribute, an ok entry with an unknown product moves no
// bucket, an ok entry with no finite latency is skipped rather
// than counted as zero, and an empty bucket reads "none" — no
// sampling, no model, no invented latency.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, latencyMs, product = "ignis") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, status = "network_error", product = "ignis", latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status,
    error: "boom",
  });
}

test("empty log: every product bucket is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().avgOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("each product's mean is over its own ok latencies only", () => {
  const log = new SessionLog();
  recordOk(log, 100, "vigiles");
  recordOk(log, 300, "vigiles");
  recordOk(log, 50, "ignis");
  assert.deepEqual(log.stats().avgOkLatencyMsByProduct, {
    vigiles: 200,
    ignis: 50,
    medicus: null,
  });
});

test("a product with no success stays null while other buckets move", () => {
  const log = new SessionLog();
  recordOk(log, 100, "medicus");
  assert.equal(log.stats().avgOkLatencyMsByProduct.medicus, 100);
  assert.equal(log.stats().avgOkLatencyMsByProduct.vigiles, null);
  assert.equal(log.stats().avgOkLatencyMsByProduct.ignis, null);
});

test("failures never contribute, even with a recorded latency", () => {
  const log = new SessionLog();
  recordOk(log, 100, "ignis");
  recordFailed(log, "http_error", "ignis", 9999);
  recordFailed(log, "network_error", "vigiles", 9999);
  assert.deepEqual(log.stats().avgOkLatencyMsByProduct, {
    vigiles: null,
    ignis: 100,
    medicus: null,
  });
});

test("failures alone leave every bucket null", () => {
  const log = new SessionLog();
  recordFailed(log, "network_error", "ignis");
  recordFailed(log, "http_error", "vigiles");
  assert.deepEqual(log.stats().avgOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("ok entry with an unknown product moves no bucket", () => {
  const log = new SessionLog();
  recordOk(log, 100, "mystery");
  assert.deepEqual(log.stats().avgOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
  assert.equal(log.stats().avgOkLatencyMs, 100);
});

test("ok entry with no finite latency is skipped, not counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, 100, "ignis");
  recordOk(log, null, "ignis");
  recordOk(log, null, "vigiles");
  assert.equal(log.stats().avgOkLatencyMsByProduct.ignis, 100);
  assert.equal(log.stats().avgOkLatencyMsByProduct.vigiles, null);
});

test("avgOkLatencyMsByProduct follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, 100, "ignis");
  log.clear();
  assert.deepEqual(log.stats().avgOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the per-product average-latency line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsAvgLatencyByProduct: \$\("log-stats-avg-latency-by-product"\)/);
  assert.match(
    app,
    /Average successful latency by product: Vigiles \$\{stats\.avgOkLatencyMsByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.avgOkLatencyMsByProduct\.vigiles\)\} ms`\} · Ignis \$\{stats\.avgOkLatencyMsByProduct\.ignis === null \? "none" : `\$\{Math\.round\(stats\.avgOkLatencyMsByProduct\.ignis\)\} ms`\} · Medicus \$\{stats\.avgOkLatencyMsByProduct\.medicus === null \? "none" : `\$\{Math\.round\(stats\.avgOkLatencyMsByProduct\.medicus\)\} ms`\}/,
    "updateLogStats sets the per-product average-latency line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product average-latency stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-avg-latency-by-product" class="note mono">Average successful latency by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
