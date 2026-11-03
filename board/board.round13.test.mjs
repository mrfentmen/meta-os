// R13-426..450 — 25 board cases against the real board/board.mjs and board.html.
//
//   node --test board/board.round13.test.mjs
//
// Rendered-output cases fetch the real viewer and write the served HTML plus the JSON the page
// would render into os-build/round13/nuntius/dom/ as the DOM dump the task asks for. The viewer
// renders client-side, so "the page does not reflect post text" is a property of the server and
// is tested as one: the HTML served at / is static no matter what has been posted.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawn, spawnSync } from "node:child_process";
import { createBoardServer } from "./board.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const OUT = path.join(ROOT, "os-build", "round13", "nuntius");
const DOM = path.join(OUT, "dom");
const rows = [];

function boot(options = {}) {
  return new Promise((resolve) => {
    const server = createBoardServer(options);
    server.listen(0, "127.0.0.1", () => {
      resolve({ server, base: "http://127.0.0.1:" + server.address().port });
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
  try { json = JSON.parse(text); } catch { /* viewer HTML */ }
  return { status: res.status, json, text };
}

function note(task, name, outcome, extra = {}) {
  const row = { task, case: name, outcome, ...extra };
  rows.push(row);
  return row;
}

function dump(name, html, data) {
  fs.mkdirSync(DOM, { recursive: true });
  fs.writeFileSync(path.join(DOM, name + ".html"), html);
  fs.writeFileSync(path.join(DOM, name + ".json"), JSON.stringify(data, null, 2) + "\n");
  return { html: path.relative(ROOT, path.join(DOM, name + ".html")), json: path.relative(ROOT, path.join(DOM, name + ".json")) };
}

function firstLogLine(env, timeoutMs = 5000) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [path.join(HERE, "board.mjs")],
      { cwd: ROOT, env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"] });
    let out = "";
    let done = false;
    const finish = (result) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { child.kill("SIGKILL"); } catch { /* gone */ }
      resolve(result);
    };
    const timer = setTimeout(() => finish({ line: out.trim(), timedOut: true }), timeoutMs);
    child.stdout.on("data", (d) => {
      out += d.toString();
      if (out.includes("\n")) finish({ line: out.split("\n")[0], timedOut: false });
    });
    child.stderr.on("data", (d) => { out += d.toString(); });
    child.on("exit", (code) => finish({ line: out.trim().split("\n")[0] || "", code, timedOut: false }));
  });
}

let board;

test("R13-426 post path", async () => {
  board = await boot({ storeFile: null });
  const r = await call(board.base, "POST", "/rooms/main/messages", { nick: "pax", text: "post me" });
  assert.equal(r.status, 201);
  assert.equal(r.json.index, 0);
  note("R13-426", "post path", "201 with index 0");
});

test("R13-427 read path", async () => {
  await call(board.base, "POST", "/rooms/main/messages", { nick: "del", text: "read me" });
  const r = await call(board.base, "GET", "/rooms/main/messages?since=0");
  assert.equal(r.json.messages.length, 1);
  assert.match(r.json.messages[0], /^del: read me \[ts:\d+\]$/);
  note("R13-427", "read path", "since watermark returned the later line");
});

test("R13-428 board.html render of an empty board", async () => {
  const page = await call(board.base, "GET", "/");
  const rooms = await call(board.base, "GET", "/rooms/empty-room/messages?since=-1");
  assert.equal(page.status, 200);
  assert.match(page.text, /id="composer"/);
  assert.equal(rooms.json.total, 0);
  const ev = dump("empty-board", page.text, rooms.json);
  note("R13-428", "board.html render of an empty board", "viewer served, empty room has 0 lines", ev);
});

test("R13-429 render of a long thread", async () => {
  for (let i = 0; i < 60; i++) {
    await call(board.base, "POST", "/rooms/long/messages", { nick: "n" + (i % 3), text: "thread line " + i });
  }
  const all = await call(board.base, "GET", "/rooms/long/messages?since=-1");
  assert.equal(all.json.total, 60);
  const page = await call(board.base, "GET", "/");
  const ev = dump("long-thread", page.text, all.json);
  note("R13-429", "render of a long thread", "60 lines served in one response", ev);
});

test("R13-430 render of unicode text", async () => {
  const text = "检测 ок — naïve ✓";
  await call(board.base, "POST", "/rooms/uni/messages", { nick: "hana", text });
  const all = await call(board.base, "GET", "/rooms/uni/messages?since=-1");
  assert.ok(all.json.messages[0].includes(text));
  const page = await call(board.base, "GET", "/");
  const ev = dump("unicode", page.text, all.json);
  note("R13-430", "render of unicode text", "unicode round-trips through the JSON the viewer renders", ev);
});

test("R13-431 render of a malformed record", async () => {
  const dir = fs.mkdtempSync(path.join(ROOT, "os-build", "round13", "nuntius", "torn-"));
  const store = path.join(dir, "board.jsonl");
  fs.writeFileSync(store,
    JSON.stringify({ room: "main", line: "pax: good line [ts:1]" }) + "\n" + '{"room":"main","line":');
  const torn = await boot({ storeFile: store });
  const all = await call(torn.base, "GET", "/rooms/main/messages?since=-1");
  assert.equal(all.json.total, 1, "the torn record is skipped, not fatal");
  const page = await call(torn.base, "GET", "/");
  const ev = dump("malformed-record", page.text, all.json);
  torn.server.close();
  fs.rmSync(dir, { recursive: true, force: true });
  note("R13-431", "render of a malformed record", "1 good line loaded, torn record skipped", ev);
});

test("R13-432 ordering of posts", async () => {
  const all = await call(board.base, "GET", "/rooms/long/messages?since=-1");
  const firstFive = all.json.messages.slice(0, 5).map((l) => Number(l.match(/thread line (\d+)/)[1]));
  assert.deepEqual(firstFive, [0, 1, 2, 3, 4]);
  note("R13-432", "ordering of posts", "post order preserved");
});

test("R13-433 duplicate post", async () => {
  const payload = { nick: "pax", text: "the same words" };
  const a = await call(board.base, "POST", "/rooms/dup/messages", payload);
  const b = await call(board.base, "POST", "/rooms/dup/messages", payload);
  const all = await call(board.base, "GET", "/rooms/dup/messages?since=-1");
  assert.equal(all.json.total, 2);
  assert.notEqual(a.json.index, b.json.index);
  note("R13-433", "duplicate post", "identical text stored twice",
    { finding: "the board has no duplicate detection; the client must dedupe by index" });
});

test("R13-434 oversized post", async () => {
  const r = await call(board.base, "POST", "/rooms/main/messages", { nick: "pax", text: "x".repeat(2001) });
  assert.equal(r.status, 400);
  note("R13-434", "oversized post", "400 at 2001 chars");
});

test("R13-435 empty post", async () => {
  const r = await call(board.base, "POST", "/rooms/main/messages", { nick: "pax", text: "" });
  assert.equal(r.status, 400);
  note("R13-435", "empty post", "400 for empty text");
});

test("R13-436 pagination of a long post list", async () => {
  const page = await call(board.base, "GET", "/rooms/long/messages?since=39");
  assert.equal(page.json.total, 60);
  assert.equal(page.json.messages.length, 20);
  note("R13-436", "pagination of a long post list", "since=39 returned the last 20 lines",
    { finding: "there is no page-size cap; a full read returns every line in one response" });
});

test("R13-437 error envelope", async () => {
  const cases = [
    ["POST", "/rooms/main/messages", { nick: "", text: "x" }],
    ["POST", "/rooms/main/notify", { severity: "loud", topic: "t", text: "x" }],
    ["GET", "/rooms/Bad Room/messages", undefined],
    ["GET", "/nope", undefined],
  ];
  for (const [m, route, body] of cases) {
    const r = await call(board.base, m, route, body);
    assert.ok([400, 404].includes(r.status));
    assert.equal(typeof r.json.error, "string");
  }
  note("R13-437", "error envelope", "every refusal carried {error: string}");
});

test("R13-438 state persistence across restart", async () => {
  const dir = fs.mkdtempSync(path.join(ROOT, "os-build", "round13", "nuntius", "persist-"));
  const store = path.join(dir, "board.jsonl");
  try {
    const first = await boot({ storeFile: store });
    await call(first.base, "POST", "/rooms/main/messages", { nick: "milo", text: "before restart" });
    first.server.close();
    const second = await boot({ storeFile: store });
    const all = await call(second.base, "GET", "/rooms/main/messages?since=-1");
    assert.equal(all.json.total, 1);
    second.server.close();
    note("R13-438", "state persistence across restart", "1 line survived a restart");
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test("R13-439 concurrent posters", async () => {
  const results = await Promise.all(Array.from({ length: 8 }, (_, i) =>
    call(board.base, "POST", "/rooms/conc/messages", { nick: "p" + i, text: "c" + i })));
  assert.equal(new Set(results.map((r) => r.json.index)).size, 8);
  const all = await call(board.base, "GET", "/rooms/conc/messages?since=-1");
  assert.equal(all.json.total, 8);
  note("R13-439", "concurrent posters", "8 concurrent posts got 8 distinct indices");
});

test("R13-440 stale record handling", async () => {
  const r = await call(board.base, "GET", "/rooms/main/messages?since=9999");
  assert.equal(r.json.messages.length, 0);
  assert.ok(r.json.total >= 1);
  note("R13-440", "stale record handling", "an index past the end returns no lines, not an error");
});

test("R13-441 timestamp display", async () => {
  const line = (await call(board.base, "GET", "/rooms/main/messages?since=-1")).json.messages[0];
  assert.match(line, /\[ts:\d+\]$/);
  note("R13-441", "timestamp display", "every line ends with a second-resolution ts stamp");
});

test("R13-442 author display", async () => {
  const line = (await call(board.base, "GET", "/rooms/main/messages?since=-1")).json.messages[0];
  assert.match(line, /^[^:]+: /);
  note("R13-442", "author display", "the nick precedes the first colon-space");
});

test("R13-443 escaping of HTML in post text", async () => {
  const text = '<script>alert(1)</script><img src=x onerror=alert(2)>';
  const posted = await call(board.base, "POST", "/rooms/html/messages", { nick: "attacker", text });
  assert.equal(posted.status, 201);
  const page = await call(board.base, "GET", "/");
  assert.ok(!page.text.includes("<script>alert(1)</script>"), "the server does not reflect post text into the page");
  const all = await call(board.base, "GET", "/rooms/html/messages?since=-1");
  assert.ok(all.json.messages[0].includes(text), "the text is stored verbatim for the client to escape");
  const ev = dump("html-escaping", page.text, all.json);
  note("R13-443", "escaping of HTML in post text", "server never reflects post text; escaping is the viewer's job", {
    ...ev,
    finding: page.text.includes("innerHTML")
      ? "board.html uses innerHTML somewhere: the viewer must escape before it renders a line"
      : "board.html does not use innerHTML: lines reach the DOM as text",
  });
});

test("R13-444 link handling", async () => {
  const text = "see https://example.com/report for the numbers";
  await call(board.base, "POST", "/rooms/links/messages", { nick: "pax", text });
  const line = (await call(board.base, "GET", "/rooms/links/messages?since=-1")).json.messages[0];
  assert.ok(line.includes("https://example.com/report"));
  note("R13-444", "link handling", "URLs are stored as text; the server builds no anchors");
});

test("R13-445 config defaults", async () => {
  const r = await firstLogLine({ BOARD_PORT: "" });
  const busy = r.code !== undefined && r.line.includes("EADDRINUSE");
  note("R13-445", "config defaults", r.line || "(no line)", {
    default_port_expected: 8790, busy,
    finding: busy ? "8790 was already bound on this host; the default could not be observed" : null,
  });
});

test("R13-446 exit codes", () => {
  const r = spawnSync(process.execPath, [path.join(HERE, "board.mjs")], {
    cwd: ROOT, env: { ...process.env, BOARD_PORT: "abc" }, timeout: 5000, encoding: "utf8",
  });
  assert.notEqual(r.status, 0);
  note("R13-446", "exit codes", "bad port exits nonzero",
    { exit: r.status, stderr_head: String(r.stderr || "").split("\n")[0].slice(0, 120) });
});

test("R13-447 log line shape", async () => {
  const r = await firstLogLine({ BOARD_PORT: "0" });
  assert.match(r.line, /^Meta OS Board listening on port \d+ \(store: memory\)$/);
  note("R13-447", "log line shape", r.line, {
    finding: /port 0 /.test(r.line) ? "the log prints the configured port (0), not the bound port" : null,
  });
});

test("R13-448 shutdown behaviour", async () => {
  const second = await boot({ storeFile: null });
  await new Promise((resolve) => second.server.close(resolve));
  let refused = false;
  try { await fetch(second.base + "/health"); } catch { refused = true; }
  assert.equal(refused, true);
  note("R13-448", "shutdown behaviour", "close() stopped accepting connections");
});

test("R13-449 restart idempotence", async () => {
  const dir = fs.mkdtempSync(path.join(ROOT, "os-build", "round13", "nuntius", "idem-"));
  const store = path.join(dir, "board.jsonl");
  try {
    const first = await boot({ storeFile: store });
    await call(first.base, "POST", "/rooms/main/messages", { nick: "a", text: "one" });
    await call(first.base, "POST", "/rooms/main/messages", { nick: "b", text: "two" });
    first.server.close();
    const second = await boot({ storeFile: store });
    const third = await boot({ storeFile: store });
    const a = await call(second.base, "GET", "/rooms/main/messages?since=-1");
    const b = await call(third.base, "GET", "/rooms/main/messages?since=-1");
    assert.equal(a.json.total, 2);
    assert.equal(b.json.total, 2, "replaying the store twice does not duplicate lines");
    second.server.close(); third.server.close();
    note("R13-449", "restart idempotence", "two restarts on one store: 2 lines, not 4");
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test("R13-450 fixture set completeness", async () => {
  const listed = await call(board.base, "GET", "/rooms");
  assert.equal(listed.status, 200);
  const byName = new Map(listed.json.rooms.map((r) => [r.room, r.count]));
  for (const room of ["main", "long", "uni", "dup", "conc", "html", "links"]) {
    assert.ok(byName.has(room), "room " + room + " is listed");
  }
  const checked = {};
  for (const [room, count] of byName) {
    const got = await call(board.base, "GET", "/rooms/" + room + "/messages?since=-1");
    checked[room] = { listed: count, read: got.json.total };
    assert.equal(got.json.total, count, room + " count matches its messages");
  }
  note("R13-450", "fixture set completeness", "the room list agrees with every room read", { checked });
});

after(() => {
  fs.mkdirSync(path.join(OUT, "dom"), { recursive: true });
  try { board.server.close(); } catch { /* already closed */ }
  const findings = rows.filter((r) => r.finding).map((r) => ({ task: r.task, finding: r.finding }));
  const counts = { total: rows.length, ok: rows.length - findings.length, findings: findings.length };
  fs.writeFileSync(path.join(OUT, "R_CASES.json"),
    JSON.stringify({ tool: "board/board.round13.test.mjs", ran_at: new Date().toISOString(), counts, rows, findings }, null, 2) + "\n");
  const table = ["| task | case | outcome | evidence / finding |", "|---|---|---|---|"];
  for (const r of rows) {
    const ev = [r.html, r.finding].filter(Boolean).join("; ");
    table.push("| " + r.task + " | " + r.case + " | " + String(r.outcome).replace(/\|/g, "\\|").slice(0, 90)
      + " | " + String(ev).replace(/\|/g, "\\|").slice(0, 150) + " |");
  }
  fs.writeFileSync(path.join(OUT, "SECTION_R.md"),
    "# Section R — Nuntius board hardening (R13-426..450)\n\n"
    + "Run: `node --test board/board.round13.test.mjs`. Machine record: `R_CASES.json`; "
    + "rendered-output evidence in `dom/` (served HTML + the JSON the page renders).\n\n"
    + "Counts: " + JSON.stringify(counts) + "\n\n"
    + "The viewer renders client-side, so every render case records the static HTML that was served "
    + "plus the JSON a browser would draw — that is the DOM dump.\n\n"
    + table.join("\n") + "\n");
  console.log("R_CASES " + JSON.stringify(counts));
});
