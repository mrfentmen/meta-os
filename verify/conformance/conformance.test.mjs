// Conformance suite for POST /api/assess (Meta Trio v2 contract).
//
// Two modes:
// 1. Fixture mode (default): spawns verify/conformance/fixture-server.mjs
//    and drives it with the SHIPPED client (js/client.js) and validator
//    (js/schema.js). Proves the client, the validator, and the contract
//    shape agree, with no model and no key involved.
// 2. Live mode: set ASSESS_BASE_URL (e.g. http://localhost:8080) to run
//    the positive checks against a real server implementation. This is
//    the suite Rowan's server must pass. It fires no model calls itself;
//    what the server does behind the endpoint is the server's business,
//    and per Del's ruling Spark stays off until he starts the test phase.
//
// Run: node --test verify/conformance/conformance.test.mjs

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { assessFrame, AssessError } from "../../js/client.js";

const PRODUCTS = ["vigiles", "ignis", "sanitas"];
const FIXTURE_PORT = 18099;
const FIXTURE_URL = `http://localhost:${FIXTURE_PORT}/api/assess`;
const LIVE_BASE = process.env.ASSESS_BASE_URL || null;
const TS = "2026-10-28T14:00:00.000Z";
const IMG = "data:image/jpeg;base64,/9j/4AAQSkZJRg==";

let fixtureProc = null;

async function waitForFixture() {
  for (let i = 0; i < 50; i++) {
    try {
      await fetch(FIXTURE_URL, { method: "POST", body: "{}" });
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 100));
    }
  }
  throw new Error("fixture server did not start");
}

before(async () => {
  const fixturePath = fileURLToPath(new URL("./fixture-server.mjs", import.meta.url));
  fixtureProc = spawn(process.execPath, [fixturePath], {
    env: { ...process.env, PORT: String(FIXTURE_PORT) },
    stdio: "ignore",
  });
  await waitForFixture();
});

after(() => {
  if (fixtureProc) fixtureProc.kill();
});

for (const product of PRODUCTS) {
  test(`fixture: ${product} round trip passes the shipped validator`, async () => {
    const value = await assessFrame(FIXTURE_URL, { product, timestamp: TS, image: IMG });
    assert.equal(value.product, product);
    assert.equal(value.timestamp, TS);
    assert.ok(Array.isArray(value.observations));
    assert.equal(value.assessment.requires_human_review, true);
    assert.match(value.processing.model, /fixture/i);
    assert.ok(Object.hasOwn(value.processing, "latency_ms"));
    assert.equal(value.processing.latency_ms, null);
  });
}

test("fixture: unknown product is an error, never an assessment", async () => {
  await assert.rejects(
    () => assessFrame(FIXTURE_URL, { product: "bogus", timestamp: TS, image: IMG }),
    (err) => err instanceof AssessError,
  );
});

test("fixture: missing image is an error, never an assessment", async () => {
  await assert.rejects(
    () => assessFrame(FIXTURE_URL, { product: "vigiles", timestamp: TS }),
    (err) => err instanceof AssessError,
  );
});

test("fixture: unparseable JSON gets HTTP 400 with an error body", async () => {
  const res = await fetch(FIXTURE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{not json",
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(typeof body.error, "string");
  assert.ok(body.error.length > 0);
});

test("fixture: unknown route gets HTTP 404 with an error body", async () => {
  const res = await fetch(`http://localhost:${FIXTURE_PORT}/nope`, { method: "POST", body: "{}" });
  assert.equal(res.status, 404);
  const body = await res.json();
  assert.equal(typeof body.error, "string");
});

for (const product of PRODUCTS) {
  test(
    `live: ${product} round trip against ASSESS_BASE_URL`,
    { skip: LIVE_BASE ? false : "set ASSESS_BASE_URL to run against a real server" },
    async () => {
      const value = await assessFrame(`${LIVE_BASE}/api/assess`, {
        product,
        timestamp: new Date().toISOString(),
        image: IMG,
      });
      assert.equal(value.product, product);
      assert.ok(Object.hasOwn(value.processing, "latency_ms"));
    },
  );
}
