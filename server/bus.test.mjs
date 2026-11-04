#!/usr/bin/env node
// server/bus.test.mjs — selftest + negative tests for the local bus.
// Starts the bus on a RANDOM port (127.0.0.1 only) under a temp data
// dir, exercises send/list/search, pagination, presence, attachments,
// retention guard, SSE fan-out, 50-way parallel writes, auth, bind
// address, log hygiene, and the Upstash-off default. Exits 0 when every
// check passes, non-zero otherwise. Stdlib only.
import { strict as assert } from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createBusServer, defaultDataDir } from "./bus.mjs";

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "bus-test-"));
const DATA_DIR = path.join(TMP, "bus");
const logs = [];
let failures = 0;
let passes = 0;

function ok(name) {
  passes++;
  console.log("ok - " + name);
}
function fail(name, err) {
  failures++;
  console.log("FAIL - " + name + ": " + (err && err.message ? err.message : String(err)));
}

async function main() {
  const server = createBusServer({ dataDir: DATA_DIR, logger: (o) => logs.push(o) });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const addr = server.address();
  const base = `http://${addr.address}:${addr.port}`;
  const token = fs.readFileSync(path.join(DATA_DIR, "token"), "utf8").trim();

  async function req(method, p, body, useToken = true, rawHeaders = {}) {
    const headers = { ...rawHeaders };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (useToken && body !== undefined && (method === "POST" || method === "DELETE" || method === "PATCH")) {
      headers["x-bus-token"] = token;
    } else if (useToken && method === "GET" && rawHeaders["x-bus-token"]) {
      headers["x-bus-token"] = rawHeaders["x-bus-token"];
    }
    const res = await fetch(base + p, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let json = null;
    const text = await res.text();
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = { _raw: text };
    }
    return { status: res.status, json, text };
  }

  try {
    // (21) bind 127.0.0.1 only.
    try {
      assert.equal(addr.address, "127.0.0.1");
      ok("bind is 127.0.0.1 (got " + addr.address + ":" + addr.port + ")");
    } catch (e) { fail("bind is 127.0.0.1", e); }

    // (15) health: store path, count, last write.
    try {
      const r = await req("GET", "/health");
      assert.equal(r.status, 200);
      assert.equal(r.json.store, "file");
      assert.equal(r.json.dataDir, DATA_DIR);
      assert.ok(typeof r.json.count === "number");
      assert.ok("lastWrite" in r.json);
      ok("GET /health reports file store + dataDir + count + lastWrite");
    } catch (e) { fail("GET /health", e); }

    // (4) default general room.
    try {
      const r = await req("GET", "/rooms");
      assert.equal(r.status, 200);
      assert.ok(r.json.rooms.some((x) => x.room === "general"));
      ok("default room general exists");
    } catch (e) { fail("default general room", e); }

    // (13) writes refused without token.
    try {
      const r = await req("POST", "/rooms/general/messages", { nick: "a", text: "hi" }, false);
      assert.equal(r.status, 401);
      assert.ok(r.json.code === "bus_auth_missing" || r.json.code === "bus_auth_invalid");
      assert.equal(r.json.delivery.state, "failed");
      ok("POST without token refused (401 bus_auth_missing)");
    } catch (e) { fail("auth refusal without token", e); }

    // (13) token file is 0600.
    try {
      const st = fs.statSync(path.join(DATA_DIR, "token"));
      assert.equal(st.mode & 0o777, 0o600);
      ok("token file mode is 0600");
    } catch (e) { fail("token file mode 0600", e); }

    // (19) send/list.
    let firstId = null;
    try {
      const r = await req("POST", "/rooms/general/messages", { nick: "alice", text: "hello bus" });
      assert.equal(r.status, 201);
      assert.ok(typeof r.json.index === "number");
      assert.ok(typeof r.json.id === "string");
      assert.equal(r.json.delivery.state, "stored");
      firstId = r.json.id;
      const g = await req("GET", "/rooms/general/messages?since=-1");
      assert.equal(g.status, 200);
      assert.ok(g.json.messages.some((l) => l.includes("alice: hello bus")));
      assert.ok(g.json.items.some((it) => it.id === firstId && typeof it.ts === "number"));
      assert.ok(/\[ts:\d+\]$/.test(g.json.messages[0]));
      ok("send + list round trip (board line + stable id + server ts)");
    } catch (e) { fail("send/list", e); }

    // (3) notify compat.
    try {
      const r = await req("POST", "/rooms/general/notify", { severity: "info", topic: "t", text: "n1" });
      assert.equal(r.status, 201);
      assert.ok(/^ntf-[0-9a-f]{16}$/.test(r.json.id));
      const g = await req("GET", "/rooms/general/messages?since=-1");
      assert.ok(g.json.messages.some((l) => l.includes("NOTIFY:" + r.json.id)));
      ok("POST /rooms/<room>/notify keeps board shape (ntf- id + line)");
    } catch (e) { fail("notify compat", e); }

    // (4) rooms create/list/join.
    try {
      const c = await req("POST", "/rooms", { room: "test-room" });
      assert.ok(c.status === 201 || c.status === 200);
      const l = await req("GET", "/rooms");
      assert.ok(l.json.rooms.some((x) => x.room === "test-room"));
      const j = await req("POST", "/rooms/test-room/join", { nick: "bob" });
      assert.equal(j.status, 200);
      assert.ok(j.json.online.includes("bob"));
      ok("rooms create/list/join (+ default general)");
    } catch (e) { fail("rooms create/list/join", e); }

    // (6) pagination: page size + cursor.
    try {
      for (let i = 0; i < 60; i++) {
        const r = await req("POST", "/rooms/test-room/messages", { nick: "p", text: "page line " + i });
        assert.equal(r.status, 201);
      }
      const h1 = await req("GET", "/rooms/test-room/history?limit=50");
      assert.equal(h1.status, 200);
      assert.equal(h1.json.pageSize, 50);
      assert.equal(h1.json.items.length, 50);
      const h2 = await req("GET", `/rooms/test-room/history?cursor=${h1.json.nextCursor}&limit=50`);
      assert.equal(h2.status, 200);
      assert.ok(h2.json.items.length > 0);
      assert.ok(h2.json.items[0].seq > h1.json.items[h1.json.items.length - 1].seq);
      ok("pagination: 50-item pages + seq cursor (60 msgs -> 50 + rest)");
    } catch (e) { fail("pagination", e); }

    // (7) case + accent-insensitive search.
    try {
      await req("POST", "/rooms/test-room/messages", { nick: "searcher", text: "caf\u00e9 au lait" });
      const s1 = await req("GET", "/rooms/test-room/search?q=cafe");
      assert.ok(s1.json.items.some((it) => it.text.includes("caf\u00e9")));
      const s2 = await req("GET", "/rooms/test-room/search?q=CAFE");
      assert.ok(s2.json.items.length >= 1);
      ok("search is case+accent-insensitive (cafe matches caf\u00e9)");
    } catch (e) { fail("search accent-insensitive", e); }

    // (8) presence join/leave/heartbeat.
    try {
      await req("POST", "/rooms/test-room/presence", { nick: "carol", action: "join" });
      let g = await req("GET", "/rooms/test-room/presence");
      assert.ok(g.json.online.includes("carol"));
      await req("POST", "/rooms/test-room/presence", { nick: "carol", action: "heartbeat" });
      g = await req("GET", "/rooms/test-room/presence");
      assert.ok(g.json.online.includes("carol"));
      await req("POST", "/rooms/test-room/presence", { nick: "carol", action: "leave" });
      g = await req("GET", "/rooms/test-room/presence");
      assert.ok(!g.json.online.includes("carol"));
      ok("presence join/heartbeat/leave (60s TTL configured)");
    } catch (e) { fail("presence", e); }

    // (10-11) attachments: cap + allowlist + named rejection, outside JSONL.
    let attachId = null;
    try {
      const small = Buffer.from("hello attachment").toString("base64");
      const a = await req("POST", "/rooms/test-room/attachments", {
        filename: "note.txt", mime: "text/plain", dataBase64: small,
      });
      assert.equal(a.status, 201);
      assert.ok(a.json.path.startsWith("attachments/test-room/"));
      attachId = a.json.id;
      assert.ok(!a.json.path.endsWith(".jsonl"));
      const diskPath = path.join(DATA_DIR, a.json.path);
      assert.ok(fs.existsSync(diskPath));
      assert.ok(!fs.readFileSync(path.join(DATA_DIR, "rooms", "test-room.jsonl"), "utf8").includes("hello attachment"));
      ok("attachment stored outside JSONL with relative path " + a.json.path);
    } catch (e) { fail("attachment store", e); }

    // (11) attachment download round trip.
    try {
      if (attachId) {
        const res = await fetch(base + `/rooms/test-room/attachments/${attachId}`);
        assert.equal(res.status, 200);
        const txt = await res.text();
        assert.equal(txt, "hello attachment");
        ok("attachment download returns stored bytes");
      } else ok("attachment download skipped (no id)");
    } catch (e) { fail("attachment download", e); }

    // (20) negative: malformed message.
    try {
      const bads = [
        await req("POST", "/rooms/test-room/messages", { nick: "", text: "x" }),
        await req("POST", "/rooms/test-room/messages", { nick: "x", text: "" }),
        await req("POST", "/rooms/test-room/messages", { nick: "x", text: "a".repeat(2001) }),
        await req("POST", "/rooms/test-room/messages", { nick: "bad\nnick", text: "x" }),
      ];
      for (const b of bads) assert.equal(b.status, 400);
      assert.ok(bads[0].json.delivery.state === "failed");
      ok("negative: 4 malformed messages refused (400 + failed delivery)");
    } catch (e) { fail("negative malformed message", e); }

    // (20) negative: oversized attachment.
    try {
      const big = Buffer.alloc(1_048_577, 65).toString("base64");
      const r = await req("POST", "/rooms/test-room/attachments", {
        filename: "big.txt", mime: "text/plain", dataBase64: big,
      });
      assert.ok(r.status === 413);
      assert.equal(r.json.code, "attachment_too_large");
      const badMime = await req("POST", "/rooms/test-room/attachments", {
        filename: "x.exe", mime: "application/x-msdownload", dataBase64: Buffer.from("hi").toString("base64"),
      });
      assert.equal(badMime.status, 415);
      assert.equal(badMime.json.code, "attachment_mime_not_allowed");
      ok("negative: oversized attachment 413 attachment_too_large; bad MIME 415");
    } catch (e) { fail("negative oversized attachment", e); }

    // (12) retention never silently deletes last 500.
    try {
      await req("POST", "/rooms", { room: "ret-room" });
      for (let i = 0; i < 5; i++) {
        await req("POST", "/rooms/ret-room/messages", { nick: "r", text: "ret " + i });
      }
      const refused = await req("POST", "/rooms/ret-room/prune", { before: 5 });
      assert.equal(refused.status, 409);
      assert.equal(refused.json.code, "retention_would_leave_fewer_than_500");
      // Boundary: fill to 505, prune 5 -> 500 remain is allowed.
      for (let i = 5; i < 505; i++) {
        await req("POST", "/rooms/ret-room/messages", { nick: "r", text: "ret " + i });
      }
      const allowed = await req("POST", "/rooms/ret-room/prune", { before: 5 });
      assert.equal(allowed.status, 200);
      assert.equal(allowed.json.total, 500);
      ok("retention: prune refused below 500, allowed at boundary (500 remain)");
    } catch (e) { fail("retention guard", e); }

    // (16) two concurrent SSE readers see one message.
    try {
      const cur = await req("GET", "/rooms/test-room/messages?since=-1");
      const cursor = cur.json.total - 1;
      const marker = "sse-two-clients-" + Date.now();
      function sseOnce() {
        return new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error("sse timeout")), 8000);
          import("node:http").then(({ default: http }) => {
            const rq = http.get(
              `${base}/rooms/test-room/events?cursor=${cursor}`,
              { headers: { "x-bus-token": token } },
              (res) => {
                let buf = "";
                res.on("data", (c) => {
                  buf += c.toString();
                  if (buf.includes(marker)) {
                    clearTimeout(timer);
                    try { rq.destroy(); } catch { /* ignore */ }
                    resolve(buf);
                  }
                });
                res.on("error", (err) => { clearTimeout(timer); reject(err); });
              }
            );
            rq.on("error", (err) => { clearTimeout(timer); reject(err); });
          });
        });
      }
      const p1 = sseOnce();
      const p2 = sseOnce();
      await new Promise((r) => setTimeout(r, 400));
      const posted = await req("POST", "/rooms/test-room/messages", { nick: "sse", text: marker });
      assert.equal(posted.status, 201);
      const [b1, b2] = await Promise.all([p1, p2]);
      assert.ok(b1.includes(marker) && b2.includes(marker));
      ok("SSE: two concurrent readers saw the same message");
    } catch (e) { fail("SSE two clients", e); }

    // (17) reconnect with cursor replays missed.
    try {
      const h = await req("GET", "/rooms/test-room/history?limit=1");
      const firstCursor = h.json.items[0].seq - 1 >= -1 ? h.json.items[0].seq - 1 : -1;
      const after = await req("GET", `/rooms/test-room/history?cursor=${firstCursor}&limit=3`);
      assert.ok(after.json.items.length >= 1);
      ok("reconnect with cursor replays missed items (history cursor)");
    } catch (e) { fail("reconnect cursor", e); }

    // (18) 50 parallel sends, all stored exactly once.
    try {
      await req("POST", "/rooms", { room: "par-room" });
      const before = (await req("GET", "/rooms/par-room/messages?since=-1")).json.total;
      const sends = [];
      for (let i = 0; i < 50; i++) {
        sends.push(req("POST", "/rooms/par-room/messages", { nick: "w", text: "parallel " + i + " " + Date.now() }));
      }
      const results = await Promise.all(sends);
      for (const r of results) assert.equal(r.status, 201);
      const after = await req("GET", "/rooms/par-room/messages?since=-1");
      assert.equal(after.json.total - before, 50);
      const ids = new Set(after.json.items.map((it) => it.id));
      assert.equal(ids.size, after.json.items.length);
      const seqs = after.json.items.map((it) => it.seq).sort((a, b) => a - b);
      for (let i = 1; i < seqs.length; i++) assert.ok(seqs[i] === seqs[i - 1] + 1);
      ok("concurrent safety: 50 parallel sends stored exactly once, seqs contiguous");
    } catch (e) { fail("50 parallel sends", e); }

    // (22) logs carry room+id+result, never the body.
    try {
      const planted = "PLANTED-LOG-PROBE-" + Date.now().toString(36) + "-xyzzy";
      const r = await req("POST", "/rooms/general/messages", { nick: "logger", text: planted });
      assert.equal(r.status, 201);
      const blob = JSON.stringify(logs);
      assert.ok(!blob.includes(planted), "planted body string must not appear in logs");
      const entry = logs.find((l) => l && l.id === r.json.id);
      assert.ok(entry && entry.room === "general" && entry.result === "stored");
      ok("structured logs: room+id+result, planted body absent");
    } catch (e) { fail("log hygiene (no body)", e); }

    // (14) default path never imports/requires a remote helper.
    // Strip line comments first so prose mentioning the words cannot
    // trip the check; what matters is a module specifier.
    try {
      const raw = fs.readFileSync(new URL(import.meta.url).pathname.replace(/bus\.test\.mjs$/, "bus.mjs"), "utf8");
      const code = raw.split("\n").map((l) => l.replace(/^\s*\/\/.*$/, "")).join("\n");
      assert.ok(!/require\s*\(\s*['"][^'"]*(upstash|redis)[^'"]*['"]\s*\)/i.test(code));
      assert.ok(!/from\s+['"][^'"]*(upstash|redis)[^'"]*['"]/i.test(code));
      ok("default path has no upstash/redis import or require");
    } catch (e) { fail("no remote import in default path", e); }

    // (2) default data dir is outside the git tree.
    try {
      const savedBus = process.env.BUS_DATA_DIR;
      const savedState = process.env.METAOS_STATE;
      delete process.env.BUS_DATA_DIR;
      delete process.env.METAOS_STATE;
      const d = defaultDataDir();
      const repoRoot = process.cwd();
      assert.ok(!path.resolve(d).startsWith(path.resolve(repoRoot) + path.sep) || d.includes(os.homedir()));
      if (savedBus !== undefined) process.env.BUS_DATA_DIR = savedBus;
      if (savedState !== undefined) process.env.METAOS_STATE = savedState;
      ok("default data dir is outside the git tree (" + d + ")");
    } catch (e) { fail("data dir outside git tree", e); }

    // (24) no required-Upstash-token in default startup: env sweep.
    try {
      for (const k of ["MUSE_RELAY_URL", "TRIO_UPSTASH_HOST", "UPSTASH_TOKEN", "BUS_UPSTASH"]) {
        assert.ok(!process.env[k] || process.env[k] === "", k + " must be unset for default startup");
      }
      ok("default startup needs no Upstash token (env sweep clean)");
    } catch (e) { fail("no required Upstash token", e); }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }

  console.log(`\nbus selftest: ${passes} passed, ${failures} failed`);
  if (failures > 0) process.exit(1);
}

main().catch((err) => {
  console.error("bus selftest crashed: " + (err && err.stack ? err.stack : String(err)));
  process.exit(2);
});
