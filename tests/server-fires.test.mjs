// Node built-in test runner, no dependencies:  node --test tests/server-fires.test.mjs
// Covers the FIRMS proxy module (server/fires.mjs): no-key refusal,
// CSV parsing through the shared layer helpers, upstream error
// propagation, in-memory caching, and deterministic test doubles
// (stub fetch). No network, no key, no live FIRMS.

import test from "node:test";
import assert from "node:assert/strict";

import { clearFiresCache, fetchFires, readFiresCached } from "../server/fires.mjs";

const HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight";
const ROW = "40.71,-74.00,320.5,1.0,1.0,2024-05-01,1200,N,VIIRS,h,5,410.2,22.5,D";

function stubFetch(text, { ok = true, status = 200 } = {}) {
  return async (url) => {
    stubFetch.lastUrl = String(url);
    return {
      ok,
      status,
      text: async () => text,
    };
  };
}

test("fetchFires parses the area CSV through the shared helpers", async () => {
  const body = await fetchFires(stubFetch(`${HEADER}\n${ROW}\n`), { mapKey: "TESTKEY" });
  assert.ok(body.fetchedAt);
  assert.equal(body.source, "VIIRS_SNPP_NRT");
  assert.equal(body.count, 1);
  assert.equal(body.dropped, 0);
  assert.equal(body.fires[0].latitude, 40.71);
  assert.equal(body.fires[0].frp, 22.5);
  assert.ok(String(stubFetch.lastUrl).includes("TESTKEY"));
  assert.ok(String(stubFetch.lastUrl).includes("world/1"));
});

test("fetchFires refuses without a key before any fetch", async () => {
  let fetched = false;
  const never = async () => {
    fetched = true;
    throw new Error("must not fetch");
  };
  await assert.rejects(fetchFires(never, { mapKey: "" }), /FIRMS_MAP_KEY/);
  await assert.rejects(fetchFires(never, {}), /FIRMS_MAP_KEY/);
  assert.equal(fetched, false);
});

test("fetchFires surfaces upstream HTTP failures", async () => {
  await assert.rejects(fetchFires(stubFetch("nope", { ok: false, status: 401 }), { mapKey: "K" }), /HTTP 401/);
});

test("readFiresCached serves stale cache and refetches after TTL", async () => {
  clearFiresCache();
  let calls = 0;
  const stub = async () => {
    calls += 1;
    return { ok: true, status: 200, text: async () => `${HEADER}\n${ROW}\n` };
  };
  const first = await readFiresCached(stub, { mapKey: "K" }, 1000);
  assert.equal(first.stale, false);
  assert.equal(calls, 1);
  const second = await readFiresCached(stub, { mapKey: "K" }, 1000 + 1000);
  assert.equal(second.stale, true);
  assert.equal(calls, 1);
  await readFiresCached(stub, { mapKey: "K" }, 1000 + 16 * 60 * 1000);
  assert.equal(calls, 2);
  clearFiresCache();
});
