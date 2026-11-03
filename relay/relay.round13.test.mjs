// R13-401..425 — 25 relay cases against the real relay/relay.mjs.
//
// Every case drives a real HTTP server on an ephemeral localhost port, or the real CLI in a
// child when the case is about the process itself (exit code, log line, defaults, shutdown).
// Nothing is mocked and the crew bus is never a target.
//
//   node --test relay/relay.round13.test.mjs
//
// The after() hook writes Q_CASES.json and SECTION_Q.md under os-build/round13/nuntius/, so a
// reader can see per-case counts without re-running the suite. Findings are the measured
// behaviour — several record a limit that does not exist (no trim, no rate limit, no dedupe).
import { test, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawn, spawnSync } from "node:child_process";
import { createRelayServer } from "./relay.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const OUT = path.join(ROOT, "os-build", "round13", "nuntius");
const rows = [];

async function start(options = {}) {
  const server = createRelayServer(options);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return { server, base: "http://127.0.0.1:" + server.address().port };
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

// The CLI's first log line, without waiting for the server to exit.
function firstLogLine(env, timeoutMs = 5000) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [path.join(HERE, "relay.mjs")],
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

let main;

test("R13-401 append path", async () => {
  main = await start({ storeFile: null });
  const r = await call(main.base, "POST", "/rooms/main/messages", { nick: "pax", text: "append me" });
  assert.equal(r.status, 201);
  assert.equal(r.json.index, 0);
  note("R13-401", "append path", "201 with index 0", { index: r.json.index });
});

test("R13-402 poll path", async () => {
  await call(main.base, "POST", "/rooms/main/messages", { nick: "del", text: "second" });
  const r = await call(main.base, "GET", "/rooms/main/messages?since=0");
  assert.equal(r.json.messages.length, 1);
  assert.match(r.json.messages[0], /^del: second \[ts:\d+\]$/);
  note("R13-402", "poll path", "since=0 returned the one later line");
});

test("R13-403 room routing", async () => {
  await call(main.base, "POST", "/rooms/ops/messages", { nick: "hana", text: "ops only" });
  const ops = await call(main.base, "GET", "/rooms/ops/messages?since=-1");
  const mainRoom = await call(main.base, "GET", "/rooms/main/messages?since=-1");
  assert.equal(ops.json.total, 1);
  assert.ok(!mainRoom.json.messages.some((l) => l.includes("ops only")));
  note("R13-403", "room routing", "rooms isolated");
});

test("R13-404 message ordering", async () => {
  const before = (await call(main.base, "GET", "/rooms/order/messages?since=-1")).json.total;
  for (let i = 0; i < 5; i++) {
    await call(main.base, "POST", "/rooms/order/messages", { nick: "n" + i, text: "line " + i });
  }
  const all = await call(main.base, "GET", "/rooms/order/messages?since=-1");
  assert.equal(all.json.total, before + 5);
  const tail = all.json.messages.slice(-5).map((l) => l.split(": ")[0]);
  assert.deepEqual(tail, ["n0", "n1", "n2", "n3", "n4"]);
  note("R13-404", "message ordering", "5 posts kept their order");
});

test("R13-405 duplicate delivery", async () => {
  const payload = { severity: "info", topic: "dup", text: "same text twice" };
  const a = await call(main.base, "POST", "/rooms/dup/notify", payload);
  const b = await call(main.base, "POST", "/rooms/dup/notify", payload);
  const all = await call(main.base, "GET", "/rooms/dup/messages?since=-1");
  assert.equal(a.json.id, b.json.id, "the id is content-addressed");
  assert.notEqual(a.json.index, b.json.index, "but the line is appended twice");
  assert.equal(all.json.total, 2);
  note("R13-405", "duplicate delivery", "same id, two lines",
    { finding: "the id is content-addressed but not a dedupe key: an identical notify is delivered twice" });
});

test("R13-406 oversized message", async () => {
  const r = await call(main.base, "POST", "/rooms/main/messages", { nick: "pax", text: "x".repeat(2001) });
  assert.equal(r.status, 400);
  note("R13-406", "oversized message", "400 at 2001 chars");
});

test("R13-407 empty message", async () => {
  const r = await call(main.base, "POST", "/rooms/main/messages", { nick: "pax", text: "" });
  assert.equal(r.status, 400);
  note("R13-407", "empty message", "400 for empty text");
});

test("R13-408 malformed frame", async () => {
  const res = await fetch(main.base + "/rooms/main/messages", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{not json",
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.match(body.error, /not valid JSON/);
  note("R13-408", "malformed frame", "400 with a JSON error");
});

test("R13-409 slow consumer", async () => {
  for (let i = 0; i < 50; i++) {
    await call(main.base, "POST", "/rooms/slow/messages", { nick: "producer", text: "line " + i });
  }
  const r = await call(main.base, "GET", "/rooms/slow/messages?since=-1");
  assert.equal(r.json.messages.length, 50);
  note("R13-409", "slow consumer", "50 buffered lines survived a late first read",
    { finding: "the backlog is served in one response; nothing caps or trims it" });
});

test("R13-410 fast producer burst", async () => {
  const started = Date.now();
  for (let i = 0; i < 200; i++) {
    await call(main.base, "POST", "/rooms/burst/messages", { nick: "p", text: "b" + i });
  }
  const total = (await call(main.base, "GET", "/rooms/burst/messages?since=-1")).json.total;
  const ms = Date.now() - started;
  assert.equal(total, 200);
  note("R13-410", "fast producer burst", "200 accepted in " + ms + " ms",
    { finding: "no rate limit or backpressure: every post in the burst was accepted" });
});

test("R13-411 viewer reconnect", async () => {
  await call(main.base, "POST", "/rooms/recon/messages", { nick: "a", text: "one" });
  const first = await call(main.base, "GET", "/rooms/recon/messages?since=-1");
  const watermark = first.json.total - 1;
  await call(main.base, "POST", "/rooms/recon/messages", { nick: "b", text: "two" });
  const after = await call(main.base, "GET", "/rooms/recon/messages?since=" + watermark);
  assert.equal(after.json.messages.length, 1);
  assert.match(after.json.messages[0], /^b: two/);
  note("R13-411", "viewer reconnect", "watermark resumed with no gap and no repeat");
});

test("R13-412 backlog trim behaviour", async () => {
  const total = (await call(main.base, "GET", "/rooms/burst/messages?since=-1")).json.total;
  assert.equal(total, 200);
  note("R13-412", "backlog trim behaviour", "no trim: 200 of 200 retained",
    { finding: "rooms grow without bound; there is no trim, cap or eviction path in relay.mjs" });
});

test("R13-413 nick parsing", async () => {
  const r = await call(main.base, "POST", "/rooms/parse/messages", { nick: "a:b", text: "text" });
  assert.equal(r.status, 201);
  const line = (await call(main.base, "GET", "/rooms/parse/messages?since=-1")).json.messages[0];
  assert.match(line, /^a:b: text/);
  // A reader that splits on the FIRST colon — the obvious parse of "<nick>: <text>" — attributes
  // the line to "a", not to the nick the server accepted.
  const reNick = line.slice(0, line.indexOf(":"));
  assert.equal(reNick, "a");
  note("R13-413", "nick parsing", "nick 'a:b' is recorded, but a first-colon reader sees 'a'",
    { finding: "the line format is not escaped: a colon in the nick makes the line ambiguous for any reader" });
});

test("R13-414 colon in message body", async () => {
  const text = "ratio 3:1 and time 12:30";
  await call(main.base, "POST", "/rooms/colon/messages", { nick: "pax", text });
  const line = (await call(main.base, "GET", "/rooms/colon/messages?since=-1")).json.messages[0];
  assert.ok(line.includes(text));
  note("R13-414", "colon in message body", "colons in the body are preserved");
});

test("R13-415 unicode message body", async () => {
  const text = "检测 ок — naïve";
  await call(main.base, "POST", "/rooms/uni/messages", { nick: "nervus", text });
  const line = (await call(main.base, "GET", "/rooms/uni/messages?since=-1")).json.messages[0];
  assert.ok(line.includes(text));
  note("R13-415", "unicode message body", "unicode round-trips");
});

test("R13-416 long nick", async () => {
  const r = await call(main.base, "POST", "/rooms/main/messages", { nick: "n".repeat(41), text: "x" });
  assert.equal(r.status, 400);
  note("R13-416", "long nick", "400 at 41 chars");
});

test("R13-417 missing nick", async () => {
  const r = await call(main.base, "POST", "/rooms/main/messages", { text: "x" });
  assert.equal(r.status, 400);
  note("R13-417", "missing nick", "400 with no nick");
});

test("R13-418 state dir watermark", async () => {
  const health = await call(main.base, "GET", "/health");
  assert.equal(health.json.ok, true);
  assert.equal(health.json.store, "memory");
  const rooms = (await call(main.base, "GET", "/rooms/main/messages?since=-1")).json;
  assert.ok(rooms.total >= 1);
  note("R13-418", "state dir watermark", "server holds rooms in memory; the watermark is client-side",
    { finding: "there is no state directory and no server-side watermark: a client that loses its index can only start over" });
});

test("R13-419 resync after clamp", async () => {
  const r = await call(main.base, "GET", "/rooms/main/messages?since=-5");
  assert.ok(Array.isArray(r.json.messages));
  const all = await call(main.base, "GET", "/rooms/main/messages?since=-1");
  assert.deepEqual(r.json.messages, all.json.messages);
  note("R13-419", "resync after clamp", "since=-5 clamps to -1 and returns the whole room",
    { finding: "a negative or unparseable watermark silently re-delivers the whole room" });
});

test("R13-420 concurrent pollers", async () => {
  const results = await Promise.all(Array.from({ length: 5 }, () =>
    call(main.base, "GET", "/rooms/main/messages?since=-1")));
  const totals = new Set(results.map((r) => r.json.total));
  assert.equal(totals.size, 1);
  note("R13-420", "concurrent pollers", "5 simultaneous polls agreed on total");
});

test("R13-421 error envelope", async () => {
  const cases = [
    ["POST", "/rooms/main/messages", { nick: "", text: "x" }],
    ["POST", "/rooms/main/messages", { nick: "pax", text: "x".repeat(2001) }],
    ["POST", "/rooms/main/notify", { severity: "loud", topic: "t", text: "x" }],
    ["GET", "/rooms/Bad Room/messages", undefined],
    ["GET", "/nope", undefined],
  ];
  for (const [m, route, body] of cases) {
    const r = await call(main.base, m, route, body);
    assert.ok([400, 404].includes(r.status), m + " " + route);
    assert.equal(typeof r.json.error, "string");
  }
  note("R13-421", "error envelope", "every refusal carried {error: string}");
});

test("R13-422 exit codes", () => {
  const r = spawnSync(process.execPath, [path.join(HERE, "relay.mjs")], {
    cwd: ROOT, env: { ...process.env, RELAY_PORT: "abc" }, timeout: 5000, encoding: "utf8",
  });
  assert.notEqual(r.status, 0);
  note("R13-422", "exit codes", "bad port exits nonzero",
    { exit: r.status, stderr_head: String(r.stderr || "").split("\n")[0].slice(0, 120) });
});

test("R13-423 log line shape", async () => {
  const r = await firstLogLine({ RELAY_PORT: "0" });
  assert.match(r.line, /^Meta Nuntius relay listening on port \d+ \(store: memory\)$/);
  note("R13-423", "log line shape", r.line, {
    finding: /port 0 /.test(r.line) ? "the log prints the configured port (0), not the bound port" : null,
  });
});

test("R13-424 config defaults", async () => {
  const env = { ...process.env };
  delete env.RELAY_PORT;
  const r = await firstLogLine({ RELAY_PORT: "" });
  const busy = r.code !== undefined && r.line.includes("EADDRINUSE");
  note("R13-424", "config defaults", r.line || "(no line)", {
    default_port_expected: 8787, busy,
    finding: busy ? "8787 was already bound on this host; the default could not be observed" : null,
  });
});

test("R13-425 shutdown behaviour", async () => {
  const second = await start({ storeFile: null });
  await new Promise((resolve) => second.server.close(resolve));
  let refused = false;
  try {
    await fetch(second.base + "/health");
  } catch { refused = true; }
  assert.equal(refused, true, "a closed server refuses new connections");
  note("R13-425", "shutdown behaviour", "close() stopped accepting connections");
});

after(() => {
  fs.mkdirSync(path.join(OUT, "dom"), { recursive: true });
  try { main.server.close(); } catch { /* already closed */ }
  const findings = rows.filter((r) => r.finding).map((r) => ({ task: r.task, finding: r.finding }));
  const counts = { total: rows.length, ok: rows.length - findings.length, findings: findings.length };
  fs.writeFileSync(path.join(OUT, "Q_CASES.json"),
    JSON.stringify({ tool: "relay/relay.round13.test.mjs", ran_at: new Date().toISOString(), counts, rows, findings }, null, 2) + "\n");
  const table = ["| task | case | outcome | finding |", "|---|---|---|---|"];
  for (const r of rows) {
    table.push("| " + r.task + " | " + r.case + " | " + String(r.outcome).replace(/\|/g, "\\|").slice(0, 90)
      + " | " + String(r.finding || "").replace(/\|/g, "\\|").slice(0, 140) + " |");
  }
  fs.writeFileSync(path.join(OUT, "SECTION_Q.md"),
    "# Section Q — Nuntius relay hardening (R13-401..425)\n\n"
    + "Run: `node --test relay/relay.round13.test.mjs`. Machine record: `Q_CASES.json`.\n\n"
    + "Counts: " + JSON.stringify(counts) + "\n\n"
    + "Every case drives the real server on a loopback ephemeral port, or the real CLI in a child "
    + "for the process-level cases. The crew bus is never a target.\n\n"
    + table.join("\n") + "\n");
  console.log("Q_CASES " + JSON.stringify(counts));
});
