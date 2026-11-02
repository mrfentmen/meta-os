// Tests for the Meta OS Board service (board/board.mjs).
//
// Run from the worktree root:  node --test board/board.test.mjs
//
// Every server binds an ephemeral localhost port; the persistence test
// uses a temporary directory. Nothing here touches the network beyond
// 127.0.0.1, and nothing is mocked — each test drives the real HTTP
// service end to end.

import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, describe, test } from "node:test";

import {
  createBoardServer,
  EMPTY_BOARD_HTML,
  escapeHtml,
  MAX_NICK_CHARS,
  MAX_TEXT_CHARS,
  messageToNote,
  renderBoard,
  renderPost,
  ROOM_RE,
  sortPosts,
} from "./board.mjs";

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

const EDGE = JSON.parse(
  readFileSync(new URL("../relay/protocol-edge.json", import.meta.url), "utf8")
);

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

test("the shared protocol fixture is refused by the board too", async () => {
  for (const room of EDGE.invalidRooms) {
    assert.equal(ROOM_RE.test(room), false, room);
  }
  for (const body of EDGE.invalidMessages) {
    const res = await call(board.base, "POST", "/rooms/main/messages", body);
    assert.equal(res.status, 400, JSON.stringify(body));
  }
});

test("CB-044 a post with an empty title is refused", async () => {
  const res = await call(board.base, "POST", "/rooms/review/posts", {
    title: "", author: "pax", text: "no title",
  });
  assert.equal(res.status, 400);
  assert.match(res.json.error, /title/);
});

test("CB-046 editing another author's post is refused", async () => {
  const created = await call(board.base, "POST", "/rooms/review/posts", {
    title: "Kernel note", author: "pax", text: "body",
  });
  assert.equal(created.status, 201);
  const id = created.json.post.id;

  const other = await call(board.base, "PATCH", `/rooms/review/posts/${id}`, {
    author: "milo", title: "hijacked",
  });
  assert.equal(other.status, 403);

  const owner = await call(board.base, "PATCH", `/rooms/review/posts/${id}`, {
    author: "pax", title: "edited",
  });
  assert.equal(owner.status, 200);
  assert.equal(owner.json.post.title, "edited");
});

test("CB-048 deleting a post leaves a tombstone", async () => {
  const created = await call(board.base, "POST", "/rooms/review/posts", {
    title: "Tombstone note", author: "pax", text: "body",
  });
  const id = created.json.post.id;

  const other = await call(board.base, "DELETE", `/rooms/review/posts/${id}`, {
    author: "milo",
  });
  assert.equal(other.status, 403);

  const deleted = await call(board.base, "DELETE", `/rooms/review/posts/${id}`, {
    author: "pax",
  });
  assert.equal(deleted.status, 200);
  assert.equal(deleted.json.post.deleted, true);

  const list = await call(board.base, "GET", "/rooms/review/posts");
  const row = list.json.posts.find((p) => p.id === id);
  assert.ok(row);
  assert.equal(row.deleted, true);
  assert.equal(row.deleted_by, "pax");
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

async function postNote(base, room, overrides = {}) {
  return call(base, "POST", `/rooms/${room}/posts`, {
    title: "note",
    author: "pax",
    text: "body",
    ...overrides,
  });
}

describe("board store and rendering edges", () => {
  test("empty title is refused", async () => {
    const res = await postNote(board.base, "edge-title", { title: "" });
    assert.equal(res.status, 400);
    assert.match(res.json.error, /title/);
  });

  test("maximum body length passes, one over is refused", async () => {
    const ok = await postNote(board.base, "edge-body", {
      text: "x".repeat(MAX_TEXT_CHARS),
    });
    assert.equal(ok.status, 201);
    const bad = await postNote(board.base, "edge-body", {
      text: "x".repeat(MAX_TEXT_CHARS + 1),
    });
    assert.equal(bad.status, 400);
  });

  test("three notes list oldest-first", async () => {
    for (const title of ["first", "second", "third"]) {
      await postNote(board.base, "edge-order", { title });
    }
    const list = await call(board.base, "GET", "/rooms/edge-order/posts");
    assert.deepEqual(
      list.json.posts.map((p) => p.title),
      ["first", "second", "third"]
    );
  });

  test("a note survives a store round-trip", async () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-roundtrip-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      const first = await boot({ storeFile });
      const created = await postNote(first.base, "persist", {
        title: "kept", author: "pax", text: "round trip",
      });
      first.server.close();
      const second = await boot({ storeFile });
      const list = await call(second.base, "GET", "/rooms/persist/posts");
      assert.equal(list.json.total, 1);
      assert.deepEqual(list.json.posts[0], created.json.post);
      second.server.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("corrupted store file raises the named error", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-corrupt-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      writeFileSync(storeFile, '{"room":"main","line":"pax: ok [ts:1]"}\n{"room":"ma');
      assert.throws(
        () => createBoardServer({ storeFile }),
        /board store corrupted/
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("valid JSON with the wrong store shape is refused", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-shape-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      writeFileSync(storeFile, '{"room":"main","line":123}\n');
      assert.throws(
        () => createBoardServer({ storeFile }),
        /board store corrupted/
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("two concurrent notes both survive a reload", async () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-concurrent-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      const first = await boot({ storeFile });
      await Promise.all([
        postNote(first.base, "race", { title: "one" }),
        postNote(first.base, "race", { title: "two" }),
      ]);
      first.server.close();
      const second = await boot({ storeFile });
      const list = await call(second.base, "GET", "/rooms/race/posts");
      assert.equal(list.json.total, 2);
      assert.deepEqual(list.json.posts.map((p) => p.title).sort(), ["one", "two"]);
      second.server.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("50 posted notes have unique ids", async () => {
    const replies = await Promise.all(
      Array.from({ length: 50 }, (_, i) =>
        postNote(board.base, "edge-ids", { title: `note-${i}` })
      )
    );
    assert.equal(replies.every((r) => r.status === 201), true);
    assert.equal(new Set(replies.map((r) => r.json.post.id)).size, 50);
  });

  test("body HTML is escaped by the renderer", () => {
    const html = renderPost({
      id: "p1", title: "T", author: "pax", text: "<b>bold</b>",
    });
    assert.match(html, /&lt;b&gt;bold&lt;\/b&gt;/);
    assert.ok(!html.includes("<b>bold</b>"));
  });

  test("script tag in a title is escaped exactly", () => {
    const html = renderPost({
      id: "p2", title: "<script>alert(1)</script>", author: "pax", text: "x",
    });
    assert.equal(
      html,
      '<article class="post" data-id="p2"><header><h3>&lt;script&gt;alert(1)&lt;/script&gt;</h3><span class="author">pax</span></header><p>x</p></article>'
    );
  });

  test("plain note markup is exact", () => {
    assert.equal(
      renderPost({ id: "post-1", title: "Hello", author: "pax", text: "Body" }),
      '<article class="post" data-id="post-1"><header><h3>Hello</h3><span class="author">pax</span></header><p>Body</p></article>'
    );
  });

  test("empty board markup is exact", () => {
    assert.equal(renderBoard([]), EMPTY_BOARD_HTML);
  });

  test("timestamps exist and equal-time sort is stable", () => {
    return (async () => {
      const created = await postNote(board.base, "edge-ts", { title: "stamped" });
      assert.equal(typeof created.json.post.ts, "number");
      const rows = [
        { id: "a", ts: 5 }, { id: "b", ts: 5 }, { id: "c", ts: 4 },
      ];
      assert.deepEqual(sortPosts(rows).map((p) => p.id), ["c", "a", "b"]);
    })();
  });

  test("deleting a note leaves a tombstone after reload", async () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-delete-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      const first = await boot({ storeFile });
      const one = await postNote(first.base, "del", { title: "one" });
      await postNote(first.base, "del", { title: "two" });
      const deleted = await call(
        first.base,
        "DELETE",
        `/rooms/del/posts/${one.json.post.id}`,
        { author: "pax" }
      );
      assert.equal(deleted.status, 200);
      first.server.close();
      const second = await boot({ storeFile });
      const list = await call(second.base, "GET", "/rooms/del/posts");
      const row = list.json.posts.find((p) => p.id === one.json.post.id);
      assert.equal(row.deleted, true);
      assert.equal(list.json.posts.find((p) => p.title === "two").deleted, false);
      second.server.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("editing preserves id and original timestamp", async () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-edit-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      const first = await boot({ storeFile });
      const one = await postNote(first.base, "edit", {
        title: "before", text: "old body",
      });
      const edited = await call(
        first.base,
        "PATCH",
        `/rooms/edit/posts/${one.json.post.id}`,
        { author: "pax", title: "after", text: "new body" }
      );
      assert.equal(edited.status, 200);
      assert.equal(edited.json.post.id, one.json.post.id);
      assert.equal(edited.json.post.ts, one.json.post.ts);
      first.server.close();
      const second = await boot({ storeFile });
      const list = await call(second.base, "GET", "/rooms/edit/posts");
      assert.equal(list.json.posts[0].title, "after");
      assert.equal(list.json.posts[0].id, one.json.post.id);
      second.server.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("unicode note survives a store round-trip", async () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-unicode-"));
    const storeFile = path.join(dir, "board.jsonl");
    const text = "lab \u{1f9ea} cafe\u0301";
    try {
      const first = await boot({ storeFile });
      await postNote(first.base, "uni", { title: "unicode", text });
      first.server.close();
      const second = await boot({ storeFile });
      const list = await call(second.base, "GET", "/rooms/uni/posts");
      assert.equal(list.json.posts[0].text, text);
      second.server.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("posting to a fresh temp path creates the store file", async () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-create-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      const first = await boot({ storeFile });
      await postNote(first.base, "create", { title: "created" });
      first.server.close();
      assert.equal(existsSync(storeFile), true);
      const records = readFileSync(storeFile, "utf8").trim().split("\n");
      const parsed = JSON.parse(records[0]);
      assert.equal(parsed.room, "create");
      assert.equal(typeof parsed.post.id, "string");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("a store path that is a directory is refused by name", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-dir-"));
    try {
      assert.throws(
        () => createBoardServer({ storeFile: dir }),
        /board store path is a directory/
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("note without an author is refused", async () => {
    const res = await postNote(board.base, "edge-author", { author: "" });
    assert.equal(res.status, 400);
    assert.match(res.json.error, /author/);
  });

  test("author at the cap passes, one over is refused", async () => {
    const ok = await postNote(board.base, "edge-author-cap", {
      author: "a".repeat(MAX_NICK_CHARS),
    });
    assert.equal(ok.status, 201);
    const bad = await postNote(board.base, "edge-author-cap", {
      author: "a".repeat(MAX_NICK_CHARS + 1),
    });
    assert.equal(bad.status, 400);
  });

  test("post listing limit returns the oldest two of five", async () => {
    for (const title of ["1", "2", "3", "4", "5"]) {
      await postNote(board.base, "edge-limit", { title });
    }
    const limited = await call(
      board.base,
      "GET",
      "/rooms/edge-limit/posts?limit=2"
    );
    assert.equal(limited.json.posts.length, 2);
    assert.deepEqual(limited.json.posts.map((p) => p.title), ["1", "2"]);
  });

  test("relay message adapter uses the nick as author", () => {
    const note = messageToNote("pax: hello from relay [ts:123]", "ops");
    assert.equal(note.author, "pax");
    assert.equal(note.text, "hello from relay");
    assert.equal(note.ts, 123);
    assert.match(note.id, /^note-[0-9a-f]{16}$/);
  });

  test("duplicate submissions create two notes without idempotency", async () => {
    const one = await postNote(board.base, "edge-dup", { title: "same" });
    const two = await postNote(board.base, "edge-dup", { title: "same" });
    assert.equal(one.status, 201);
    assert.equal(two.status, 201);
    assert.notEqual(one.json.post.id, two.json.post.id);
    const list = await call(board.base, "GET", "/rooms/edge-dup/posts");
    assert.equal(list.json.total, 2);
  });

  test("partial store tail raises, never returns partial notes", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "board-partial-"));
    const storeFile = path.join(dir, "board.jsonl");
    try {
      const good = JSON.stringify({
        room: "main",
        post: { id: "p1", room: "main", title: "kept", author: "pax", text: "", ts: 1, deleted: false },
      });
      writeFileSync(storeFile, good + "\n{\"room\":\"main\",\"post\":");
      assert.throws(
        () => createBoardServer({ storeFile }),
        /board store corrupted/
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("board exports the documented API", async () => {
    const mod = await import("./board.mjs");
    assert.equal(typeof mod.createBoardServer, "function");
    assert.equal(typeof mod.notifyId, "function");
    assert.equal(typeof mod.escapeHtml, "function");
    assert.equal(typeof mod.renderPost, "function");
    assert.equal(typeof mod.renderBoard, "function");
    assert.equal(typeof mod.sortPosts, "function");
    assert.equal(typeof mod.messageToNote, "function");
    assert.ok(mod.ROOM_RE instanceof RegExp);
    assert.equal(typeof mod.EMPTY_BOARD_HTML, "string");
    assert.equal(escapeHtml('<a href="x">&'), "&lt;a href=&quot;x&quot;&gt;&amp;");
  });
});
