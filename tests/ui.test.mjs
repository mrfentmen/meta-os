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
import { isSupportedImageFile, readFileAsDataURL, downscaleImageToDataURL } from "../js/image_input.js";
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
  assert.deepEqual(PRODUCT_IDS, ["vigiles", "ignis", "medicus"]);
  assert.equal(PRODUCTS.length, 3);
  assert.equal(PRODUCT_BY_ID.vigiles.displayName, "Meta Vigiles");
  assert.equal(PRODUCT_BY_ID.ignis.displayName, "Meta Ignis");
  assert.equal(PRODUCT_BY_ID.medicus.displayName, "Meta Medicus");
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
  assert.ok(PRODUCT_BY_ID.medicus.scenarios.includes("A person on the ground"));
  assert.ok(!PRODUCT_BY_ID.ignis.scenarios.includes("A staged argument"));
  assert.ok(!PRODUCT_BY_ID.medicus.scenarios.includes("Visible smoke"));
});

test("products: isProductId accepts only the trio ids", () => {
  assert.equal(isProductId("vigiles"), true);
  assert.equal(isProductId("ignis"), true);
  assert.equal(isProductId("medicus"), true);
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
    assessFrame("/api/assess", { product: "medicus", timestamp: "t", image: "i" }, fakeFetch),
    (err) => {
      assert.ok(err instanceof AssessError);
      assert.equal(err.kind, "invalid");
      assert.match(err.message, /product: expected "medicus", got "vigiles"/);
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
    products: ["vigiles", "ignis", "medicus"],
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
  log.record({ requestTimestamp: "t2", product: "medicus", latencyMs: 12, status: "ok" });
  assert.deepEqual(log.entries().map((e) => e.product), ["vigiles", "medicus"]);
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
  const next = reloaded.record({ requestTimestamp: "t3", product: "medicus", latencyMs: 1, status: "ok" });
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

test("image input: downscaleImageToDataURL draws the image at its own size and returns a JPEG data URL", () => {
  const drawn = [];
  const image = { naturalWidth: 640, naturalHeight: 360 };
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ({ drawImage: (el, x, y, w, h) => drawn.push([el, x, y, w, h]) }),
    toDataURL: (type, quality) => `data:${type};base64,still-${quality}`,
  };
  assert.equal(downscaleImageToDataURL(image, canvas), "data:image/jpeg;base64,still-0.8");
  assert.equal(canvas.width, 640);
  assert.equal(canvas.height, 360);
  assert.deepEqual(drawn, [[image, 0, 0, 640, 360]]);
});

test("image input: downscaleImageToDataURL downscales an oversize image to a 1280px longest side, like live capture", () => {
  const drawn = [];
  const image = { naturalWidth: 4000, naturalHeight: 3000 };
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ({ drawImage: (el, x, y, w, h) => drawn.push([el, x, y, w, h]) }),
    toDataURL: (type, quality) => `data:${type};base64,still-${quality}`,
  };
  assert.equal(downscaleImageToDataURL(image, canvas), "data:image/jpeg;base64,still-0.8");
  assert.equal(canvas.width, 1280);
  assert.equal(canvas.height, 960);
  assert.deepEqual(drawn, [[image, 0, 0, 1280, 960]]);
});

test("image input: downscaleImageToDataURL throws when the image has no dimensions yet", () => {
  const canvas = { getContext: () => { throw new Error("should not draw"); }, toDataURL: () => "" };
  assert.throws(() => downscaleImageToDataURL({ naturalWidth: 0, naturalHeight: 0 }, canvas), /not ready yet/);
  assert.throws(() => downscaleImageToDataURL({ naturalWidth: 640, naturalHeight: 0 }, canvas), /not ready yet/);
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

test("video input: captureVideoFrame downscales an oversize frame to a 1280px longest side, like live capture", () => {
  const drawn = [];
  const video = { videoWidth: 4000, videoHeight: 3000 };
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ({ drawImage: (el, x, y, w, h) => drawn.push([el, x, y, w, h]) }),
    toDataURL: (type, quality) => `data:${type};base64,frame-${quality}`,
  };
  assert.equal(captureVideoFrame(video, canvas), "data:image/jpeg;base64,frame-0.8");
  assert.equal(canvas.width, 1280);
  assert.equal(canvas.height, 960);
  assert.deepEqual(drawn, [[video, 0, 0, 1280, 960]]);
});

// ---------- native video frame downscale (native parity with the web video path) ----------
// The web video path, the native live camera, and the native still-image
// path all cap frames at a 1280px longest side at JPEG 0.8. The native
// video-frame path did neither — it encoded the extracted frame at
// full size with the default JPEG quality, so a 4K clip's frame could
// be several megabytes while every other frame path sailed under the
// server's request-body cap. No Swift toolchain exists in this sandbox,
// so this is a static check on the shipped Swift source, in the same
// style as the other native-parity checks in this suite.
test("video input: native video frame downscales to a 1280px longest side at JPEG 0.8, like live capture", () => {
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Services/VideoFrameService.swift", import.meta.url), "utf8");
  assert.match(swift, /private static let maxFrameDimension: CGFloat = 1280/);
  assert.match(swift, /private static let jpegQuality: CGFloat = 0\.8/);
  assert.match(swift, /if longestSide > maxFrameDimension \{\n\s+let scale = maxFrameDimension \/ longestSide/);
  assert.match(swift, /rep\.representation\(using: \.jpeg, properties: \[\.compressionFactor: jpegQuality\]\)/);
  assert.doesNotMatch(swift, /rep\.representation\(using: \.jpeg, properties: \[:\]\)/);
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

// ---------- video frame capture failure (web parity with the native app) ----------
// The native app's video-frame path records a capture failure directly
// in the timeline and the backend status, in the same shapes as a
// backend failure, because no request was made. The web panel only
// logged it and showed it in the video panel, so the failure never
// reached the history a reviewer reads. No browser exists in this
// suite, so these are static checks on the shipped wiring: the web
// capture catch sets the backend status to the capture message itself
// (not a backend message), adds an "Analysis request failed" history
// entry carrying that message, and still logs it with a null latency
// (no request, so the last round trip is untouched); the native side
// carries the same timeline insertion and backend-status error.
test("video input: a video frame capture failure lands in the web history and backend status, matching the native app", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /const message = `Video frame capture failed: \$\{err\.message\}`;/);
  assert.match(app, /error: message,\n\s+scenarioLabel,/);
  assert.match(app, /setBackendStatus\("error", message\);/);
  assert.match(app, /addHistoryItem\(\{\n\s+title: "Analysis request failed",\n\s+timestamp,\n\s+body: message,\n\s+kind: "error",/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url), "utf8");
  assert.match(swift, /let message = "Video frame capture failed: /);
  assert.match(swift, /backendStatus = \.error\(message\)/);
  assert.match(swift, /TimelineItem\(product: product, timestamp: timestamp, kind: \.failure\(message\)\)/);
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

// The idle half of the same empty state: the native timeline says
// "No events yet. Assessments and errors will appear here." while
// nothing runs, and the web note said only "No events yet." — which
// never says what will appear there. Same static-check shape as the
// running half: the idle branch of updateHistoryEmpty, the initial
// markup (the text before the first refreshButtons call), and the
// native idle line must all carry the full sentence.
test("history: idle empty history note matches the native timeline", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /els\.historyEmpty\.textContent = sampler\.running\n\s+\? "Analysis is running — assessments and errors will appear here as they arrive\."\n\s+: "No events yet\. Assessments and errors will appear here\.";/);
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /id="history-empty"[^>]*>No events yet\. Assessments and errors will appear here\.</);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url), "utf8");
  assert.match(swift, /Text\("No events yet\. Assessments and errors will appear here\."\)/);
});

// ---------- camera permission wait (web parity with the native camera) ----------
// The native camera has a requesting-permission state while the system
// prompt is up; the web panel said "Camera is off." through that wait.
// No browser exists in this suite, so these are static checks on the
// shipped wiring: the Start handler says the wait before awaiting the
// start, marks the start pending (refreshButtons() owns the disabled
// state from that flag, so no mid-wait refresh can re-enable Start),
// and the native side carries the same waiting text in its
// requesting-permission state.
test("camera: web Start says it is waiting for camera permission, matching the native camera", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /els\.btnCameraStart\.addEventListener\("click", async \(\) => \{[\s\S]*?setCameraState\("Waiting for camera permission…"\)/);
  assert.match(app, /cameraStartPending = true;\n\s+refreshButtons\(\);\n\s+setCameraState\("Waiting for camera permission…"\)/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url), "utf8");
  assert.match(swift, /Waiting for camera permission…/);
});

// ---------- waiting for the first assessment (web parity with the native latest panel) ----------
// The native app's Latest panel says "Waiting for the first
// assessment…" while a request is outstanding and no assessment has
// been shown yet; the web panel left "No assessment received yet." on
// screen through that wait, as if nothing were happening. No browser
// exists in this suite, so these are static checks on the shipped
// wiring: submitAssessment shows the waiting line only while no
// assessment has ever been displayed (renderLatest sets the flag, so a
// displayed assessment stays put during later requests), a failed
// first request shows the real backend error (the native panel shows
// its backend-status error the same way, and reserves "No assessment
// received yet." for when nothing has been attempted), Reset clears
// the flag, and the native panel carries the same waiting line.
test("latest: web panel waits for the first assessment, matching the native panel", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /let latestAssessmentShown = false;/);
  assert.match(app, /function renderLatest\(assessment, earlierNote = null\) \{\n\s+latestAssessmentShown = true;/);
  assert.match(app, /if \(!latestAssessmentShown\) \{\n\s+els\.latest\.textContent = "Waiting for the first assessment…";\n\s+\}/);
  assert.match(app, /if \(!latestAssessmentShown\) \{\n\s+els\.latest\.textContent = `Model backend not connected: \$\{err\.message\}`;\n\s+\}/);
  assert.match(app, /els\.btnReset\.addEventListener\("click", \(\) => \{[\s\S]*?latestAssessmentShown = false;\n\s+els\.latest\.textContent = "No assessment received yet\.";/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url), "utf8");
  assert.match(swift, /Text\("Waiting for the first assessment…"\)/);
  assert.match(swift, /\} else if case \.error\(let message\) = model\.backendStatus \{\n\s+Text\(message\)/);
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

// ---------- in-panel assessing notes (web parity with the native panels) ----------
// The native Still image panel shows "Sending still image…" and the
// native video panel shows "Sending video frame…" inside the panel
// while the request is outstanding. The web panels had only the generic
// in-flight line in the Camera panel, so a user watching the panel they
// just tapped saw nothing move. No browser exists in this suite, so
// these are static checks on the shipped markup and wiring: each panel
// carries its note hidden by default, its Assess handler shows the note
// while the request is out and hides it again when it settles (the video
// path also hides it on a capture failure, which never reaches the
// submit path), Clear hides it too, and the native panels carry the
// same lines.
test("panels: still-image and video panels show an in-panel sending note while assessing, matching the native panels", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /id="image-assessing"[^>]*hidden>Sending still image…</);
  assert.match(html, /id="video-assessing"[^>]*hidden>Sending video frame…</);
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /imageAssessing: \$\("image-assessing"\)/);
  assert.match(app, /videoAssessing: \$\("video-assessing"\)/);
  assert.match(app, /els\.btnImageAssess\.addEventListener\("click", async \(\) => \{[\s\S]*?els\.imageAssessing\.hidden = false;/);
  assert.match(app, /els\.btnImageAssess\.addEventListener\("click", async \(\) => \{[\s\S]*?els\.imageAssessing\.hidden = true;/);
  assert.match(app, /els\.btnVideoAssess\.addEventListener\("click", async \(\) => \{[\s\S]*?els\.videoAssessing\.hidden = false;/);
  assert.match(app, /els\.btnVideoAssess\.addEventListener\("click", async \(\) => \{[\s\S]*?els\.videoAssessing\.hidden = true;/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url), "utf8");
  assert.match(swift, /Text\("Sending still image…"\)/);
  assert.match(swift, /Text\("Sending video frame…"\)/);
});

// ---------- analysis-active banner (web parity with the native camera panel) ----------
// The native camera panel shows an ANALYSIS ACTIVE banner with the live
// sampling interval while analysis runs; the web Camera panel only had
// moving counters and a request-only in-flight line, so a running
// analysis with no request currently out was not visible at a glance.
// No browser exists in this suite, so these are static checks on the
// shipped markup and wiring: the banner element exists hidden by
// default with the default 3-second wording, updateAnalysisActive
// rewords it from the live interval and hides it unless the sampler
// runs, refreshButtons — called on analysis start, stop, and Reset —
// refreshes it, the interval-change handler refreshes it too, and the
// native panel carries the same banner.
test("camera: web shows an analysis-active banner while sampling, matching the native camera panel", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /id="analysis-active"[^>]*hidden>Analysis active — sampling one frame every 3 seconds\.</);
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /analysisActive: \$\("analysis-active"\)/);
  assert.match(app, /function updateAnalysisActive\(\) \{[\s\S]*?els\.analysisActive\.hidden = !sampler\.running;/);
  assert.match(app, /Analysis active — sampling one frame every \$\{seconds\} second/);
  assert.match(app, /function refreshButtons\(\) \{[\s\S]*?updateAnalysisActive\(\);/);
  assert.match(app, /els\.intervalSeconds\.addEventListener\("change", \(\) => \{[\s\S]*?updateAnalysisActive\(\);/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url), "utf8");
  assert.match(swift, /ANALYSIS ACTIVE — sampling one frame every/);
});

// ---------- live frame capture failure (web + native parity with the video path) ----------
// The prerecorded-video path on both frontends records a capture failure
// directly in the history/timeline and the backend status, in the same
// shapes as a backend failure. The live sampled-frame path only logged
// it, so a failed tick during a run never reached the history a
// reviewer reads, even though the sampler counted it as a failed tick.
// No browser exists in this suite, so these are static checks on the
// shipped wiring, anchored on runSample so they cannot pass off the
// video path: the web live catch builds the capture message, logs it
// with a null latency (no request, so the last round trip is untouched),
// sets the backend status to the capture message itself, and adds an
// "Analysis request failed" history entry carrying that message, then
// still rethrows so the sampler counts the tick as failed; the native
// live catch carries the same backend-status error and timeline
// insertion before rethrowing.
test("camera: a live frame capture failure lands in history and backend status, matching the video path", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /async function runSample\(\) \{[\s\S]*?const message = `Frame capture failed: \$\{err\.message\}`;/);
  assert.match(app, /async function runSample\(\) \{[\s\S]*?error: message,\n\s+scenarioLabel,/);
  assert.match(app, /async function runSample\(\) \{[\s\S]*?setBackendStatus\("error", message\);/);
  assert.match(app, /async function runSample\(\) \{[\s\S]*?addHistoryItem\(\{\n\s+title: "Analysis request failed",\n\s+timestamp,\n\s+body: message,\n\s+kind: "error",/);
  assert.match(app, /async function runSample\(\) \{[\s\S]*?throw err;\n\s+\}\n\s+await submitAssessment\(product, timestamp, image, scenarioLabel, "live-camera"\);/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url), "utf8");
  assert.match(swift, /private func runSample\(\) async throws \{[\s\S]*?let message = "Frame capture failed: /);
  assert.match(swift, /private func runSample\(\) async throws \{[\s\S]*?backendStatus = \.error\(message\)/);
  assert.match(swift, /private func runSample\(\) async throws \{[\s\S]*?TimelineItem\(product: requestProduct, timestamp: timestamp, kind: \.failure\(message\)\)/);
});

// ---------- no-request endpoint failure (web parity with the native client) ----------
// The native AssessClient rejects an endpoint that is not a valid http(s)
// URL before anything is sent, and reports a nil latency — no request was
// attempted, so there is no round trip to measure and AppModel leaves the
// last round trip alone. The web client passed every endpoint straight to
// fetch, so a mistyped scheme failed only when fetch rejected it, and the
// submit path then stamped the time-to-reject as a "last round trip" and
// logged it as a measured latency. These tests pin the fix at both ends:
// the client refuses before fetching (fetch is never called, for an
// assess request or a health check), an absolute http(s) endpoint still
// reaches fetch, and the submit catch logs a null latency and guards the
// round-trip display when the error says no request was made.
test("client: non-http(s) endpoint is rejected before any fetch, matching the native client", async () => {
  let calls = 0;
  const countingFetch = async () => {
    calls += 1;
    throw new Error("must not be called");
  };
  const payload = { product: "vigiles", timestamp: "t", image: "i" };
  for (const endpoint of ["ftp://example.com/api/assess", "http://exa mple/api/assess", "localhost:8080/api/assess"]) {
    calls = 0;
    await assert.rejects(
      assessFrame(endpoint, payload, countingFetch),
      (err) => {
        assert.ok(err instanceof AssessError);
        assert.equal(err.kind, "network");
        assert.equal(err.noRequest, true);
        assert.match(err.message, /not a valid http\(s\) URL/);
        return true;
      },
    );
    assert.equal(calls, 0);
  }
});

test("client: absolute http(s) endpoint still reaches fetch, and the health check rejects a bad scheme before fetching", async () => {
  let seenUrl = null;
  const fakeFetch = async (url) => {
    seenUrl = url;
    return { ok: true, status: 200, statusText: "OK", json: async () => validAssessment("vigiles") };
  };
  const result = await assessFrame(
    "http://localhost:8080/api/assess",
    { product: "vigiles", timestamp: "t", image: "i" },
    fakeFetch,
  );
  assert.equal(seenUrl, "http://localhost:8080/api/assess");
  assert.deepEqual(result, validAssessment("vigiles"));
  let healthCalls = 0;
  await assert.rejects(
    checkHealth("ftp://example.com/api/assess", async () => {
      healthCalls += 1;
      throw new Error("must not be called");
    }),
    (err) => err instanceof AssessError && err.kind === "network" && err.noRequest === true,
  );
  assert.equal(healthCalls, 0);
});

test("camera: a no-request failure leaves the last round trip alone and logs a null latency, matching the native client", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /async function submitAssessment\(product, timestamp, image, scenarioLabel, source\) \{[\s\S]*?const noRequest = err instanceof AssessError && err\.noRequest;/);
  assert.match(app, /async function submitAssessment\(product, timestamp, image, scenarioLabel, source\) \{[\s\S]*?const latencyMs = noRequest \? null : Math\.round\(performance\.now\(\) - started\);/);
  assert.match(app, /async function submitAssessment\(product, timestamp, image, scenarioLabel, source\) \{[\s\S]*?if \(latencyMs !== null\) \{\n\s+updateLastRoundTrip\(latencyMs\);\n\s+\}/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Services/AssessClient.swift", import.meta.url), "utf8");
  assert.match(swift, /throw AssessError\(kind: \.network, message: "Endpoint is not a valid http\(s\) URL: \\\(endpoint\)", latencyMs: nil\)/);
});

// ---------- empty summary / empty evidence (native parity with the web latest panel) ----------
// Summary and evidence need only be strings in the v2 contract, so a
// server may validly report either as empty. The native panel renders
// the summary paragraph only when it is non-empty and renders an
// observation's Evidence line only when its evidence is non-empty; the
// web panel rendered both unconditionally, leaving a blank paragraph
// for an empty summary and a bare "(; confidence …)" slot for empty
// evidence. No browser or Swift toolchain exists in this suite, so
// these are static checks on the shipped panel sources: the web
// renderLatest guards both fields, and the native view already does.
test("latest: web panel omits an empty summary, matching the native panel", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /if \(assessment\.assessment\.summary !== ""\) \{\n\s+const text = document\.createElement\("p"\);/);
  const swift = readFileSync(
    new URL("../native/Sources/MetaTrio/Views/AssessmentView.swift", import.meta.url),
    "utf8",
  );
  assert.match(swift, /if !response\.assessment\.summary\.isEmpty \{/);
});

test("latest: web observation line omits empty evidence, matching the native panel", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /const evidencePart = obs\.evidence !== "" \? `\$\{obs\.evidence\}; ` : "";/);
  assert.match(app, /` — \$\{obs\.description\} \(\$+\{evidencePart\}\$\{confidence\}\)`/);
  const swift = readFileSync(
    new URL("../native/Sources/MetaTrio/Views/AssessmentView.swift", import.meta.url),
    "utf8",
  );
  assert.match(swift, /if !observation\.evidence\.isEmpty \{/);
});

// ---------- observable-evidence note (native parity with the web latest panel) ----------
// The web Latest panel carries a note under the assessment saying
// assessments describe observable evidence only, pointing at the
// product limitations notice; the native Latest panel had nothing
// equivalent, so a bare assessment could be read as more than it
// claims. No browser or Swift toolchain exists in this suite, so
// these are static checks on the shipped markup and view source: the
// web note exists, and the native note sits in rightColumn next to
// the Latest panel (before the timeline), in the web panel's words.
test("latest: native panel carries the observable-evidence note, matching the web panel", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /Assessments describe observable evidence only\. Each product's limitations notice \(above\) states what its assessments never claim\./);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url), "utf8");
  const rightColumn = swift.slice(swift.indexOf("private var rightColumn"), swift.indexOf("TimelineView(model: model)"));
  assert.match(rightColumn, /Text\("Assessments describe observable evidence only\. Each product's limitations notice \(above\) states what its assessments never claim\."\)/);
});

// ---------- uncertainty section (web parity with the native latest panel) ----------
// The native panel gives uncertainty its own labeled section: one line
// per item, and "The model reported no uncertainty items." when the
// server reported none. The web panel squeezed the items into a single
// joined paragraph ("Uncertainty: …") and said "none stated" when
// empty, so a multi-item uncertainty read as one run-on sentence and
// an empty one softened the fact that the model reported nothing. No
// browser or Swift toolchain exists in this suite, so these are static
// checks on the shipped panel sources, anchored on renderLatest: the
// web panel builds the heading, one list item per uncertainty item,
// and the native empty wording, and the native view already does.
test("latest: web uncertainty section matches the native panel", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  const render = app.slice(app.indexOf("function renderLatest"), app.indexOf("function addHistoryItem"));
  assert.match(render, /uncertaintyHead\.textContent = "Uncertainty";/);
  assert.match(render, /for \(const item of assessment\.assessment\.uncertainty\) \{/);
  assert.match(render, /line\.textContent = item;/);
  assert.match(render, /uncertainty\.textContent = "The model reported no uncertainty items\.";/);
  assert.doesNotMatch(render, /Uncertainty: none stated\./);
  assert.doesNotMatch(render, /uncertainty\.join\(" "\)/);
  const swift = readFileSync(
    new URL("../native/Sources/MetaTrio/Views/AssessmentView.swift", import.meta.url),
    "utf8",
  );
  assert.match(swift, /Text\("Uncertainty"\)/);
  assert.match(swift, /Text\("The model reported no uncertainty items\."\)/);
  assert.match(swift, /ForEach\(Array\(response\.assessment\.uncertainty\.enumerated\(\)\), id: \\.offset\)/);
});

// ---------- contacting status on still-image / video assess (native parity with the web panels) ----------
// The web still-image and video handlers set the backend status to
// "Contacting…" while the request is outstanding; the native
// still-image and video paths went straight to submitAssessment, so
// the status bar kept showing the previous state for the whole flight
// (a stale "connected" from an earlier success). No browser or Swift
// toolchain exists in this suite, so these are static checks on the
// shipped wiring: the web handlers already set it, and both native run
// methods now set it before the request, where submitAssessment
// overwrites it on settle (connected or error) and a video capture
// failure overwrites it with the real error.
test("status: native still-image and video assess show a contacting status while the request is outstanding, matching the web panels", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /els\.btnImageAssess\.addEventListener\("click", async \(\) => \{[\s\S]*?setBackendStatus\("unknown", `Contacting model backend: \$\{currentEndpoint\(\)\} …`\);/,
  );
  assert.match(
    app,
    /els\.btnVideoAssess\.addEventListener\("click", async \(\) => \{[\s\S]*?setBackendStatus\("unknown", `Contacting model backend: \$\{currentEndpoint\(\)\} …`\);/,
  );
  const swift = readFileSync(
    new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
    "utf8",
  );
  const still = swift.slice(
    swift.indexOf("private func runStillImageAssessment"),
    swift.indexOf("func clearStillImage()"),
  );
  assert.match(
    still,
    /backendStatus = \.unknown\("Contacting model backend: \\\(trimmedEndpoint\) …"\)/,
  );
  assert.ok(
    still.indexOf('backendStatus = .unknown("Contacting model backend:') <
      still.indexOf("submitAssessment(product:"),
    "still-image contacting status is set before the request",
  );
  const video = swift.slice(
    swift.indexOf("private func runVideoFrameAssessment"),
    swift.indexOf("func clearVideo()"),
  );
  assert.match(
    video,
    /backendStatus = \.unknown\("Contacting model backend: \\\(trimmedEndpoint\) …"\)/,
  );
  assert.ok(
    video.indexOf('backendStatus = .unknown("Contacting model backend:') <
      video.indexOf("submitAssessment(product:"),
    "video contacting status is set before the request",
  );
});

// ---------- sampling interval clamp (web parity with the native Stepper) ----------
// The native interval Stepper can only hold 1–60, so the value on screen
// is always the value being sampled at. The web number box accepted
// anything — 99, 0, or blank — while the interval below silently fell
// back to 3 s, so the box and the disclosure (and the sampler) disagreed
// about the real interval. No browser exists in this suite, so these are
// static checks on the shipped wiring: the interval helper clamps to the
// range with the 3 s default only for a blank or non-numeric box, the
// change handler writes the clamped value back into the box before
// refreshing the disclosure and the sampler, and the native panel holds
// the same range in its Stepper.
test("config: web sampling interval clamps to 1–60 like the native Stepper, instead of silently falling back", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /function currentIntervalSeconds\(\) \{/);
  assert.match(app, /if \(!Number\.isFinite\(seconds\)\) return 3;/);
  assert.match(app, /return Math\.min\(60, Math\.max\(1, seconds\)\);/);
  assert.match(
    app,
    /els\.intervalSeconds\.addEventListener\("change", \(\) => \{\n\s+els\.intervalSeconds\.value = String\(currentIntervalSeconds\(\)\);/,
  );
  assert.match(
    app,
    /els\.intervalSeconds\.addEventListener\("change", \(\) => \{[\s\S]*?updateSamplingDisclosure\(\);/,
  );
  const swift = readFileSync(
    new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
    "utf8",
  );
  assert.match(swift, /Stepper\(value: \$model\.intervalSeconds, in: 1\.\.\.60\)/);
});

// ---------- reset across an in-flight request (web parity with the native app) ----------
// Reset clears the view, but it cannot cancel a request already out on
// the network: when that request settles, its success or failure used to
// repaint the cleared view — latest panel, history entry, backend
// status, last round trip — as if Reset had never happened. Both
// frontends now carry a view generation: submitAssessment captures it
// when the request starts, Reset bumps it, and the settle path only
// touches the screen when the numbers still match. The session-log
// entry is recorded either way: the request genuinely happened, and
// the log survives Reset by design. No browser exists in this suite,
// so these are static checks on the shipped wiring, plus the native
// video-extraction failure path, which also awaits and can straddle a
// Reset.
test("reset: a request outstanding across Reset logs but does not repaint the cleared view, matching the native app", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /let viewGeneration = 0;/);
  assert.match(app, /async function submitAssessment\(product, timestamp, image, scenarioLabel, source\) \{\n\s+const endpoint = currentEndpoint\(\);\n\s+const generation = viewGeneration;/);
  assert.match(app, /els\.btnReset\.addEventListener\("click", \(\) => \{\n\s+\/\/ Bump the view generation first[\s\S]*?\n\s+viewGeneration \+= 1;/);
  // Both settle paths log unconditionally and gate only the display.
  assert.match(app, /if \(generation === viewGeneration\) \{\n\s+updateLastRoundTrip\(latencyMs\);\n\s+setBackendStatus\("connected"/);
  assert.match(app, /if \(generation === viewGeneration\) \{\n\s+if \(latencyMs !== null\) \{\n\s+updateLastRoundTrip\(latencyMs\);\n\s+\}\n\s+setBackendStatus\("error"/);
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url), "utf8");
  assert.match(swift, /private var viewGeneration = 0/);
  assert.match(swift, /func resetSession\(\) \{\n\s+\/\/ Bump the view generation first[\s\S]*?\n\s+viewGeneration \+= 1/);
  assert.match(swift, /private func submitAssessment\(product: ProductID, timestamp: String, imageDataURL: String, scenarioLabel: String\?, generation: Int\)/);
  assert.doesNotMatch(swift, /let generation = viewGeneration/);
  assert.match(swift, /recordLog\(product: product, timestamp: timestamp, latencyMs: latencyMs, status: \.ok, response: response, scenarioLabel: scenarioLabel\)\n\s+if generation == viewGeneration \{/);
  assert.match(swift, /recordLog\(product: product, timestamp: timestamp, latencyMs: error\.latencyMs, status: status, error: error\.message, scenarioLabel: scenarioLabel\)\n\s+if generation == viewGeneration \{/);
  // The async video-extraction failure path carries the same guard,
  // now on the generation captured at tap time, not one re-read here.
  assert.match(swift, /private func runVideoFrameAssessment\(url: URL, seconds: Double, product: ProductID, scenarioLabel: String\?, generation: Int\)/);
  assert.match(swift, /recordLog\(product: product, timestamp: timestamp, latencyMs: nil, status: \.invalidResponse, error: message, scenarioLabel: scenarioLabel\)\n\s+if generation == viewGeneration \{/);
});

// ---------- in-flight indicator with overlapping requests ----------
// The Camera panel's "Analysis request in flight…" line (and the native
// status bar's equivalent) is shared by every submit path, but it used
// to be a single boolean: a live sampled frame, a still image, and a
// prerecorded-video frame can all be outstanding at once — the sampler
// guards only live-vs-live, and each panel guards only itself — so the
// first of several requests to settle hid the line while another was
// still out, and the UI claimed nothing was in flight when something
// was. Both frontends now count outstanding requests: the line shows
// while at least one is out and hides only when the last one settles.
// Reset never touches the count — a request outstanding across Reset
// is still outstanding. No browser exists in this suite, so these are
// static checks on the shipped wiring, in the same style as the Reset
// checks above.
test("in-flight: the loading line stays up until the last overlapping request settles, on web and native", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(app, /let inFlightCount = 0;/);
  assert.match(app, /function showInFlight\(\) \{\n\s+inFlightCount \+= 1;\n\s+els\.inFlight\.hidden = false;\n\}/);
  assert.match(app, /function hideInFlight\(\) \{\n\s+inFlightCount = Math\.max\(0, inFlightCount - 1\);\n\s+els\.inFlight\.hidden = inFlightCount === 0;\n\}/);
  // submitAssessment uses the counter at both ends, never the bare flip.
  const submit = app.slice(
    app.indexOf("async function submitAssessment"),
    app.indexOf("async function runSample"),
  );
  assert.match(submit, /const generation = viewGeneration;\n\s+showInFlight\(\);/);
  assert.match(submit, /\} finally \{\n\s+hideInFlight\(\);/);
  assert.doesNotMatch(submit, /els\.inFlight\.hidden/);
  // Reset leaves the count alone: the outstanding request is still out.
  const reset = app.slice(
    app.indexOf('els.btnReset.addEventListener'),
    app.indexOf('els.intervalSeconds.addEventListener'),
  );
  assert.doesNotMatch(reset, /inFlightCount|showInFlight|hideInFlight/);

  const swift = readFileSync(new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url), "utf8");
  assert.match(swift, /private var inFlightCount = 0/);
  assert.match(
    swift,
    /requestInFlight = true\n\s+inFlightCount \+= 1\n\s+defer \{\n\s+inFlightCount -= 1\n\s+if inFlightCount == 0 \{\n\s+requestInFlight = false/,
  );
  assert.doesNotMatch(swift, /defer \{ requestInFlight = false \}/);
  const nativeReset = swift.slice(
    swift.indexOf("func resetSession()"),
    swift.indexOf("// MARK: - Backend health check"),
  );
  assert.doesNotMatch(nativeReset, /inFlightCount|requestInFlight/);
});

// ---------- reset generation captured at sample/tap time (native) ----------
// The native submit path used to capture the view generation itself,
// when the request started. That left a hole the web frontend does not
// have, because its capture is synchronous: the native prerecorded-video
// frame extraction awaits between the tap and submit, so a Reset tapped
// mid-extraction gave submit the post-reset generation and its settling
// result repainted the view Reset had just cleared — while the
// extraction failure path, which kept the pre-extraction generation,
// correctly stayed dark. The same hole existed, smaller, in the Task hop
// between an Assess tap and its runner. The generation is now captured
// at sample or tap time, beside the product and the scenario, and
// threaded through to submit; a stale still-image or video runner
// returns before it sets any status or sends anything. No Swift
// toolchain exists in this suite, so these are static checks on the
// shipped wiring, in the same style as the Reset checks above.
test("reset: native view generation is captured at sample/tap time, so a Reset during video extraction cannot let the result repaint the cleared view", () => {
  const swift = readFileSync(new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url), "utf8");
  // Captured beside product and scenario on every path.
  assert.match(
    swift,
    /func assessStillImage\(\) \{[\s\S]*?let requestGeneration = viewGeneration[\s\S]*?runStillImageAssessment\(dataURL: dataURL, product: requestProduct, scenarioLabel: requestScenarioLabel, generation: requestGeneration\)/,
  );
  assert.match(
    swift,
    /func assessVideoFrame\(\) \{[\s\S]*?let requestGeneration = viewGeneration[\s\S]*?runVideoFrameAssessment\(url: url, seconds: seconds, product: requestProduct, scenarioLabel: requestScenarioLabel, generation: requestGeneration\)/,
  );
  const sample = swift.slice(
    swift.indexOf("private func runSample()"),
    swift.indexOf("try await submitAssessment(product: requestProduct"),
  );
  assert.match(sample, /let requestGeneration = viewGeneration/);
  assert.match(
    swift,
    /try await submitAssessment\(product: requestProduct, timestamp: timestamp, imageDataURL: image, scenarioLabel: requestScenarioLabel, generation: requestGeneration\)/,
  );
  // Submit takes the generation as a parameter and never re-reads it.
  assert.match(
    swift,
    /private func submitAssessment\(product: ProductID, timestamp: String, imageDataURL: String, scenarioLabel: String\?, generation: Int\)/,
  );
  const submit = swift.slice(
    swift.indexOf("private func submitAssessment("),
    swift.indexOf("private func recordLog("),
  );
  assert.doesNotMatch(submit, /viewGeneration =|let generation = viewGeneration/);
  assert.match(submit, /if generation == viewGeneration \{/);
  // Stale runners abort before touching the status bar or the network.
  const still = swift.slice(
    swift.indexOf("private func runStillImageAssessment"),
    swift.indexOf("func clearStillImage()"),
  );
  assert.ok(
    still.indexOf("guard generation == viewGeneration else { return }") <
      still.indexOf('backendStatus = .unknown("Contacting model backend:'),
    "stale still-image runner returns before setting the contacting status",
  );
  const video = swift.slice(
    swift.indexOf("private func runVideoFrameAssessment"),
    swift.indexOf("func clearVideo()"),
  );
  assert.ok(
    video.indexOf("guard generation == viewGeneration else { return }") <
      video.indexOf('backendStatus = .unknown("Contacting model backend:'),
    "stale video runner returns before setting the contacting status",
  );
  assert.ok(
    video.indexOf("guard generation == viewGeneration else { return }") <
      video.indexOf("try await VideoFrameService.jpegDataURL"),
    "stale video runner returns before extracting a frame",
  );
  // The video success path now passes the same tap-time generation the
  // extraction failure path already guarded on.
  assert.match(
    video,
    /try await submitAssessment\(product: product, timestamp: ISO8601\.now\(\), imageDataURL: dataURL, scenarioLabel: scenarioLabel, generation: generation\)/,
  );
});
