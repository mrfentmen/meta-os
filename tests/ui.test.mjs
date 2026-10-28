// Node built-in test runner, no dependencies:  node --test tests/
// Covers the pure logic the browser loads: schema validation, sampler
// skip-while-in-flight, analysis client error handling, session log shape.

import { test } from "node:test";
import assert from "node:assert/strict";

import { validateAssessment } from "../js/schema.js";
import { FrameSampler } from "../js/sampler.js";
import { assessFrame, AssessError } from "../js/client.js";
import { SessionLog } from "../js/log.js";

function validAssessment() {
  return {
    timestamp: "2026-10-28T10:15:00.000Z",
    observations: [
      { action: "person raising both arms", evidence: "both arms above shoulder height in frame", confidence: 0.72 },
    ],
    event_type: "unknown",
    assessment: "One person with raised arms; no contact with another person is visible.",
    uncertainty: "Cannot determine intent or what happened before this frame.",
    requires_human_review: false,
  };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

// ---------- schema validation ----------

test("schema: accepts a valid assessment", () => {
  const result = validateAssessment(validAssessment());
  assert.equal(result.ok, true);
  assert.deepEqual(result.errors, []);
});

test("schema: accepts an assessment with zero observations", () => {
  const value = validAssessment();
  value.observations = [];
  assert.equal(validateAssessment(value).ok, true);
});

const malformedCases = [
  ["null", null],
  ["an array", []],
  ["a string", "not an object"],
  ["missing timestamp", (() => { const v = validAssessment(); delete v.timestamp; return v; })()],
  ["unparseable timestamp", { ...validAssessment(), timestamp: "not-a-date" }],
  ["observations not an array", { ...validAssessment(), observations: "none" }],
  ["observation missing action", { ...validAssessment(), observations: [{ evidence: "e", confidence: 0.5 }] }],
  ["observation empty action", { ...validAssessment(), observations: [{ action: "  ", evidence: "e", confidence: 0.5 }] }],
  ["observation missing evidence", { ...validAssessment(), observations: [{ action: "a", confidence: 0.5 }] }],
  ["confidence above 1", { ...validAssessment(), observations: [{ action: "a", evidence: "e", confidence: 1.5 }] }],
  ["confidence below 0", { ...validAssessment(), observations: [{ action: "a", evidence: "e", confidence: -0.1 }] }],
  ["confidence not a number", { ...validAssessment(), observations: [{ action: "a", evidence: "e", confidence: "high" }] }],
  ["empty event_type", { ...validAssessment(), event_type: "" }],
  ["missing assessment", (() => { const v = validAssessment(); delete v.assessment; return v; })()],
  ["missing uncertainty", (() => { const v = validAssessment(); delete v.uncertainty; return v; })()],
  ["requires_human_review not boolean", { ...validAssessment(), requires_human_review: "yes" }],
];

for (const [name, value] of malformedCases) {
  test(`schema: rejects ${name}`, () => {
    const result = validateAssessment(value);
    assert.equal(result.ok, false);
    assert.ok(result.errors.length > 0);
  });
}

// ---------- sampler ----------

test("sampler: skips ticks while a request is in flight", async () => {
  const resolvers = [];
  const sampler = new FrameSampler({
    onSample: () => new Promise((resolve) => resolvers.push(resolve)),
  });

  const first = sampler.tick();
  assert.equal(sampler.inFlight, true);

  const second = await sampler.tick();
  assert.equal(second, "skipped");
  assert.equal(sampler.skippedCount, 1);
  assert.equal(resolvers.length, 1); // onSample was NOT called again

  resolvers[0]();
  assert.equal(await first, "sampled");
  assert.equal(sampler.inFlight, false);
  assert.equal(sampler.sampledCount, 1);

  const third = sampler.tick();
  assert.equal(resolvers.length, 2); // sampling resumes after settle
  resolvers[1]();
  assert.equal(await third, "sampled");
  assert.equal(sampler.sampledCount, 2);
  assert.equal(sampler.tickCount, 3);
});

test("sampler: interval callback drives ticks and stop() halts it", async () => {
  let callback = null;
  let clearedId = null;
  let calls = 0;
  const sampler = new FrameSampler({
    intervalMs: 1000,
    onSample: async () => { calls += 1; },
    setIntervalFn: (fn) => { callback = fn; return 42; },
    clearIntervalFn: (id) => { clearedId = id; callback = null; },
  });

  sampler.start();
  assert.equal(sampler.running, true);
  callback();
  await flush();
  assert.equal(calls, 1);
  callback();
  await flush();
  assert.equal(calls, 2);

  sampler.stop();
  assert.equal(sampler.running, false);
  assert.equal(clearedId, 42);
});

test("sampler: a rejecting onSample returns 'error' and never wedges inFlight", async () => {
  const seen = [];
  let shouldFail = true;
  const sampler = new FrameSampler({
    onSample: async () => { if (shouldFail) throw new Error("backend down"); },
    onError: (err) => seen.push(err.message),
  });

  assert.equal(await sampler.tick(), "error");
  assert.equal(sampler.inFlight, false);
  assert.equal(sampler.errorCount, 1);
  assert.deepEqual(seen, ["backend down"]);

  shouldFail = false;
  assert.equal(await sampler.tick(), "sampled");
});

test("sampler: onTick observes every outcome", async () => {
  const statuses = [];
  const resolvers = [];
  const sampler = new FrameSampler({
    onSample: () => new Promise((resolve) => resolvers.push(resolve)),
    onTick: (s) => statuses.push(s),
  });
  const first = sampler.tick();
  await sampler.tick();
  resolvers[0]();
  await first;
  assert.deepEqual(statuses, ["skipped", "sampled"]);
});

// ---------- analysis client ----------

test("client: returns the validated assessment on HTTP 200", async () => {
  let seenUrl = null;
  let seenInit = null;
  const fakeFetch = async (url, init) => {
    seenUrl = url;
    seenInit = init;
    return { ok: true, status: 200, statusText: "OK", json: async () => validAssessment() };
  };
  const payload = { timestamp: "2026-10-28T10:15:00.000Z", image: "data:image/jpeg;base64,AAAA" };
  const result = await assessFrame("/api/assess", payload, fakeFetch);
  assert.deepEqual(result, validAssessment());
  assert.equal(seenUrl, "/api/assess");
  assert.equal(seenInit.method, "POST");
  assert.deepEqual(JSON.parse(seenInit.body), payload);
});

test("client: HTTP error status throws AssessError kind=http with the status", async () => {
  const fakeFetch = async () => ({ ok: false, status: 503, statusText: "Service Unavailable", json: async () => ({}) });
  await assert.rejects(
    assessFrame("/api/assess", { timestamp: "t", image: "i" }, fakeFetch),
    (err) => {
      assert.ok(err instanceof AssessError);
      assert.equal(err.kind, "http");
      assert.match(err.message, /503/);
      return true;
    },
  );
});

test("client: network failure throws AssessError kind=network", async () => {
  const fakeFetch = async () => { throw new TypeError("fetch failed"); };
  await assert.rejects(
    assessFrame("/api/assess", { timestamp: "t", image: "i" }, fakeFetch),
    (err) => {
      assert.ok(err instanceof AssessError);
      assert.equal(err.kind, "network");
      assert.match(err.message, /fetch failed/);
      return true;
    },
  );
});

test("client: schema-violating body throws AssessError kind=invalid", async () => {
  const fakeFetch = async () => ({ ok: true, status: 200, statusText: "OK", json: async () => ({ hello: "world" }) });
  await assert.rejects(
    assessFrame("/api/assess", { timestamp: "t", image: "i" }, fakeFetch),
    (err) => {
      assert.ok(err instanceof AssessError);
      assert.equal(err.kind, "invalid");
      assert.match(err.message, /schema validation/);
      return true;
    },
  );
});

test("client: non-JSON body throws AssessError kind=invalid", async () => {
  const fakeFetch = async () => ({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => { throw new SyntaxError("Unexpected token"); },
  });
  await assert.rejects(
    assessFrame("/api/assess", { timestamp: "t", image: "i" }, fakeFetch),
    (err) => err instanceof AssessError && err.kind === "invalid",
  );
});

// ---------- session log ----------

test("log: export has the documented shape and sequenced entries", () => {
  const fixed = new Date("2026-10-28T10:16:00.000Z");
  const log = new SessionLog({ nowFn: () => fixed });

  const e1 = log.record({
    requestTimestamp: "2026-10-28T10:15:00.000Z",
    latencyMs: 812,
    status: "ok",
    response: validAssessment(),
    scenarioLabel: "staged-fall-01",
  });
  const e2 = log.record({
    requestTimestamp: "2026-10-28T10:15:03.000Z",
    latencyMs: 45,
    status: "http_error",
    error: "Endpoint returned HTTP 503 Service Unavailable",
  });

  assert.equal(e1.seq, 1);
  assert.equal(e2.seq, 2);

  const out = log.toExport({ endpoint: "/api/assess", samplingIntervalSeconds: 3 });
  assert.equal(out.app, "meta-sentinel-frontend");
  assert.equal(out.exported_at, "2026-10-28T10:16:00.000Z");
  assert.equal(out.endpoint, "/api/assess");
  assert.equal(out.sampling_interval_seconds, 3);
  assert.equal(out.entry_count, 2);
  assert.equal(out.entries.length, 2);
  assert.equal(out.entries[0].status, "ok");
  assert.equal(out.entries[0].latency_ms, 812);
  assert.equal(out.entries[0].scenario_label, "staged-fall-01");
  assert.deepEqual(out.entries[0].response, validAssessment());
  assert.equal(out.entries[1].status, "http_error");
  assert.equal(out.entries[1].response, null);
  assert.match(out.entries[1].error, /503/);
});

test("log: entries() returns a copy and clear() resets sequence", () => {
  const log = new SessionLog();
  log.record({ requestTimestamp: "t", latencyMs: 1, status: "ok" });
  const copy = log.entries();
  copy.push({ seq: 99 });
  assert.equal(log.count, 1);
  log.clear();
  assert.equal(log.count, 0);
  const again = log.record({ requestTimestamp: "t", latencyMs: 1, status: "ok" });
  assert.equal(again.seq, 1);
});

test("log: rejects an unknown status", () => {
  const log = new SessionLog();
  assert.throws(
    () => log.record({ requestTimestamp: "t", latencyMs: 1, status: "made_up" }),
    RangeError,
  );
});
