// Node built-in test runner, no dependencies:  node --test tests/ui.test.mjs
// Covers the pure logic the browser loads: trio product configs, v2 schema
// validation, sampler skip-while-in-flight, analysis client error handling,
// session log shape (with product) and storage persistence, still-image
// input validation and read.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { PRODUCTS, PRODUCT_BY_ID, PRODUCT_IDS, isProductId } from "../js/products.js";
import { validateAssessment } from "../js/schema.js";
import { FrameSampler } from "../js/sampler.js";
import { assessFrame, AssessError, checkHealth, healthUrlFor } from "../js/client.js";
import { SessionLog } from "../js/log.js";
import { isSupportedImageFile, readFileAsDataURL } from "../js/image_input.js";
import { isSupportedVideoFile, captureVideoFrame } from "../js/video_input.js";

function validAssessment(product = "vigiles") {
  return {
    product,
    timestamp: "2026-10-28T10:15:00.000Z",
    observations: [
      {
        category: "energetic movement",
        description: "person raising both arms",
        evidence: "both arms above shoulder height in frame",
        confidence: 0.72,
      },
    ],
    assessment: {
      category: "energetic movement",
      summary: "One person with raised arms; no contact with another person is visible.",
      uncertainty: ["Cannot determine intent or what happened before this frame."],
      requires_human_review: false,
    },
    processing: { model: "meta-model-test", latency_ms: 812 },
  };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

// ---------- trio product configs ----------

test("products: exactly the three trio products, in order", () => {
  assert.deepEqual(PRODUCT_IDS, ["vigiles", "ignis", "sanitas"]);
  assert.equal(PRODUCTS.length, 3);
  assert.equal(PRODUCT_BY_ID.vigiles.displayName, "Meta Vigiles");
  assert.equal(PRODUCT_BY_ID.ignis.displayName, "Meta Ignis");
  assert.equal(PRODUCT_BY_ID.sanitas.displayName, "Meta Sanitas");
});

test("products: every product has identity, categories, scenarios, limitations, guidance", () => {
  for (const p of PRODUCTS) {
    assert.equal(typeof p.displayName, "string");
    assert.ok(p.displayName.length > 0, `${p.id} displayName`);
    assert.ok(p.department.length > 0, `${p.id} department`);
    assert.ok(p.tagline.length > 0, `${p.id} tagline`);
    assert.ok(p.limitations.length > 0, `${p.id} limitations`);
    assert.ok(p.inputGuidance.length > 0, `${p.id} inputGuidance`);
    assert.ok(Array.isArray(p.categories) && p.categories.length > 0, `${p.id} categories`);
    assert.ok(Array.isArray(p.scenarios) && p.scenarios.length > 0, `${p.id} scenarios`);
    assert.match(p.accent, /^#[0-9a-f]{6}$/, `${p.id} accent`);
    for (const c of p.categories) assert.equal(typeof c, "string");
    for (const s of p.scenarios) assert.equal(typeof s, "string");
  }
});

test("products: scenario sets differ per product", () => {
  assert.ok(PRODUCT_BY_ID.vigiles.scenarios.includes("A staged argument"));
  assert.ok(PRODUCT_BY_ID.ignis.scenarios.includes("Visible smoke"));
  assert.ok(PRODUCT_BY_ID.sanitas.scenarios.includes("An overflowing trash bin"));
  assert.ok(!PRODUCT_BY_ID.ignis.scenarios.includes("A staged argument"));
  assert.ok(!PRODUCT_BY_ID.sanitas.scenarios.includes("Visible smoke"));
});

test("products: isProductId accepts only the trio ids", () => {
  assert.equal(isProductId("vigiles"), true);
  assert.equal(isProductId("ignis"), true);
  assert.equal(isProductId("sanitas"), true);
  assert.equal(isProductId("sentinel"), false);
  assert.equal(isProductId(""), false);
  assert.equal(isProductId(null), false);
  assert.equal(isProductId(undefined), false);
});

// ---------- v2 schema validation ----------

test("schema: accepts a valid v2 assessment", () => {
  const result = validateAssessment(validAssessment(), "vigiles");
  assert.equal(result.ok, true);
  assert.deepEqual(result.errors, []);
});

test("schema: accepts a valid assessment for each product", () => {
  for (const id of PRODUCT_IDS) {
    assert.equal(validateAssessment(validAssessment(id), id).ok, true);
  }
});

test("schema: accepts zero observations, empty uncertainty, null confidence, null latency", () => {
  const value = validAssessment();
  value.observations = [];
  value.assessment.uncertainty = [];
  value.processing.latency_ms = null;
  assert.equal(validateAssessment(value, "vigiles").ok, true);

  const nullConfidence = validAssessment();
  nullConfidence.observations[0].confidence = null;
  assert.equal(validateAssessment(nullConfidence, "vigiles").ok, true);
});

test("schema: accepts an empty evidence string and extra fields", () => {
  const value = validAssessment();
  value.observations[0].evidence = "";
  value.extra_field = { anything: true };
  value.assessment.extra = 1;
  assert.equal(validateAssessment(value, "vigiles").ok, true);
});

const malformedCases = [
  ["null", null, "vigiles"],
  ["an array", [], "vigiles"],
  ["a string", "not an object", "vigiles"],
  ["missing expected product", validAssessment(), undefined],
  ["missing product", (() => { const v = validAssessment(); delete v.product; return v; })(), "vigiles"],
  ["empty product", { ...validAssessment(), product: "  " }, "vigiles"],
  ["wrong product", validAssessment("vigiles"), "ignis"],
  ["product of another trio product", validAssessment("ignis"), "vigiles"],
  ["missing timestamp", (() => { const v = validAssessment(); delete v.timestamp; return v; })(), "vigiles"],
  ["unparseable timestamp", { ...validAssessment(), timestamp: "not-a-date" }, "vigiles"],
  ["free-form timestamp (Date.parse would accept)", { ...validAssessment(), timestamp: "Oct 28 2026" }, "vigiles"],
  ["timestamp without T separator", { ...validAssessment(), timestamp: "2026-10-28 10:15:00Z" }, "vigiles"],
  ["timestamp without timezone", { ...validAssessment(), timestamp: "2026-10-28T10:15:00" }, "vigiles"],
  ["impossible timestamp date", { ...validAssessment(), timestamp: "2026-02-30T10:15:00.000Z" }, "vigiles"],
  ["observations not an array", { ...validAssessment(), observations: "none" }, "vigiles"],
  ["observation not an object", { ...validAssessment(), observations: ["x"] }, "vigiles"],
  ["observation missing category", { ...validAssessment(), observations: [{ description: "d", evidence: "e", confidence: 0.5 }] }, "vigiles"],
  ["observation empty category", { ...validAssessment(), observations: [{ category: "  ", description: "d", evidence: "e", confidence: 0.5 }] }, "vigiles"],
  ["observation missing description", { ...validAssessment(), observations: [{ category: "c", evidence: "e", confidence: 0.5 }] }, "vigiles"],
  ["observation missing evidence", { ...validAssessment(), observations: [{ category: "c", description: "d", confidence: 0.5 }] }, "vigiles"],
  ["observation non-string evidence", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: 7, confidence: 0.5 }] }, "vigiles"],
  ["confidence missing", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: "e" }] }, "vigiles"],
  ["confidence above 1", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: "e", confidence: 1.5 }] }, "vigiles"],
  ["confidence below 0", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: "e", confidence: -0.1 }] }, "vigiles"],
  ["confidence not a number", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: "e", confidence: "high" }] }, "vigiles"],
  ["confidence boolean (JSON true is not a number)", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: "e", confidence: true }] }, "vigiles"],
  ["confidence NaN", { ...validAssessment(), observations: [{ category: "c", description: "d", evidence: "e", confidence: Number.NaN }] }, "vigiles"],
  ["missing assessment", (() => { const v = validAssessment(); delete v.assessment; return v; })(), "vigiles"],
  ["assessment not an object", { ...validAssessment(), assessment: "fine" }, "vigiles"],
  ["assessment missing category", { ...validAssessment(), assessment: { ...validAssessment().assessment, category: "" } }, "vigiles"],
  ["assessment non-string summary", { ...validAssessment(), assessment: { ...validAssessment().assessment, summary: 42 } }, "vigiles"],
  ["assessment missing uncertainty", (() => { const v = validAssessment(); delete v.assessment.uncertainty; return v; })(), "vigiles"],
  ["assessment uncertainty not an array", { ...validAssessment(), assessment: { ...validAssessment().assessment, uncertainty: "unknown" } }, "vigiles"],
  ["assessment uncertainty non-string item", { ...validAssessment(), assessment: { ...validAssessment().assessment, uncertainty: [1] } }, "vigiles"],
  ["requires_human_review missing", (() => { const v = validAssessment(); delete v.assessment.requires_human_review; return v; })(), "vigiles"],
  ["requires_human_review not boolean", { ...validAssessment(), assessment: { ...validAssessment().assessment, requires_human_review: "yes" } }, "vigiles"],
  ["requires_human_review numeric 1 is not a boolean", { ...validAssessment(), assessment: { ...validAssessment().assessment, requires_human_review: 1 } }, "vigiles"],
  ["missing processing", (() => { const v = validAssessment(); delete v.processing; return v; })(), "vigiles"],
  ["processing not an object", { ...validAssessment(), processing: "fast" }, "vigiles"],
  ["processing empty model", { ...validAssessment(), processing: { model: "  ", latency_ms: 1 } }, "vigiles"],
  ["processing latency missing", { ...validAssessment(), processing: { model: "m" } }, "vigiles"],
  ["processing latency negative", { ...validAssessment(), processing: { model: "m", latency_ms: -5 } }, "vigiles"],
  ["processing latency string", { ...validAssessment(), processing: { model: "m", latency_ms: "fast" } }, "vigiles"],
  ["processing latency boolean", { ...validAssessment(), processing: { model: "m", latency_ms: false } }, "vigiles"],
];

for (const [name, value, expected] of malformedCases) {
  test(`schema: rejects ${name}`, () => {
    const result = validateAssessment(value, expected);
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

test("client: sends product with the request and returns the validated v2 assessment", async () => {
  let seenUrl = null;
  let seenInit = null;
  const fakeFetch = async (url, init) => {
    seenUrl = url;
    seenInit = init;
    return { ok: true, status: 200, statusText: "OK", json: async () => validAssessment("ignis") };
  };
  const payload = { product: "ignis", timestamp: "2026-10-28T10:15:00.000Z", image: "data:image/jpeg;base64,AAAA" };
  const result = await assessFrame("/api/assess", payload, fakeFetch);
  assert.deepEqual(result, validAssessment("ignis"));
  assert.equal(seenUrl, "/api/assess");
  assert.equal(seenInit.method, "POST");
  assert.deepEqual(JSON.parse(seenInit.body), payload);
  assert.equal(JSON.parse(seenInit.body).product, "ignis");
});

test("client: wrong-product response throws AssessError kind=invalid", async () => {
  const fakeFetch = async () => ({ ok: true, status: 200, statusText: "OK", json: async () => validAssessment("vigiles") });
  await assert.rejects(
    assessFrame("/api/assess", { product: "sanitas", timestamp: "t", image: "i" }, fakeFetch),
    (err) => {
      assert.ok(err instanceof AssessError);
      assert.equal(err.kind, "invalid");
      assert.match(err.message, /product: expected "sanitas", got "vigiles"/);
      return true;
    },
  );
});

test("client: HTTP 200 error body throws AssessError kind=invalid with the server message", async () => {
  const fakeFetch = async () => ({ ok: true, status: 200, statusText: "OK", json: async () => ({ error: "model overloaded" }) });
  await assert.rejects(
    assessFrame("/api/assess", { product: "vigiles", timestamp: "t", image: "i" }, fakeFetch),
    (err) => err instanceof AssessError && err.kind === "invalid" && /model overloaded/.test(err.message),
  );
});

test("client: HTTP error status throws AssessError kind=http with the status", async () => {
  const fakeFetch = async () => ({ ok: false, status: 503, statusText: "Service Unavailable", json: async () => ({}) });
  await assert.rejects(
    assessFrame("/api/assess", { product: "vigiles", timestamp: "t", image: "i" }, fakeFetch),
    (err) => {
      assert.ok(err instanceof AssessError);
      assert.equal(err.kind, "http");
      assert.match(err.message, /503/);
      return true;
    },
  );
});

test("client: HTTP error with a server error body includes that message", async () => {
  const fakeFetch = async () => ({
    ok: false, status: 502, statusText: "Bad Gateway",
    json: async () => ({ error: "upstream timeout" }),
  });
  await assert.rejects(
    assessFrame("/api/assess", { product: "vigiles", timestamp: "t", image: "i" }, fakeFetch),
    (err) => err instanceof AssessError && err.kind === "http" && /upstream timeout/.test(err.message),
  );
});

test("client: network failure throws AssessError kind=network", async () => {
  const fakeFetch = async () => { throw new TypeError("fetch failed"); };
  await assert.rejects(
    assessFrame("/api/assess", { product: "vigiles", timestamp: "t", image: "i" }, fakeFetch),
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
    assessFrame("/api/assess", { product: "vigiles", timestamp: "t", image: "i" }, fakeFetch),
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
    assessFrame("/api/assess", { product: "vigiles", timestamp: "t", image: "i" }, fakeFetch),
    (err) => err instanceof AssessError && err.kind === "invalid",
  );
});

// ---------- backend health check ----------

function validHealth() {
  return {
    ok: true,
    service: "meta-trio-assess",
    products: ["vigiles", "ignis", "sanitas"],
    model: { configured: false, live_enabled: false },
  };
}

test("health: healthUrlFor swaps /api/assess for /api/health, or appends it to a bare base", () => {
  assert.equal(healthUrlFor("/api/assess"), "/api/health");
  assert.equal(healthUrlFor("http://localhost:8080/api/assess"), "http://localhost:8080/api/health");
  assert.equal(healthUrlFor("http://localhost:8080"), "http://localhost:8080/api/health");
  assert.equal(healthUrlFor("http://localhost:8080/"), "http://localhost:8080/api/health");
});

test("health: checkHealth GETs the health route and returns the parsed body", async () => {
  let seenUrl = null;
  let seenInit = null;
  const fakeFetch = async (url, init) => {
    seenUrl = url;
    seenInit = init;
    return { ok: true, status: 200, statusText: "OK", json: async () => validHealth() };
  };
  const result = await checkHealth("/api/assess", fakeFetch);
  assert.deepEqual(result, validHealth());
  assert.equal(seenUrl, "/api/health");
  assert.equal(seenInit.method, "GET");
});

test("health: network failure throws AssessError kind=network", async () => {
  const fakeFetch = async () => { throw new TypeError("fetch failed"); };
  await assert.rejects(
    checkHealth("/api/assess", fakeFetch),
    (err) => err instanceof AssessError && err.kind === "network" && /fetch failed/.test(err.message),
  );
});

test("health: HTTP error status throws AssessError kind=http with the status", async () => {
  const fakeFetch = async () => ({ ok: false, status: 503, statusText: "Service Unavailable", json: async () => ({}) });
  await assert.rejects(
    checkHealth("/api/assess", fakeFetch),
    (err) => err instanceof AssessError && err.kind === "http" && /503/.test(err.message),
  );
});

test("health: malformed body throws AssessError kind=invalid, never a partial result", async () => {
  const fakeFetch = async () => ({ ok: true, status: 200, statusText: "OK", json: async () => ({ ok: true, service: "x" }) });
  await assert.rejects(
    checkHealth("/api/assess", fakeFetch),
    (err) => err instanceof AssessError && err.kind === "invalid",
  );
});

test("health: the shipped page has the check button and health line", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(html.includes('id="btn-backend-check"'), "page is missing the backend check button");
  assert.ok(html.includes('id="backend-health"'), "page is missing the backend health line");
});

// ---------- session log ----------

test("log: export has the documented shape, per-entry product, and top-level product", () => {
  const fixed = new Date("2026-10-28T10:16:00.000Z");
  const log = new SessionLog({ nowFn: () => fixed });

  const e1 = log.record({
    requestTimestamp: "2026-10-28T10:15:00.000Z",
    product: "vigiles",
    latencyMs: 812,
    status: "ok",
    response: validAssessment(),
    scenarioLabel: "A staged argument",
  });
  const e2 = log.record({
    requestTimestamp: "2026-10-28T10:15:03.000Z",
    product: "ignis",
    latencyMs: 45,
    status: "http_error",
    error: "Endpoint returned HTTP 503 Service Unavailable",
  });

  assert.equal(e1.seq, 1);
  assert.equal(e2.seq, 2);
  assert.equal(e1.product, "vigiles");
  assert.equal(e2.product, "ignis");

  const out = log.toExport({ endpoint: "/api/assess", samplingIntervalSeconds: 3, product: "ignis" });
  assert.equal(out.app, "meta-sentinel-frontend");
  assert.equal(out.exported_at, "2026-10-28T10:16:00.000Z");
  assert.equal(out.product, "ignis");
  assert.equal(out.endpoint, "/api/assess");
  assert.equal(out.sampling_interval_seconds, 3);
  assert.equal(out.entry_count, 2);
  assert.equal(out.entries.length, 2);
  assert.equal(out.entries[0].status, "ok");
  assert.equal(out.entries[0].latency_ms, 812);
  assert.equal(out.entries[0].product, "vigiles");
  assert.equal(out.entries[0].scenario_label, "A staged argument");
  assert.deepEqual(out.entries[0].response, validAssessment());
  assert.equal(out.entries[1].status, "http_error");
  assert.equal(out.entries[1].product, "ignis");
  assert.equal(out.entries[1].response, null);
  assert.match(out.entries[1].error, /503/);
});

test("log: entries keep their own product when the session switches products", () => {
  const log = new SessionLog();
  log.record({ requestTimestamp: "t1", product: "vigiles", latencyMs: 10, status: "ok" });
  log.record({ requestTimestamp: "t2", product: "sanitas", latencyMs: 12, status: "ok" });
  assert.deepEqual(log.entries().map((e) => e.product), ["vigiles", "sanitas"]);
});

test("log: entries() returns a copy and clear() resets sequence", () => {
  const log = new SessionLog();
  log.record({ requestTimestamp: "t", product: "vigiles", latencyMs: 1, status: "ok" });
  const copy = log.entries();
  copy.push({ seq: 99 });
  assert.equal(log.count, 1);
  log.clear();
  assert.equal(log.count, 0);
  const again = log.record({ requestTimestamp: "t", product: "vigiles", latencyMs: 1, status: "ok" });
  assert.equal(again.seq, 1);
});

function fakeStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, value),
    removeItem: (key) => store.delete(key),
    has: (key) => store.has(key),
  };
}

test("log: with storage, records are saved and restored with sequence intact", () => {
  const storage = fakeStorage();
  const first = new SessionLog({ storage });
  first.record({ requestTimestamp: "t1", product: "vigiles", latencyMs: 10, status: "ok", response: validAssessment() });
  first.record({ requestTimestamp: "t2", product: "ignis", latencyMs: 5, status: "network_error", error: "fetch failed" });
  assert.equal(storage.has("meta-trio-session-log-v1"), true);

  const reloaded = new SessionLog({ storage });
  assert.equal(reloaded.count, 2);
  assert.deepEqual(reloaded.entries().map((e) => e.seq), [1, 2]);
  assert.equal(reloaded.entries()[0].product, "vigiles");
  assert.equal(reloaded.entries()[1].error, "fetch failed");
  const next = reloaded.record({ requestTimestamp: "t3", product: "sanitas", latencyMs: 1, status: "ok" });
  assert.equal(next.seq, 3);
});

test("log: clear() removes the saved copy, so a reload starts empty", () => {
  const storage = fakeStorage();
  const log = new SessionLog({ storage });
  log.record({ requestTimestamp: "t", product: "vigiles", latencyMs: 1, status: "ok" });
  log.clear();
  assert.equal(storage.has("meta-trio-session-log-v1"), false);
  assert.equal(new SessionLog({ storage }).count, 0);
});

test("log: corrupt or malformed saved data is ignored, never fatal", () => {
  const corrupt = new SessionLog({ storage: fakeStorage({ "meta-trio-session-log-v1": "{not json" }) });
  assert.equal(corrupt.count, 0);
  const wrongShape = new SessionLog({ storage: fakeStorage({ "meta-trio-session-log-v1": JSON.stringify({ seq: 1 }) }) });
  assert.equal(wrongShape.count, 0);
  const mixed = new SessionLog({
    storage: fakeStorage({
      "meta-trio-session-log-v1": JSON.stringify([
        { seq: 1, status: "ok", request_timestamp: "t1", product: "vigiles" },
        { seq: 2, status: "made_up", request_timestamp: "t2", product: "vigiles" },
        { seq: "three", status: "ok", request_timestamp: "t3", product: "vigiles" },
      ]),
    }),
  });
  assert.equal(mixed.count, 1);
  assert.equal(mixed.entries()[0].seq, 1);
});

test("log: an unwritable store never breaks recording", () => {
  const broken = {
    getItem: () => null,
    setItem: () => { throw new Error("denied"); },
    removeItem: () => { throw new Error("denied"); },
  };
  const log = new SessionLog({ storage: broken });
  const entry = log.record({ requestTimestamp: "t", product: "vigiles", latencyMs: 1, status: "ok" });
  assert.equal(entry.seq, 1);
  assert.equal(log.count, 1);
  log.clear();
  assert.equal(log.count, 0);
});

test("log: rejects an unknown status", () => {
  const log = new SessionLog();
  assert.throws(
    () => log.record({ requestTimestamp: "t", product: "vigiles", latencyMs: 1, status: "made_up" }),
    RangeError,
  );
});

// ---------- still-image input ----------

test("image input: only image/* files are accepted", () => {
  assert.equal(isSupportedImageFile({ type: "image/jpeg" }), true);
  assert.equal(isSupportedImageFile({ type: "image/png" }), true);
  assert.equal(isSupportedImageFile({ type: "IMAGE/JPEG" }), true);
  assert.equal(isSupportedImageFile({ type: "text/plain" }), false);
  assert.equal(isSupportedImageFile({ type: "video/mp4" }), false);
  assert.equal(isSupportedImageFile({ type: "" }), false);
  assert.equal(isSupportedImageFile({}), false);
  assert.equal(isSupportedImageFile(null), false);
});

test("image input: readFileAsDataURL resolves with the reader result", async () => {
  const previous = globalThis.FileReader;
  class MockReader {
    readAsDataURL() {
      this.result = "data:image/jpeg;base64,abc";
      this.onload();
    }
  }
  globalThis.FileReader = MockReader;
  try {
    assert.equal(await readFileAsDataURL({ type: "image/jpeg" }), "data:image/jpeg;base64,abc");
  } finally {
    if (previous === undefined) delete globalThis.FileReader;
    else globalThis.FileReader = previous;
  }
});

test("image input: readFileAsDataURL rejects when the reader errors", async () => {
  const previous = globalThis.FileReader;
  class FailingReader {
    readAsDataURL() {
      this.error = new Error("read failed");
      this.onerror();
    }
  }
  globalThis.FileReader = FailingReader;
  try {
    await assert.rejects(() => readFileAsDataURL({ type: "image/jpeg" }), /read failed/);
  } finally {
    if (previous === undefined) delete globalThis.FileReader;
    else globalThis.FileReader = previous;
  }
});

// ---------- prerecorded-video input ----------

test("video input: only video/* files are accepted", () => {
  assert.equal(isSupportedVideoFile({ type: "video/mp4" }), true);
  assert.equal(isSupportedVideoFile({ type: "video/webm" }), true);
  assert.equal(isSupportedVideoFile({ type: "VIDEO/MP4" }), true);
  assert.equal(isSupportedVideoFile({ type: "image/jpeg" }), false);
  assert.equal(isSupportedVideoFile({ type: "text/plain" }), false);
  assert.equal(isSupportedVideoFile({ type: "" }), false);
  assert.equal(isSupportedVideoFile({}), false);
  assert.equal(isSupportedVideoFile(null), false);
});

test("video input: captureVideoFrame draws the current frame and returns a JPEG data URL", () => {
  const drawn = [];
  const video = { videoWidth: 640, videoHeight: 360 };
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ({ drawImage: (el, x, y, w, h) => drawn.push([el, x, y, w, h]) }),
    toDataURL: (type, quality) => `data:${type};base64,frame-${quality}`,
  };
  assert.equal(captureVideoFrame(video, canvas), "data:image/jpeg;base64,frame-0.8");
  assert.equal(canvas.width, 640);
  assert.equal(canvas.height, 360);
  assert.deepEqual(drawn, [[video, 0, 0, 640, 360]]);
});

test("video input: captureVideoFrame throws when the video has no dimensions yet", () => {
  const canvas = { getContext: () => { throw new Error("should not draw"); }, toDataURL: () => "" };
  assert.throws(() => captureVideoFrame({ videoWidth: 0, videoHeight: 0 }, canvas), /not ready yet/);
  assert.throws(() => captureVideoFrame({ videoWidth: 640, videoHeight: 0 }, canvas), /not ready yet/);
});

test("video input: the shipped page has the video panel elements", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /<input[^>]*id="video-input"[^>]*accept="video\/\*"/);
  assert.match(html, /<video[^>]*id="video-preview"[^>]*controls/);
  assert.match(html, /id="video-state"/);
  assert.match(html, /id="btn-video-assess"/);
});

// ---------- history inspection (web parity with the native timeline) ----------
// The native timeline's assessment rows are selectable and redisplay that
// assessment; the web history must do the same. No browser exists in this
// suite, so these are static checks on the shipped markup and wiring:
// the page explains the button, app.js adds one per assessment entry,
// and both the live path and the reload-restore path hand the validated
// assessment to the history item. Failure entries carry no assessment,
// so they get no button.

test("history: past assessments can be shown again from the web history", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /Show assessment.*Latest assessment panel/);
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /show\.textContent = "Show assessment"/);
  assert.match(app, /Showing an earlier assessment from .*not a new assessment/);
  // Live path: the submitted assessment reaches the history item.
  assert.match(app, /kind: assessment\.assessment\.requires_human_review \? "review" : "ok",\n\s+assessment,/);
  // Reload path: a restored log entry's response reaches the history item.
  assert.match(app, /kind: entry\.response\.assessment\.requires_human_review \? "review" : "ok",\n\s+assessment: entry\.response,/);
});

// ---------- empty history note (web parity with the native timeline) ----------
// The native timeline's empty state says analysis is running when it is,
// so the web history note must do the same: "No events yet." while idle,
// the running line while the sampler runs. No browser exists in this
// suite, so these are static checks on the shipped wiring: the note text
// follows sampler.running, and refreshButtons — called on every state
// change including analysis start, stop, and Reset — refreshes it.
test("history: empty history note says analysis is running, matching the native timeline", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /function updateHistoryEmpty\(\) \{/);
  assert.match(app, /els\.historyEmpty\.textContent = sampler\.running/);
  assert.match(app, /Analysis is running — assessments and errors will appear here as they arrive\./);
  assert.match(app, /function refreshButtons\(\) \{[\s\S]*?updateHistoryEmpty\(\);/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url), "utf8");
  assert.match(swift, /Analysis is running — assessments and errors will appear here as they arrive\./);
});

// ---------- last round trip (web parity with the native status bar) ----------
// The native app's status bar shows the client-measured last round trip,
// so the web Camera panel must show the same line, next to the sampler
// counters. No browser exists in this suite, so these are static checks
// on the shipped markup and wiring: the element exists, app.js fills it
// from the client-measured latency on both the success and the failure
// path of submitAssessment (never from the server-reported processing
// latency), and Reset clears it again.
test("status: web shows the client-measured last round trip, cleared by Reset", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /id="last-round-trip"/);
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /lastRoundTrip: \$\("last-round-trip"\)/);
  assert.match(app, /Last round trip: .* ms \(client-measured\)/);
  assert.equal((app.match(/updateLastRoundTrip\(latencyMs\);/g) || []).length, 2);
  assert.match(app, /els\.btnReset\.addEventListener\("click", \(\) => \{[\s\S]*?clearLastRoundTrip\(\);/);
});

// ---------- accessibility announcements ----------
// Static checks on the shipped markup and stylesheet: a new assessment
// and a backend-status change must be announced to screen readers, and
// keyboard focus on a product radio (whose input is visually hidden)
// must show a visible ring on its label. These are not DOM tests — the
// suite has no browser — so they assert on the exact attributes and
// rules the browser will use.

test("a11y: backend status and latest assessment are polite live regions", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  const backendTag = html.match(/<p[^>]*id="backend-status"[^>]*>/);
  assert.ok(backendTag, "backend-status element exists");
  assert.match(backendTag[0], /aria-live="polite"/, "backend status is announced");
  const latestTag = html.match(/<div[^>]*id="latest-assessment"[^>]*>/);
  assert.ok(latestTag, "latest-assessment element exists");
  assert.match(latestTag[0], /aria-live="polite"/, "latest assessment is announced");
  assert.match(latestTag[0], /aria-atomic="true"/, "latest assessment is announced whole");
});

test("a11y: keyboard focus on a product option shows a visible ring", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(css, /\.product-option:has\(input:focus-visible\)\s*\{[^}]*outline:/);
});
