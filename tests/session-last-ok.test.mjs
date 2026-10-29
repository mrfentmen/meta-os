// Node built-in test runner, no dependencies:
//   node --test tests/session-last-ok.test.mjs
//
// Rowan DETAIL-3 (Del direction 2026-10-29, Rowan leads detail/stats,
// Ignis first): the session-log panel gains a last-successful-assessment
// line, computed only from entries the log actually recorded. DETAIL-1
// bucketed successes by product and DETAIL-2 broke failures down by
// cause; this names the most recent success by its request timestamp,
// so a session that went quiet after its last success reads differently
// from one that never succeeded. Failures never move it, and an empty
// log reads "none" — no sampling, no model, no invented timestamp.

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

function recordFailed(log, status = "network_error") {
  return log.record({
    requestTimestamp: "2026-10-29T12:00:00.000Z",
    product: "ignis",
    latencyMs: null,
    status,
    error: "boom",
  });
}

test("empty log: lastOkAt is null", () => {
  const log = new SessionLog();
  assert.equal(log.stats().lastOkAt, null);
});

test("most recent ok entry wins, by record order", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z");
  recordOk(log, "2026-10-29T12:05:00.000Z", "vigiles");
  assert.equal(log.stats().lastOkAt, "2026-10-29T12:05:00.000Z");
});

test("failures after the last success never move lastOkAt", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z");
  recordFailed(log, "http_error");
  recordFailed(log, "invalid_response");
  assert.equal(log.stats().lastOkAt, "2026-10-29T12:00:00.000Z");
});

test("failures alone leave lastOkAt null", () => {
  const log = new SessionLog();
  recordFailed(log);
  assert.equal(log.stats().lastOkAt, null);
});

test("ok entry with no usable request timestamp leaves the previous value", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z");
  log.record({
    product: "ignis",
    latencyMs: 100,
    status: "ok",
    response: { product: "ignis" },
  });
  assert.equal(log.stats().lastOkAt, "2026-10-29T12:00:00.000Z");
});

test("lastOkAt follows clear: back to null", () => {
  const log = new SessionLog();
  recordOk(log, "2026-10-29T12:00:00.000Z");
  log.clear();
  assert.equal(log.stats().lastOkAt, null);
});

test("web wiring: updateLogStats renders the last-success line from log.stats()", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /logStatsLastOk: \$\("log-stats-last-ok"\)/);
  assert.match(
    app,
    /Last successful assessment: \$\{stats\.lastOkAt \?\? "none"\}/,
    "updateLogStats sets the last-success line from stats()",
  );
});

test("web wiring: session-log panel holds the last-success stats element", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="log-stats-last-ok" class="note mono">Last successful assessment: none<\/p>/,
    "static placeholder matches the empty-log rendering exactly",
  );
});
