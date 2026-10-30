// Spark transport tests (Rowan's lane): the gate-3 wiring in
// server/model.mjs, exercised only through an injected stub fetch.
// No test here ever fires a live call, and the stub key is a fake
// test-only string, never a real credential.

import test from "node:test";
import assert from "node:assert/strict";

import {
  assessWithModel,
  ModelError,
  SPARK_ENDPOINT,
  SPARK_MODEL,
  buildSparkPrompt,
} from "../server/model.mjs";
import { PRODUCT_BY_ID } from "../js/products.js";

// Minimal bytes carrying the JPEG magic prefix; the transport sends the
// envelope, not a picture — interpreting pixels is the model's job.
const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
const INPUT = {
  product: "ignis",
  timestamp: "2026-10-28T12:00:00.000Z",
  imageBytes: JPEG_BYTES,
  mediaType: "image/jpeg",
};
const GATE_AND_KEY = { ASSESS_LIVE_MODEL: "1", SPARK_API_KEY: "test-key-not-real" };

function validAssessment(product) {
  return {
    product,
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [
      { category: "visible smoke", description: "Grey plume above the roofline.", evidence: "upper third of frame", confidence: 0.8 },
    ],
    assessment: {
      category: "visible smoke",
      summary: "Smoke visible; no flame in frame.",
      uncertainty: ["Distance to source unknown."],
      requires_human_review: true,
    },
    processing: { model: SPARK_MODEL, latency_ms: null },
  };
}

function stubFetch(response) {
  const calls = [];
  const fn = async (url, opts) => {
    calls.push({ url, opts });
    return response;
  };
  fn.calls = calls;
  return fn;
}

function jsonResponse(content) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ choices: [{ message: { content } }] }),
  };
}

test("transport: success sends the verified Spark shape and returns the parsed JSON unchanged", async () => {
  const expected = validAssessment("ignis");
  const fetch = stubFetch(jsonResponse(JSON.stringify(expected)));
  const result = await assessWithModel(INPUT, GATE_AND_KEY, { fetch });
  assert.deepEqual(result, expected);

  assert.equal(fetch.calls.length, 1);
  const { url, opts } = fetch.calls[0];
  assert.equal(url, SPARK_ENDPOINT);
  assert.equal(opts.method, "POST");
  assert.equal(opts.headers.Authorization, "Bearer test-key-not-real");
  assert.equal(opts.headers["Content-Type"], "application/json");
  const body = JSON.parse(opts.body);
  assert.equal(body.model, SPARK_MODEL);
  assert.equal(body.messages.length, 1);
  assert.equal(body.messages[0].role, "user");
  const [textPart, imagePart] = body.messages[0].content;
  assert.equal(textPart.type, "text");
  assert.match(textPart.text, /visible flame/);
  assert.match(textPart.text, /visible smoke/);
  assert.equal(imagePart.type, "image_url");
  assert.equal(imagePart.image_url.url, `data:image/jpeg;base64,${JPEG_BYTES.toString("base64")}`);
  // The key travels only in the Authorization header, never in the body.
  assert.equal(opts.body.includes("test-key-not-real"), false);
});

test("transport: prompt echoes the request product and timestamp and names the profile categories", () => {
  const prompt = buildSparkPrompt(PRODUCT_BY_ID.ignis, INPUT);
  assert.match(prompt, /"product": "ignis"/);
  assert.match(prompt, /"timestamp": "2026-10-28T12:00:00.000Z"/);
  assert.match(prompt, /steam or fog/);
  assert.match(prompt, /flame-like lighting/);
  assert.match(prompt, /Not a certified fire-detection system/);
});

test("transport: fenced JSON content is unwrapped, not rejected", async () => {
  const expected = validAssessment("ignis");
  const fetch = stubFetch(jsonResponse(`\`\`\`json\n${JSON.stringify(expected)}\n\`\`\``));
  const result = await assessWithModel(INPUT, GATE_AND_KEY, { fetch });
  assert.deepEqual(result, expected);
});

test("transport: non-200 from Spark is a typed model_call_failed", async () => {
  const fetch = stubFetch({ ok: false, status: 429 });
  await assert.rejects(
    () => assessWithModel(INPUT, GATE_AND_KEY, { fetch }),
    (err) => err instanceof ModelError && err.code === "model_call_failed" && /429/.test(err.message),
  );
});

test("transport: non-JSON content and missing content are typed model_call_failed", async () => {
  const notJson = stubFetch(jsonResponse("not json at all"));
  await assert.rejects(
    () => assessWithModel(INPUT, GATE_AND_KEY, { fetch: notJson }),
    (err) => err instanceof ModelError && err.code === "model_call_failed",
  );
  const empty = stubFetch({
    ok: true,
    status: 200,
    json: async () => ({ choices: [] }),
  });
  await assert.rejects(
    () => assessWithModel(INPUT, GATE_AND_KEY, { fetch: empty }),
    (err) => err instanceof ModelError && err.code === "model_call_failed",
  );
});

test("transport: missing image bytes fail typed before any fetch", async () => {
  const fetch = stubFetch(jsonResponse("{}"));
  await assert.rejects(
    () => assessWithModel({ product: "ignis", timestamp: INPUT.timestamp }, GATE_AND_KEY, { fetch }),
    (err) => err instanceof ModelError && err.code === "model_call_failed",
  );
  assert.equal(fetch.calls.length, 0);
});

test("transport: held and not_configured refuse before any fetch", async () => {
  const heldFetch = stubFetch(jsonResponse("{}"));
  await assert.rejects(() => assessWithModel(INPUT, {}, { fetch: heldFetch }), /held/i);
  await assert.rejects(
    () => assessWithModel(INPUT, { ASSESS_LIVE_MODEL: "1" }, { fetch: heldFetch }),
    /SPARK_API_KEY/,
  );
  assert.equal(heldFetch.calls.length, 0);
});
