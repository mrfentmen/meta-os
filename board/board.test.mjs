// Tests for the Meta OS Board service (board/board.mjs).
//
// Run from the worktree root:  node --test board/board.test.mjs
//
// Every server binds an ephemeral localhost port; the persistence test
// uses a temporary directory. Nothing here touches the network beyond
// 127.0.0.1, and nothing is mocked — each test drives the real HTTP
// service end to end.

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";

import { createBoardServer } from "./board.mjs";

function boot(options) {
  return new Promise((resolve) => {
    const server = createBoardServer(options);
    server.listen(0, "127.0.0.1", () => {
      resolve({
        server,
        base: `http://127.0.0.1:${server.address().port}`,
      });
    });
  });
}

async function call(base, method, route, body) {
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
    /* the viewer is HTML, not JSON */
  }
  return { status: res.status, json, text };
}

let board;

before(async () => {
  board = await boot({ storeFile: null });
});

after(() => board.server.close());

test("health answers and names the memory store", async () => {
  const health = await call(board.base, "GET", "/health");
  assert.equal(health.status, 200);
  assert.equal(health.json.ok, true);
  assert.equal(health.json.store, "memory");
});

test("post then read back, in order, with protocol stamps", async () => {
  const first = await call(board.base, "POST", "/rooms/main/messages", {
    nick: "pax",
    text: "board is up",
  });
  assert.equal(first.status, 201);
  assert.equal(first.json.index, 0);

  const second = await call(board.base, "POST", "/rooms/main/messages", {
    nick: "del",
    text: "second line here",
  });
  assert.equal(second.status, 201);
  assert.equal(second.json.index, 1);

  const all = await call(board.base, "GET", "/rooms/main/messages?since=-1");
  assert.equal(all.status, 200);
  assert.equal(all.json.room, "main");
  assert.equal(all.json.total, 2);
  assert.match(all.json.messages[0], /^pax: board is up \[ts:\d+\]$/);
  assert.match(all.json.messages[1], /^del: second line here \[ts:\d+\]$/);
});

test("since returns only the lines after the given index", async () => {
  const tail = await call(board.base, "GET", "/rooms/main/messages?since=0");
  assert.equal(tail.json.total, 2);
  assert.equal(tail.json.messages.length, 1);
  assert.match(tail.json.messages[0], /^del: /);

  const caughtUp = await call(board.base, "GET", "/rooms/main/messages?since=1");
  assert.deepEqual(caughtUp.json.messages, []);
  assert.equal(caughtUp.json.total, 2);

  const noSince = await call(board.base, "GET", "/rooms/main/messages");
  assert.equal(noSince.json.messages.length, 2);
});

test("rooms are isolated from each other", async () => {
  await call(board.base, "POST", "/rooms/ops/messages", {
    nick: "hana",
    text: "ops room only",
  });
  const ops = await call(board.base, "GET", "/rooms/ops/messages?since=-1");
  assert.equal(ops.json.total, 1);
  assert.match(ops.json.messages[0], /^hana: ops room only \[ts:\d+\]$/);

  const main = await call(board.base, "GET", "/rooms/main/messages?since=-1");
  assert.equal(main.json.total, 2);
  assert.ok(!main.json.messages.some((line) => line.includes("ops room")));
});

test("GET /rooms lists rooms with their line counts", async () => {
  const res = await call(board.base, "GET", "/rooms");
  assert.equal(res.status, 200);
  const byName = new Map(res.json.rooms.map((r) => [r.room, r.count]));
  assert.equal(byName.get("main"), 2);
  assert.equal(byName.get("ops"), 1);
});

test("notify posts carry the NOTIFY line format and a stable id", async () => {
  const payload = { severity: "warning", topic: "kernel", text: "k6 boot ok" };
  const posted = await call(board.base, "POST", "/rooms/main/notify", payload);
  assert.equal(posted.status, 201);
  assert.match(posted.json.id, /^ntf-[0-9a-f]{16}$/);

  const again = await call(board.base, "POST", "/rooms/main/notify", payload);
  assert.equal(again.json.id, posted.json.id);

  const lines = await call(
    board.base,
    "GET",
    `/rooms/main/messages?since=${posted.json.index - 1}`
  );
  assert.match(
    lines.json.messages[0],
    new RegExp(
      `^board: NOTIFY:${posted.json.id} warning \\[kernel\\] k6 boot ok ` +
        `\\[ts:\\d+\\]$`
    )
  );
});

test("empty nick, empty text, and bad rooms are refused with 400", async () => {
  const cases = [
    ["POST", "/rooms/main/messages", { nick: "", text: "x" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "" }],
    ["POST", "/rooms/main/messages", { nick: "pa\nx", text: "x" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "two\nlines" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "x".repeat(2001) }],
    ["POST", "/rooms/main/notify", { severity: "loud", topic: "t", text: "x" }],
    ["POST", "/rooms/Bad Room/messages", { nick: "pax", text: "x" }],
    ["GET", "/rooms/Bad Room/messages", undefined],
  ];
  for (const [method, route, body] of cases) {
    const res = await call(board.base, method, route, body);
    assert.equal(res.status, 400, `${method} ${route}`);
    assert.ok(res.json && typeof res.json.error === "string");
  }
});

test("viewer is served at / and is the Board page", async () => {
  const res = await call(board.base, "GET", "/");
  assert.equal(res.status, 200);
  assert.match(res.text, /Meta OS/);
  assert.match(res.text, /Board/);
  assert.match(res.text, /id="composer"/);
});

test("store file persists lines across a restart", async () => {
  const dir = mkdtempSync(path.join(tmpdir(), "board-test-"));
  const storeFile = path.join(dir, "board.jsonl");
  try {
    const first = await boot({ storeFile });
    const health = await call(first.base, "GET", "/health");
    assert.equal(health.json.store, "file");
    await call(first.base, "POST", "/rooms/main/messages", {
      nick: "milo",
      text: "written before the restart",
    });
    await call(first.base, "POST", "/rooms/alerts/notify", {
      severity: "critical",
      topic: "patrol",
      text: "red incident opened",
    });
    first.server.close();

    // The JSONL file itself holds one record per appended line.
    const records = readFileSync(storeFile, "utf8").trim().split("\n");
    assert.equal(records.length, 2);
    for (const record of records) {
      const parsed = JSON.parse(record);
      assert.equal(typeof parsed.room, "string");
      assert.equal(typeof parsed.line, "string");
    }

    const second = await boot({ storeFile });
    const main = await call(second.base, "GET", "/rooms/main/messages?since=-1");
    assert.equal(main.json.total, 1);
    assert.match(
      main.json.messages[0],
      /^milo: written before the restart \[ts:\d+\]$/
    );
    const alerts = await call(
      second.base,
      "GET",
      "/rooms/alerts/messages?since=-1"
    );
    assert.equal(alerts.json.total, 1);
    assert.match(
      alerts.json.messages[0],
      /^board: NOTIFY:ntf-[0-9a-f]{16} critical \[patrol\] red incident opened \[ts:\d+\]$/
    );
    const rooms = await call(second.base, "GET", "/rooms");
    const byName = new Map(rooms.json.rooms.map((r) => [r.room, r.count]));
    assert.equal(byName.get("main"), 1);
    assert.equal(byName.get("alerts"), 1);
    second.server.close();
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
