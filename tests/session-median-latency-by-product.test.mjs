// Node built-in test runner, no dependencies:
//   node --test tests/session-median-latency-by-product.test.mjs
//
// Rowan DETAIL-28: the session-log panel gains a per-product median
// successful latency line, computed only from entries the log
// actually recorded. DETAIL-26 named the median over all successes;
// this splits it per product, so a session where Ignis successes
// are typically slow but Vigiles successes are typically fast reads
// differently from one where all three sit together. Same
// measurement rules as the global median and the per-product
// mean/range: failures never contribute, an ok entry with no
// finite latency_ms is skipped rather than counted as zero, and an
// ok entry with an unknown or missing product moves no bucket —
// the global median still counts it, the buckets do not. An odd
// count reads its middle value; an even count reads the mean of
// its two middle values. No sampling, no model, no invented
// measurements.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, product, latencyMs) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "ok",
    response: { product },
  });
}

function recordFailed(log, product, latencyMs = null) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs,
    status: "network_error",
    error: "boom",
  });
}

test("empty log: every product bucket is null", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("a single success per product reads its own latency as the median", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 300);
  recordOk(log, "ignis", 100);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: 300,
    ignis: 100,
    medicus: null,
  });
});

test("an odd count reads the middle value, regardless of insertion order", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 300);
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 200);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: 200,
    medicus: null,
  });
});

test("an even count reads the mean of the two middle values", () => {
  const log = new SessionLog();
  recordOk(log, "vigiles", 400);
  recordOk(log, "vigiles", 100);
  recordOk(log, "vigiles", 300);
  recordOk(log, "vigiles", 200);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: 250,
    ignis: null,
    medicus: null,
  });
});

test("a two-success bucket reads the midpoint, not one end", () => {
  const log = new SessionLog();
  recordOk(log, "medicus", 101);
  recordOk(log, "medicus", 102);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: 101.5,
  });
});

test("failures never contribute, even when they carry a latency", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", 5);
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 200);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: 150,
    medicus: null,
  });
});

test("ok entries with no finite latency are skipped, not counted as zero", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", null);
  recordOk(log, "ignis", NaN);
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 300);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: 200,
    medicus: null,
  });
});

test("a session with only failures and latency-less successes reads null", () => {
  const log = new SessionLog();
  recordFailed(log, "vigiles", 50);
  recordOk(log, "ignis", null);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("entries with an unknown or missing product move no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "mystery", 100);
  recordOk(log, null, 300);
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
  assert.equal(log.stats().medianOkLatencyMs, 200);
});

test("median follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "ignis", 100);
  recordOk(log, "ignis", 200);
  log.clear();
  assert.deepEqual(log.stats().medianOkLatencyMsByProduct, {
    vigiles: null,
    ignis: null,
    medicus: null,
  });
});

test("web wiring: updateLogStats renders the median-latency-by-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsMedianLatencyByProduct: \$\("log-stats-median-latency-by-product"\)/);
  assert.match(
    app,
    /Median successful latency by product: Vigiles \$\{stats\.medianOkLatencyMsByProduct\.vigiles === null \? "none" : `\$\{Math\.round\(stats\.medianOkLatencyMsByProduct\.vigiles\)\} ms`\}/,
    "updateLogStats sets the median-latency-by-product line from stats()",
  );
});

test("web wiring: session-log panel holds the median-latency-by-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-median-latency-by-product" class="note mono">Median successful latency by product: Vigiles none · Ignis none · Medicus none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
