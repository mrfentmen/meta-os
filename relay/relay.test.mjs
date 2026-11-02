// Standalone tests for the Meta Nuntius relay (relay/relay.mjs).
//
// Run: node --test relay/relay.test.mjs
//
// Offline: every server binds an ephemeral localhost port, and the
// file-store test uses a temp directory. The repo's npm test script
// enumerates its files in package.json and does not list this file
// yet (see relay/README.md) — this suite is run directly.

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, describe, test } from "node:test";

import {
  createRelayServer,
  formatMessage,
  MAX_BODY_BYTES,
  MAX_NICK_CHARS,
  MAX_READ_LIMIT,
  MAX_ROOM_LINES,
  MAX_TEXT_CHARS,
  MIN_RETAINED_LINES,
  parseMessageLine,
  ROOM_RE,
  trimLines,
  validateMessage,
} from "./relay.mjs";

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

const EDGE = JSON.parse(
  readFileSync(new URL("./protocol-edge.json", import.meta.url), "utf8")
);

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

test("posting creates a room once and GET /rooms lists it once", async () => {
  const created = await req(main.base, "POST", "/rooms/created-room/messages", {
    nick: "pax",
    text: "first in a new room",
  });
  assert.equal(created.status, 201);

  const list = await req(main.base, "GET", "/rooms");
  assert.equal(list.status, 200);
  const matches = list.json.rooms.filter((r) => r.room === "created-room");
  assert.equal(matches.length, 1);
  assert.equal(matches[0].count, 1);
});

test("oversized body is refused with the cap in the error", async () => {
  const res = await req(main.base, "POST", "/rooms/main/messages", {
    nick: "pax",
    text: "x".repeat(EDGE.oversizedTextChars),
  });
  assert.equal(res.status, 400);
  assert.match(res.json.error, new RegExp(String(MAX_BODY_BYTES)));
});

test("concurrent writers never interleave a line", async () => {
  const posts = [];
  for (let i = 0; i < 20; i += 1) {
    posts.push(
      req(main.base, "POST", "/rooms/concurrent/messages", {
        nick: `w${i}`,
        text: `line${i}`,
      })
    );
  }
  const replies = await Promise.all(posts);
  assert.equal(replies.every((r) => r.status === 201), true);

  const all = await req(
    main.base,
    "GET",
    "/rooms/concurrent/messages?since=-1"
  );
  assert.equal(all.json.total, 20);
  for (const line of all.json.messages) {
    assert.match(line, /^w\d+: line\d+ \[ts:\d+\]$/);
  }
});

test("path characters are not valid room names", () => {
  for (const room of EDGE.invalidRooms) {
    assert.equal(ROOM_RE.test(room), false, room);
  }
});

test("history order survives a restart", async () => {
  const dir = mkdtempSync(path.join(tmpdir(), "nuntius-order-"));
  const storeFile = path.join(dir, "relay.jsonl");
  try {
    const first = await start({ storeFile });
    for (const [nick, text] of [
      ["a", "one"],
      ["b", "two"],
      ["c", "three"],
    ]) {
      await req(first.base, "POST", "/rooms/order/messages", { nick, text });
    }
    first.server.close();

    const second = await start({ storeFile });
    const lines = await req(
      second.base,
      "GET",
      "/rooms/order/messages?since=-1"
    );
    assert.equal(lines.json.total, 3);
    assert.match(lines.json.messages[0], /^a: one \[ts:\d+\]$/);
    assert.match(lines.json.messages[1], /^b: two \[ts:\d+\]$/);
    assert.match(lines.json.messages[2], /^c: three \[ts:\d+\]$/);
    second.server.close();
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
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

describe("protocol edges", () => {
  test("empty message body is refused", async () => {
    const res = await req(main.base, "POST", "/rooms/edge-empty/messages", {});
    assert.equal(res.status, 400);
    assert.match(res.json.error, /nick/);
  });

  test("maximum text length passes, one over is refused", async () => {
    const ok = await req(main.base, "POST", "/rooms/edge-max/messages", {
      nick: "pax",
      text: "x".repeat(MAX_TEXT_CHARS),
    });
    assert.equal(ok.status, 201);
    const bad = await req(main.base, "POST", "/rooms/edge-max/messages", {
      nick: "pax",
      text: "x".repeat(MAX_TEXT_CHARS + 1),
    });
    assert.equal(bad.status, 400);
    assert.match(bad.json.error, new RegExp(String(MAX_TEXT_CHARS)));
  });

  test("nick containing a colon keeps the documented split", async () => {
    const posted = await req(main.base, "POST", "/rooms/edge-colon/messages", {
      nick: "pa:x",
      text: "hello",
    });
    assert.equal(posted.status, 201);
    const lines = await req(
      main.base,
      "GET",
      "/rooms/edge-colon/messages?since=-1"
    );
    const parsed = parseMessageLine(lines.json.messages[0]);
    assert.deepEqual(
      { nick: parsed.nick, text: parsed.text },
      { nick: "pa:x", text: "hello" }
    );
  });

  test("a line with no nick separator is refused by the parser", () => {
    assert.throws(
      () => parseMessageLine("no separator here"),
      /malformed message line/
    );
  });

  test("unicode bodies round-trip unchanged", async () => {
    const text = "lab \u{1f9ea} cafe\u0301";
    const posted = await req(main.base, "POST", "/rooms/edge-unicode/messages", {
      nick: "pax",
      text,
    });
    assert.equal(posted.status, 201);
    const lines = await req(
      main.base,
      "GET",
      "/rooms/edge-unicode/messages?since=-1"
    );
    assert.equal(parseMessageLine(lines.json.messages[0]).text, text);
  });

  test("a newline in the body is refused", async () => {
    const res = await req(main.base, "POST", "/rooms/edge-newline/messages", {
      nick: "pax",
      text: "two\nlines",
    });
    assert.equal(res.status, 400);
  });

  test("five messages read back in post order", async () => {
    const texts = ["one", "two", "three", "four", "five"];
    for (const text of texts) {
      await req(main.base, "POST", "/rooms/edge-order/messages", {
        nick: "pax",
        text,
      });
    }
    const lines = await req(
      main.base,
      "GET",
      "/rooms/edge-order/messages?since=-1"
    );
    assert.deepEqual(
      lines.json.messages.map((line) => parseMessageLine(line).text),
      texts
    );
  });

  test("second poll with the same cursor has no duplicates", async () => {
    for (const text of ["a", "b", "c"]) {
      await req(main.base, "POST", "/rooms/edge-cursor/messages", {
        nick: "pax",
        text,
      });
    }
    const first = await req(
      main.base,
      "GET",
      "/rooms/edge-cursor/messages?since=0"
    );
    const second = await req(
      main.base,
      "GET",
      "/rooms/edge-cursor/messages?since=0"
    );
    assert.deepEqual(first.json.messages, second.json.messages);
    assert.equal(new Set(second.json.messages).size, second.json.messages.length);
  });

  test("cursor beyond the current end returns an empty page", async () => {
    await req(main.base, "POST", "/rooms/edge-beyond/messages", {
      nick: "pax",
      text: "only",
    });
    const res = await req(
      main.base,
      "GET",
      "/rooms/edge-beyond/messages?since=999"
    );
    assert.equal(res.status, 200);
    assert.deepEqual(res.json.messages, []);
  });

  test("negative cursor is refused", async () => {
    const res = await req(
      main.base,
      "GET",
      "/rooms/edge-beyond/messages?since=-5"
    );
    assert.equal(res.status, 400);
    assert.match(res.json.error, /since/);
  });

  test("two concurrent writers lose nothing and keep writer order", async () => {
    async function write(nick, prefix) {
      for (let i = 0; i < 10; i += 1) {
        await req(main.base, "POST", "/rooms/edge-concurrent/messages", {
          nick,
          text: `${prefix}${i}`,
        });
      }
    }
    await Promise.all([write("writer-a", "a"), write("writer-b", "b")]);
    const lines = await req(
      main.base,
      "GET",
      "/rooms/edge-concurrent/messages?since=-1"
    );
    assert.equal(lines.json.total, 20);
    const parsed = lines.json.messages.map(parseMessageLine);
    const aOrder = parsed.filter((m) => m.nick === "writer-a").map((m) => m.text);
    const bOrder = parsed.filter((m) => m.nick === "writer-b").map((m) => m.text);
    assert.deepEqual(aOrder, Array.from({ length: 10 }, (_, i) => `a${i}`));
    assert.deepEqual(bOrder, Array.from({ length: 10 }, (_, i) => `b${i}`));
  });

  test("rooms stay isolated", async () => {
    await req(main.base, "POST", "/rooms/edge-room-a/messages", {
      nick: "pax",
      text: "only in A",
    });
    const b = await req(
      main.base,
      "GET",
      "/rooms/edge-room-b/messages?since=-1"
    );
    assert.deepEqual(b.json.messages, []);
  });

  test("room name with whitespace is refused", async () => {
    const res = await req(main.base, "POST", "/rooms/bad%20room/messages", {
      nick: "pax",
      text: "x",
    });
    assert.equal(res.status, 400);
    assert.match(res.json.error, /room name/);
  });

  test("timestamps are assigned and non-decreasing", async () => {
    for (let i = 0; i < 5; i += 1) {
      await req(main.base, "POST", "/rooms/edge-ts/messages", {
        nick: "pax",
        text: `t${i}`,
      });
    }
    const lines = await req(
      main.base,
      "GET",
      "/rooms/edge-ts/messages?since=-1"
    );
    const stamps = lines.json.messages.map((line) => parseMessageLine(line).ts);
    for (let i = 1; i < stamps.length; i += 1) {
      assert.ok(stamps[i] >= stamps[i - 1]);
    }
  });

  test("malformed JSON frame is refused with a named error", async () => {
    const res = await fetch(main.base + "/rooms/edge-json/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{",
    });
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.match(body.error, /not valid JSON/);
  });

  test("validation helper pins nick and text limits", () => {
    assert.equal(validateMessage({ nick: "a", text: "x" }).ok, true);
    assert.equal(
      validateMessage({ nick: "n".repeat(MAX_NICK_CHARS), text: "x" }).ok,
      true
    );
    assert.equal(
      validateMessage({ nick: "n".repeat(MAX_NICK_CHARS + 1), text: "x" }).ok,
      false
    );
    assert.equal(validateMessage({ nick: "pa\nx", text: "x" }).ok, false);
    assert.equal(validateMessage({ nick: "pax", text: "" }).ok, false);
  });

  test("store trims oldest lines at the cap", async () => {
    const edge = await start({ storeFile: null, maxLinesPerRoom: 12 });
    try {
      for (let i = 0; i < 15; i += 1) {
        await req(edge.base, "POST", "/rooms/trim/messages", {
          nick: "pax",
          text: `m${i}`,
        });
      }
      const lines = await req(edge.base, "GET", "/rooms/trim/messages?since=-1");
      assert.equal(lines.json.total, 12);
      assert.equal(parseMessageLine(lines.json.messages[0]).text, "m3");
      assert.equal(parseMessageLine(lines.json.messages[11]).text, "m14");
    } finally {
      edge.server.close();
    }
  });

  test("trimming never drops below minimum retention", () => {
    const lines = Array.from({ length: 20 }, (_, i) => `line-${i}`);
    assert.equal(trimLines(lines, 5).length, MIN_RETAINED_LINES);
    assert.equal(trimLines(lines, 12).length, 12);
    assert.equal(trimLines(lines, 12)[0], "line-8");
    assert.ok(MAX_ROOM_LINES >= MIN_RETAINED_LINES);
  });

  test("reading an empty room is an empty list, not an error", async () => {
    const res = await req(
      main.base,
      "GET",
      "/rooms/edge-empty-room/messages?since=-1"
    );
    assert.equal(res.status, 200);
    assert.equal(res.json.total, 0);
    assert.deepEqual(res.json.messages, []);
  });

  test("read limit returns the oldest pending messages", async () => {
    for (const text of ["one", "two", "three", "four", "five"]) {
      await req(main.base, "POST", "/rooms/edge-limit/messages", {
        nick: "pax",
        text,
      });
    }
    const limited = await req(
      main.base,
      "GET",
      "/rooms/edge-limit/messages?since=-1&limit=2"
    );
    assert.equal(limited.json.messages.length, 2);
    assert.deepEqual(
      limited.json.messages.map((line) => parseMessageLine(line).text),
      ["one", "two"]
    );
    const zero = await req(
      main.base,
      "GET",
      "/rooms/edge-limit/messages?since=-1&limit=0"
    );
    assert.equal(zero.status, 400);
  });

  test("100 posted messages get unique ids", async () => {
    const posts = [];
    for (let i = 0; i < 100; i += 1) {
      posts.push(
        req(main.base, "POST", "/rooms/edge-ids/messages", {
          nick: "pax",
          text: `id-${i}`,
        })
      );
    }
    const replies = await Promise.all(posts);
    assert.equal(replies.every((r) => r.status === 201), true);
    const ids = replies.map((r) => r.json.id);
    assert.equal(new Set(ids).size, 100);
    assert.ok(ids.every((id) => /^msg-[0-9a-f]{16}$/.test(id)));
  });

  test("relay exports the documented API", async () => {
    const mod = await import("./relay.mjs");
    assert.equal(typeof mod.createRelayServer, "function");
    assert.equal(typeof mod.notifyId, "function");
    assert.equal(typeof mod.validateMessage, "function");
    assert.equal(typeof mod.parseMessageLine, "function");
    assert.equal(typeof mod.formatMessage, "function");
    assert.equal(typeof mod.trimLines, "function");
    assert.ok(mod.ROOM_RE instanceof RegExp);
    for (const name of [
      "MAX_BODY_BYTES",
      "MAX_NICK_CHARS",
      "MAX_TEXT_CHARS",
      "MAX_TOPIC_CHARS",
      "MAX_ROOM_LINES",
      "MIN_RETAINED_LINES",
      "MAX_READ_LIMIT",
    ]) {
      assert.equal(typeof mod[name], "number", name);
    }
    assert.equal(mod.MAX_READ_LIMIT > 0, true);
    assert.equal(mod.formatMessage("pax", "x", 1), "pax: x [ts:1]");
  });
});

// CB2-367: the parsed-message validator. Static imports must be top-level, and
// this file's import block is already written, so the module is loaded here.
const { validateMessageRecord } = await import("../relay/message_validate.mjs");

describe("parsed message validator", () => {
  test("a well-formed message record passes", () => {
    assert.deepEqual(
      validateMessageRecord({ nick: "pax", body: "hello", ts: 1700000000 }),
      []
    );
  });

  test("a missing nick is named", () => {
    assert.deepEqual(validateMessageRecord({ body: "x", ts: 1 }), [
      "nick: missing",
    ]);
  });

  test("a record that is not an object is refused", () => {
    assert.deepEqual(validateMessageRecord("pax: hi [ts:1]"), [
      "message: must be an object",
    ]);
  });

  test("body at the cap passes and one over is refused", () => {
    const atCap = "a".repeat(2000);
    assert.deepEqual(
      validateMessageRecord({ nick: "pax", body: atCap, ts: 1 }),
      []
    );
    const over = validateMessageRecord({
      nick: "pax",
      body: "a".repeat(2001),
      ts: 1,
    });
    assert.equal(over.length, 1);
    assert.match(over[0], /^body: must be a single line of 1-2000 chars$/);
  });

  test("an empty body is refused", () => {
    assert.deepEqual(validateMessageRecord({ nick: "pax", body: "", ts: 1 }), [
      "body: must be a single line of 1-2000 chars",
    ]);
  });

  test("a newline in the body is refused", () => {
    const errors = validateMessageRecord({
      nick: "pax",
      body: "two\nlines",
      ts: 1,
    });
    assert.equal(errors.length, 1);
    assert.match(errors[0], /^body:/);
  });

  test("a nil nick and its text never appear in the error list", () => {
    const secret = "do-not-echo-this";
    const errors = validateMessageRecord({
      nick: "pax",
      body: secret + "\n",
      ts: 1,
    });
    assert.equal(JSON.stringify(errors).includes(secret), false);
  });

  test("timestamps must be non-negative integers", () => {
    assert.deepEqual(
      validateMessageRecord({ nick: "pax", body: "x", ts: -1 }),
      ["ts: must be a non-negative integer of epoch seconds"]
    );
    assert.deepEqual(
      validateMessageRecord({ nick: "pax", body: "x", ts: 1.5 }),
      ["ts: must be a non-negative integer of epoch seconds"]
    );
  });

  test("an extra field is named", () => {
    assert.deepEqual(
      validateMessageRecord({ nick: "pax", body: "x", ts: 1, room: "main" }),
      ["unexpected field: room"]
    );
  });
});
