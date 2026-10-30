// Standalone tests for the Meta Nuntius relay (relay/relay.mjs).
//
// Run: node --test relay/relay.test.mjs
//
// Offline: every server binds an ephemeral localhost port, and the
// file-store test uses a temp directory. The repo's npm test script
// enumerates its files in package.json and does not list this file
// yet (see relay/README.md) — this suite is run directly.

import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";

import { createRelayServer } from "./relay.mjs";

async function start(options) {
  const server = createRelayServer(options);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return { server, base: `http://127.0.0.1:${server.address().port}` };
}

async function req(base, method, route, body) {
  const res = await fetch(base + route, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    /* viewer HTML etc. */
  }
  return { status: res.status, json, text };
}

let main;

before(async () => {
  main = await start({ storeFile: null });
});

after(() => main.server.close());

test("append then poll by watermark", async () => {
  const a = await req(main.base, "POST", "/rooms/main/messages", {
    nick: "pax",
    text: "first line",
  });
  assert.equal(a.status, 201);
  assert.equal(a.json.index, 0);
  const b = await req(main.base, "POST", "/rooms/main/messages", {
    nick: "del",
    text: "second line",
  });
  assert.equal(b.json.index, 1);

  const all = await req(main.base, "GET", "/rooms/main/messages?since=-1");
  assert.equal(all.json.room, "main");
  assert.equal(all.json.total, 2);
  assert.equal(all.json.messages.length, 2);
  assert.match(all.json.messages[0], /^pax: first line \[ts:\d+\]$/);
  assert.match(all.json.messages[1], /^del: second line \[ts:\d+\]$/);

  const afterFirst = await req(
    main.base,
    "GET",
    "/rooms/main/messages?since=0"
  );
  assert.deepEqual(afterFirst.json.messages, all.json.messages.slice(1));

  const caughtUp = await req(
    main.base,
    "GET",
    "/rooms/main/messages?since=1"
  );
  assert.deepEqual(caughtUp.json.messages, []);
  assert.equal(caughtUp.json.total, 2);

  const noSince = await req(main.base, "GET", "/rooms/main/messages");
  assert.equal(noSince.json.messages.length, 2);
});

test("rooms are isolated", async () => {
  await req(main.base, "POST", "/rooms/1/messages", {
    nick: "hana",
    text: "room one only",
  });
  const room1 = await req(main.base, "GET", "/rooms/1/messages?since=-1");
  assert.equal(room1.json.total, 1);
  const mainRoom = await req(
    main.base,
    "GET",
    "/rooms/main/messages?since=-1"
  );
  assert.equal(mainRoom.json.total, 2); // unchanged by the room-1 post
  assert.ok(!mainRoom.json.messages.some((l) => l.includes("room one")));
});

test("notify line format and deterministic id", async () => {
  const payload = {
    severity: "info",
    topic: "trio-result",
    text: "trio job trio-abc product ignis completed: category steam or fog",
  };
  const posted = await req(main.base, "POST", "/rooms/main/notify", payload);
  assert.equal(posted.status, 201);
  assert.match(posted.json.id, /^ntf-[0-9a-f]{16}$/);

  const again = await req(main.base, "POST", "/rooms/main/notify", payload);
  assert.equal(again.json.id, posted.json.id); // same basis, same id

  const lines = await req(
    main.base,
    "GET",
    `/rooms/main/messages?since=${posted.json.index - 1}`
  );
  assert.match(
    lines.json.messages[0],
    new RegExp(
      `^relay: NOTIFY:${posted.json.id} info \\[trio-result\\] ` +
        `trio job trio-abc product ignis completed: category steam or fog ` +
        `\\[ts:\\d+\\]$`
    )
  );
});

test("validation refusals", async () => {
  const cases = [
    ["POST", "/rooms/main/messages", { nick: "", text: "x" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "" }],
    ["POST", "/rooms/main/messages", { nick: "pa\nx", text: "x" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "two\nlines" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "x".repeat(2001) }],
    ["POST", "/rooms/main/notify", { severity: "loud", topic: "t", text: "x" }],
    ["POST", "/rooms/main/notify", { severity: "info", topic: "", text: "x" }],
    ["POST", "/rooms/Bad Room/messages", { nick: "pax", text: "x" }],
    ["GET", "/rooms/Bad Room/messages", undefined],
    ["POST", "/rooms/UPPER/messages", { nick: "pax", text: "x" }],
  ];
  for (const [method, route, body] of cases) {
    const res = await req(main.base, method, route, body);
    assert.equal(res.status, 400, `${method} ${route} ${JSON.stringify(body)}`);
    assert.ok(res.json && typeof res.json.error === "string");
  }
});

test("health names the memory store", async () => {
  const health = await req(main.base, "GET", "/health");
  assert.equal(health.status, 200);
  assert.equal(health.json.ok, true);
  assert.equal(health.json.store, "memory");
  assert.ok(health.json.rooms >= 2); // main + 1 were used above
});

test("viewer is served at /", async () => {
  const res = await req(main.base, "GET", "/");
  assert.equal(res.status, 200);
  assert.match(res.text, /Meta Nuntius/);
  assert.match(res.text, /Notifications/);
});

test("file store persists lines across a restart", async () => {
  const dir = mkdtempSync(path.join(tmpdir(), "nuntius-test-"));
  const storeFile = path.join(dir, "relay.jsonl");
  try {
    const first = await start({ storeFile });
    await req(first.base, "POST", "/rooms/main/messages", {
      nick: "milo",
      text: "persisted line",
    });
    await req(first.base, "POST", "/rooms/ops/notify", {
      severity: "warning",
      topic: "trio-result",
      text: "trio job trio-x product ignis failed: boom",
    });
    const health1 = await req(first.base, "GET", "/health");
    assert.equal(health1.json.store, "file");
    first.server.close();

    const second = await start({ storeFile });
    const mainLines = await req(
      second.base,
      "GET",
      "/rooms/main/messages?since=-1"
    );
    assert.equal(mainLines.json.total, 1);
    assert.match(mainLines.json.messages[0], /^milo: persisted line \[ts:\d+\]$/);
    const opsLines = await req(
      second.base,
      "GET",
      "/rooms/ops/messages?since=-1"
    );
    assert.equal(opsLines.json.total, 1);
    assert.match(
      opsLines.json.messages[0],
      /^relay: NOTIFY:ntf-[0-9a-f]{16} warning \[trio-result\] /
    );
    second.server.close();
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
