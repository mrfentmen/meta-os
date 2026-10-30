// Agent 1 lane: the real web client (js/client.js) against the real Agent 2
// server (server/server.mjs) over HTTP — no fetch doubles, no model.
// The server runs with an empty environment, so the model is not
// configured and live calls are held: the honest path the UI must show
// is a 503 with the server's real message, never an invented assessment.
// This exercises the client code the page actually ships, not a copy.

import test from "node:test";
import assert from "node:assert/strict";

import { assessFrame, checkHealth, AssessError } from "../js/client.js";
import { createAssessServer } from "../server/server.mjs";

// Minimal bytes carrying the JPEG magic prefix; the server validates the
// envelope, not the picture — interpreting pixels is the model's job.
const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
const JPEG_URL = `data:image/jpeg;base64,${JPEG_BYTES.toString("base64")}`;

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

test("live health check reports the held model state, not readiness", async () => {
  await withServer(async (base) => {
    const health = await checkHealth(`${base}/api/assess`);
    assert.equal(health.ok, true);
    assert.deepEqual([...health.products].sort(), ["ignis", "medicus", "vigiles"]);
    assert.equal(health.model.live_enabled, false);
    assert.equal(health.model.configured, false);
  });
});

test("live assess request surfaces the real 503 held error, no assessment", async () => {
  await withServer(async (base) => {
    await assert.rejects(
      assessFrame(`${base}/api/assess`, {
        product: "ignis",
        timestamp: "2026-10-28T12:00:00.000Z",
        image: JPEG_URL,
      }),
      (err) => {
        assert.ok(err instanceof AssessError);
        assert.equal(err.kind, "http");
        assert.match(err.message, /503/);
        assert.match(err.message, /held/i);
        return true;
      },
    );
  });
});

test("live assess request with a bad product surfaces the real 400", async () => {
  await withServer(async (base) => {
    await assert.rejects(
      assessFrame(`${base}/api/assess`, {
        product: "nope",
        timestamp: "2026-10-28T12:00:00.000Z",
        image: JPEG_URL,
      }),
      (err) => {
        assert.ok(err instanceof AssessError);
        assert.equal(err.kind, "http");
        assert.match(err.message, /400/);
        return true;
      },
    );
  });
});

test("live server serves the actual web frontend entry point", async () => {
  await withServer(async (base) => {
    const res = await fetch(`${base}/`);
    assert.equal(res.status, 200);
    const html = await res.text();
    assert.match(html, /js\/app\.js/);
    assert.match(html, /Vigiles/);
  });
});
