// Server tests (Rowan's lane): POST /api/assess core + HTTP wiring.
// Run by `npm test`. The model is injected at the handler boundary in
// the success/failure tests — a test double, clearly labelled, used only
// to exercise the server's validation plumbing. The production adapter
// (server/model.mjs) is tested separately in its real states, and in
// every one of them it refuses rather than fabricating an assessment.

import test from "node:test";
import assert from "node:assert/strict";

import { handleAssess, validateAssessRequest, parseImageDataUrl } from "../server/assess.mjs";
import { assessWithModel, modelStatus, PRODUCT_PROFILES } from "../server/model.mjs";
import { createAssessServer } from "../server/server.mjs";
import { validateAssessment } from "../js/schema.js";

// Minimal bytes carrying the JPEG magic prefix; the server validates the
// envelope, not the picture — interpreting pixels is the model's job.
const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
const JPEG_URL = `data:image/jpeg;base64,${JPEG_BYTES.toString("base64")}`;
const GOOD_REQUEST = { product: "ignis", timestamp: "2026-10-28T12:00:00.000Z", image: JPEG_URL };

function validAssessment(product) {
  return {
    product,
    timestamp: "2026-10-28T12:00:01.000Z",
    observations: [
      { category: "visible smoke", description: "Grey plume above the roofline.", evidence: "upper third of frame", confidence: 0.8 },
    ],
    assessment: {
      category: "visible smoke",
      summary: "Smoke visible; no flame in frame.",
      uncertainty: ["Distance to source unknown."],
      requires_human_review: true,
    },
    processing: { model: "test-double", latency_ms: 12 },
  };
}

test("request validation accepts the exact client payload shape", () => {
  const r = validateAssessRequest(GOOD_REQUEST);
  assert.equal(r.ok, true);
  assert.equal(r.value.product, "ignis");
  assert.equal(r.value.mediaType, "image/jpeg");
  assert.equal(r.value.imageBytes.length, JPEG_BYTES.length);
});

test("request validation rejects non-objects, bad products, bad timestamps", () => {
  assert.equal(validateAssessRequest(null).ok, false);
  assert.equal(validateAssessRequest([1, 2]).ok, false);
  assert.equal(validateAssessRequest({ ...GOOD_REQUEST, product: "ember" }).ok, false);
  assert.equal(validateAssessRequest({ ...GOOD_REQUEST, timestamp: "Oct 28 2026" }).ok, false);
  assert.equal(validateAssessRequest({ ...GOOD_REQUEST, timestamp: "2026-02-30T12:00:00Z" }).ok, false);
  assert.equal(validateAssessRequest({ ...GOOD_REQUEST, timestamp: "2026-10-28 12:00:00" }).ok, false);
});

test("image parsing rejects wrong types, bad magic, and empty payloads", () => {
  assert.ok(parseImageDataUrl("https://example.com/x.jpg").error);
  assert.ok(parseImageDataUrl("data:image/png;base64,iVBORw0KGgo=").error);
  const notJpeg = `data:image/jpeg;base64,${Buffer.from("plain text").toString("base64")}`;
  assert.ok(parseImageDataUrl(notJpeg).error);
  assert.ok(parseImageDataUrl("data:image/jpeg;base64,").error);
  assert.ok(parseImageDataUrl(42).error);
});

test("default adapter state: handler answers 503 held, with no assessment fields", async () => {
  const { status, body } = await handleAssess(GOOD_REQUEST, { env: {} });
  assert.equal(status, 503);
  assert.equal(typeof body.error, "string");
  assert.match(body.error, /held/i);
  assert.equal(body.observations, undefined);
  assert.equal(body.assessment, undefined);
});

test("adapter refuses in every pre-test-phase state and never fabricates", async () => {
  const input = { product: "ignis", timestamp: GOOD_REQUEST.timestamp, imageBytes: JPEG_BYTES, mediaType: "image/jpeg" };
  await assert.rejects(() => assessWithModel(input, {}), /held/i);
  await assert.rejects(() => assessWithModel(input, { SPARK_API_KEY: "k" }), /held/i);
  await assert.rejects(() => assessWithModel(input, { ASSESS_LIVE_MODEL: "1" }), /SPARK_API_KEY/);
  await assert.rejects(
    () => assessWithModel(input, { ASSESS_LIVE_MODEL: "1", SPARK_API_KEY: "k" }),
    /not wired yet/i,
  );
});

test("model status reports slot state without any key material", () => {
  assert.deepEqual(modelStatus({}), { configured: false, live_enabled: false });
  assert.deepEqual(modelStatus({ SPARK_API_KEY: "secret-value", ASSESS_LIVE_MODEL: "1" }), {
    configured: true,
    live_enabled: true,
  });
});

test("product profiles cover all three products with their contract categories", () => {
  assert.deepEqual(Object.keys(PRODUCT_PROFILES).sort(), ["ignis", "medicus", "vigiles"]);
  assert.ok(PRODUCT_PROFILES.ignis.categories.includes("visible flame"));
  assert.ok(PRODUCT_PROFILES.vigiles.categories.includes("person down"));
  assert.ok(PRODUCT_PROFILES.medicus.categories.includes("person on ground"));
});

test("success path: model output is returned only after contract validation", async () => {
  const { status, body } = await handleAssess(GOOD_REQUEST, {
    assessModel: async (input) => validAssessment(input.product),
    env: {},
  });
  assert.equal(status, 200);
  assert.equal(validateAssessment(body, "ignis").ok, true);
  assert.equal(body.processing.model, "test-double");
});

test("off-contract model output is rejected with 502, never passed through", async () => {
  const broken = async () => ({ product: "ignis", timestamp: "nope" });
  const { status, body } = await handleAssess(GOOD_REQUEST, { assessModel: broken, env: {} });
  assert.equal(status, 502);
  assert.match(body.error, /contract validation/);
});

test("a throwing model becomes a 502 with the real message", async () => {
  const boom = async () => {
    throw new Error("upstream timeout after 30s");
  };
  const { status, body } = await handleAssess(GOOD_REQUEST, { assessModel: boom, env: {} });
  assert.equal(status, 502);
  assert.match(body.error, /upstream timeout/);
});

test("bad requests never reach the model", async () => {
  let calls = 0;
  const counting = async () => {
    calls += 1;
    return validAssessment("ignis");
  };
  const { status } = await handleAssess({ product: "nope" }, { assessModel: counting, env: {} });
  assert.equal(status, 400);
  assert.equal(calls, 0);
});

async function withServer(fn) {
  const server = createAssessServer({ env: {} });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    await fn(base);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("HTTP: health, held assess, bad JSON, wrong method, static index", async () => {
  await withServer(async (base) => {
    const health = await (await fetch(`${base}/api/health`)).json();
    assert.equal(health.ok, true);
    assert.equal(health.service, "meta-trio-assess");
    assert.deepEqual(health.model, { configured: false, live_enabled: false });

    const held = await fetch(`${base}/api/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(GOOD_REQUEST),
    });
    assert.equal(held.status, 503);
    assert.match((await held.json()).error, /held/i);

    const badJson = await fetch(`${base}/api/assess`, { method: "POST", body: "{not json" });
    assert.equal(badJson.status, 400);

    const wrongMethod = await fetch(`${base}/api/assess`, { method: "GET" });
    assert.equal(wrongMethod.status, 405);

    const unknown = await fetch(`${base}/api/nope`);
    assert.equal(unknown.status, 404);

    const index = await fetch(`${base}/`);
    assert.equal(index.status, 200);
    assert.match(index.headers.get("content-type"), /text\/html/);
    assert.match(await index.text(), /Meta/);
  });
});
