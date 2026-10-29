// Node built-in test runner, no dependencies:
//   node --test tests/session-stats.test.mjs
//
// Rowan DETAIL-1 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a per-product stats line,
// computed only from entries the log actually recorded. No sampling,
// no model, no invented counts: successful assessments bucketed by
// their own product, failures as one total.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SessionLog } from "../js/log.js";

function recordOk(log, product) {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product,
    latencyMs: 100,
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

test("empty log: all stats zero", () => {
  const log = new SessionLog();
  assert.deepEqual(log.stats(), {
    total: 0,
    ok: 0,
    failed: 0,
    byProduct: { vigiles: 0, ignis: 0, sanitas: 0 },
  });
});

test("ok entries bucket by their own product; failures count once, unbucketed", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordOk(log, "ignis");
  recordOk(log, "vigiles");
  recordOk(log, "sanitas");
  recordFailed(log, "ignis");
  recordFailed(log, "vigiles", "http_error");
  assert.deepEqual(log.stats(), {
    total: 6,
    ok: 4,
    failed: 2,
    byProduct: { vigiles: 1, ignis: 2, sanitas: 1 },
  });
});

test("ok entry with unknown product counts in ok but in no bucket", () => {
  const log = new SessionLog();
  recordOk(log, "mystery");
  assert.deepEqual(log.stats(), {
    total: 1,
    ok: 1,
    failed: 0,
    byProduct: { vigiles: 0, ignis: 0, sanitas: 0 },
  });
});

test("stats follow clear: back to zero", () => {
  const log = new SessionLog();
  recordOk(log, "ignis");
  recordFailed(log, "ignis");
  log.clear();
  assert.deepEqual(log.stats(), {
    total: 0,
    ok: 0,
    failed: 0,
    byProduct: { vigiles: 0, ignis: 0, sanitas: 0 },
  });
});

test("web wiring: updateLogStats renders the per-product line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsByProduct: \$\("log-stats-by-product"\)/);
  assert.match(
    app,
    /const stats = log\.stats\(\);[\s\S]*?Assessments by product: Vigiles \$\{stats\.byProduct\.vigiles\} · Ignis \$\{stats\.byProduct\.ignis\} · Sanitas \$\{stats\.byProduct\.sanitas\} · Failed \$\{stats\.failed\}/,
    "updateLogStats sets the per-product line from stats()",
  );
});

test("web wiring: session-log panel holds the per-product stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-by-product" class="note mono">Assessments by product: Vigiles 0 · Ignis 0 · Sanitas 0 · Failed 0<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
