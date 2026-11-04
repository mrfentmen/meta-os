#!/usr/bin/env node
// Meta OS local message bus (R2-T3 Section A).
//
// A LOCAL bus with no third-party dependency: node stdlib only
// (node:http, node:fs, node:crypto, node:path, node:os, node:url).
// There is deliberately NO remote-service import in this file: the
// default path never imports or requires any Upstash/Redis/REST
// helper. The old cloud path (Upstash REST via MUSE_RELAY_URL /
// TRIO_UPSTASH_HOST / RELAY_URL + token file, bus.html /lrange/ +
// /rpush/ + /smembers/ + /mget/ shapes, relay_common, trio_store.py
// UpstashStore, trio_agent.py TRIO_RELAY_URL hook) is inventoried in
// os-build/lanes/R2_T3_A.md and is OFF by default (see BUS_UPSTASH
// below). If BUS_UPSTASH=1 is set this process refuses to start so a
// remote dependency can never be silently engaged.
//
// Data directory (ONE documented location, OUTSIDE the git tree):
//   $BUS_DATA_DIR, else $METAOS_STATE/bus, else ~/.local/state/metaos/bus
// On-disk layout (documented, see "On-disk format" in server/README.md):
//   <dataDir>/rooms/<room>.jsonl        one JSON object per line (the log)
//   <dataDir>/attachments/<room>/<id>-<safe-name>  raw attachment bytes
//   <dataDir>/presence.json             snapshot (ephemeral, 60s TTL anyway)
//   <dataDir>/token                     local-only auth token, mode 0600
//   <dataDir>/meta.json                 { created, lastWrite, counts }
// Message record (one JSONL line):
//   { id, seq, room, nick, text, ts, tsMs, kind, severity?, topic?,
//     notifyId?, delivery: { state, reason }, attachments?: [...] }
// Line protocol (board-compatible, for site-chat.js + board.html polls):
//   message : "<nick>: <text> [ts:<epoch-seconds>]"
//   notify  : "board: NOTIFY:<id> <severity> [<topic>] <text> [ts:<epoch>]"
//   notify id: "ntf-" + first 16 hex of sha256(room+"\n"+topic+"\n"+sev+"\n"+text)
//
// Endpoints (board shape kept; extras are additive, reads stay open,
// writes need the local token):
//   GET  /                                   { ok, service, board_compat }
//   GET  /health                             store path, count, last write (task 15)
//   GET  /rooms                              [{ room, count }] (+default general)
//   POST /rooms               { room }       create (task 4)
//   GET  /rooms/<room>/messages?since=<n>&limit=<k>
//        board-compat lines after index n + parallel `items` (tasks 3,5,6)
//   POST /rooms/<room>/messages { nick, text, attachmentIds? } (tasks 5,9,13)
//   POST /rooms/<room>/notify    { severity, topic, text }     (tasks 3,5,9,13)
//   GET  /rooms/<room>/history?cursor=<id|seq>&limit=<k>  paged items (task 6)
//   GET  /rooms/<room>/search?q=<text>&limit=<k>  accent-insensitive (task 7)
//   GET  /rooms/<room>/presence  live nicks (60s expiry) (task 8)
//   POST /rooms/<room>/presence { nick, action: join|leave|heartbeat } (task 8)
//   POST /rooms/<room>/join     { nick }  alias for presence join (task 4)
//   POST /rooms/<room>/attachments { filename, mime, dataBase64 } (tasks 10,11)
//   GET  /rooms/<room>/attachments/<id>  raw bytes (task 11)
//   POST /rooms/<room>/prune    { before, keep_last? }  retention-guarded (task 12)
//   GET  /rooms/<room>/events?cursor=<seq|id>  SSE stream (tasks 16,17)
//
// Pagination: PAGE_SIZE=50 documented default, MAX_LIMIT=200 for
// history/search (messages keeps board's 1000 cap). Cursor = seq
// (integer index) or stable id; nextCursor is the last item's seq.
// Search: case-insensitive AND accent-insensitive (NFD strip).
// Presence: join/leave/heartbeat, 60s expiry (PRESENCE_TTL_MS).
// Delivery: every stored item carries delivery { state: "stored",
//   reason }; the POST reply echoes it. Validation/store failures are
//   4xx/5xx with a NAMED code, delivery state "failed" is reported in
//   the error body (never invented as stored).
// Attachments: decoded cap ATTACH_MAX_BYTES (1 MiB), allowlist
//   image/png, image/jpeg, text/plain, application/pdf. Rejections are
//   named: attachment_malformed | attachment_too_large |
//   attachment_mime_not_allowed | attachment_filename_invalid.
//   Files live OUTSIDE the JSONL under attachments/<room>/, the record
//   keeps the RELATIVE path only.
// Retention: the server NEVER auto-deletes. /prune refuses anything
//   that would leave fewer than 500 messages (RETENTION_MIN_KEEP=500)
//   with code retention_would_leave_fewer_than_500.
// Auth: <dataDir>/token (0600, created on first boot). All POST/DELETE
//   need `x-bus-token: <token>` or `Authorization: Bearer <token>`.
//   GETs stay open so existing polls keep working. Wrong/missing token
//   is 401 with a named code (no body bytes are ever logged).
// Logs: one JSON line per write { ts, room, id, result } — never the
//   message body (nick/text are never passed to the logger).
// Concurrency: a single-writer promise chain serialises appends;
//   the file append itself is one appendFileSync per record.
// Binds 127.0.0.1 only. CORS `*` so product pages keep polling.
//
// Run: node server/bus.mjs  (ports/env below)
//   BUS_PORT (default 18935, the board port site-chat.js already uses)
//   BUS_DATA_DIR, METAOS_STATE (see data dir above)
//   BUS_UPSTASH (reserved: only ""/unset starts; "1" refuses to start)
//
// Stdlib only: no npm deps, no network imports.

import { createHash, randomBytes } from "node:crypto";
import {
  appendFileSync,
  chmodSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOM_RE = /^[a-z0-9-]{1,32}$/;
export const SEVERITIES = new Set(["info", "warning", "critical"]);
export const MAX_BODY_BYTES = 16384; // board-compat cap for messages/notify
export const MAX_ATTACH_BODY_BYTES = 2_100_000; // base64 of 1MiB + JSON slack
export const MAX_NICK_CHARS = 40;
export const MAX_TEXT_CHARS = 2000;
export const MAX_TOPIC_CHARS = 64;
export const MAX_FILENAME_CHARS = 80;
export const PAGE_SIZE = 50; // documented default page size (task 6)
export const MAX_LIMIT = 200; // history/search cap
export const MAX_READ_LIMIT = 1000; // messages cap (board parity)
export const ATTACH_MAX_BYTES = 1_048_576; // 1 MiB decoded (task 10)
export const ATTACH_ALLOWLIST = new Set([
  "image/png",
  "image/jpeg",
  "text/plain",
  "application/pdf",
]);
export const PRESENCE_TTL_MS = 60_000; // task 8
export const RETENTION_MIN_KEEP = 500; // task 12
export const DEFAULT_PORT = 18935;

export function defaultDataDir() {
  if (process.env.BUS_DATA_DIR && process.env.BUS_DATA_DIR.trim()) {
    return path.resolve(process.env.BUS_DATA_DIR.trim());
  }
  const base = process.env.METAOS_STATE
    ? process.env.METAOS_STATE
    : path.join(os.homedir(), ".local", "state", "metaos");
  return path.join(path.resolve(base), "bus");
}

function singleLine(value, maxChars) {
  return (
    typeof value === "string" &&
    value.length >= 1 &&
    value.length <= maxChars &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

export function notifyId(room, topic, severity, text) {
  const hex = createHash("sha256")
    .update([room, topic, severity, text].join("\n"))
    .digest("hex");
  return "ntf-" + hex.slice(0, 16);
}

export function messageId(room, seq, salt) {
  const hex = createHash("sha256")
    .update([room, String(seq), String(salt)].join("\n"))
    .digest("hex");
  return "msg-" + hex.slice(0, 16);
}

// Accent-insensitive fold for search (task 7).
export function foldText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function safeFilename(name) {
  const base = path.basename(String(name));
  const clean = base.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, MAX_FILENAME_CHARS);
  return clean && clean !== "." && clean !== ".." ? clean : "file";
}

function nowSec() {
  return Math.floor(Date.now() / 1000);
}

export function createBusServer(options = {}) {
  const dataDir =
    options.dataDir !== undefined ? options.dataDir : defaultDataDir();
  const logger = options.logger || ((obj) => console.log(JSON.stringify(obj)));

  if ((process.env.BUS_UPSTASH || "").trim() === "1") {
    throw new Error(
      "bus: BUS_UPSTASH=1 requests the remote bus, which is not compiled into this local-only build; unset BUS_UPSTASH to run the file-backed bus"
    );
  }

  const roomsDir = path.join(dataDir, "rooms");
  const attachDir = path.join(dataDir, "attachments");
  const tokenFile = path.join(dataDir, "token");
  const metaFile = path.join(dataDir, "meta.json");
  const presenceFile = path.join(dataDir, "presence.json");

  mkdirSync(roomsDir, { recursive: true });
  mkdirSync(attachDir, { recursive: true });

  // Local-only auth token, 0600 (task 13).
  let token;
  try {
    token = readFileSync(tokenFile, "utf8").trim();
  } catch {
    token = "";
  }
  if (!token) {
    token = randomBytes(24).toString("hex");
    writeFileSync(tokenFile, token + "\n", { mode: 0o600 });
  }
  try {
    chmodSync(tokenFile, 0o600);
  } catch {
    /* non-POSIX fs: best effort */
  }

  // Room name -> ordered message records (persisted as JSONL).
  const rooms = new Map();
  // Room name -> Map(nick -> lastSeenMs).
  const presence = new Map();
  // Room name -> Set(SSE responses).
  const streams = new Map();
  // Attachment id -> { id, room, filename, mime, bytes, path } (relative path).
  const attachments = new Map();
  let lastWrite = null;
  const startedAt = Date.now();

  function roomFile(room) {
    return path.join(roomsDir, room + ".jsonl");
  }

  function logWrite(room, id, result) {
    // Structured, never the body: room + id + result only (task 22).
    try {
      logger({ ts: new Date().toISOString(), room, id, result });
    } catch {
      /* logging must never break the write */
    }
  }

  function touchRoom(room) {
    if (!rooms.has(room)) rooms.set(room, []);
    if (!presence.has(room)) presence.set(room, new Map());
    if (!streams.has(room)) streams.set(room, new Set());
  }

  function loadRoom(room) {
    touchRoom(room);
    const list = rooms.get(room);
    if (list.length > 0 || !existsSync(roomFile(room))) return list;
    if (statSync(roomFile(room)).isDirectory()) {
      throw new Error(`bus store path is a directory: ${roomFile(room)}`);
    }
    const lines = readFileSync(roomFile(room), "utf8").split("\n");
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim() === "") continue;
      let rec;
      try {
        rec = JSON.parse(line);
      } catch {
        throw new Error(
          `bus store corrupted: ${room}.jsonl line ${i + 1} is not valid JSON`
        );
      }
      if (!rec || typeof rec !== "object" || typeof rec.id !== "string") {
        throw new Error(
          `bus store corrupted: ${room}.jsonl line ${i + 1} is not a message record`
        );
      }
      list.push(rec);
      if (rec.attachments) {
        for (const a of rec.attachments) {
          if (a && a.id) attachments.set(a.id, a);
        }
      }
      if (rec.ts) lastWrite = lastWrite || null;
    }
    // Recompute lastWrite from the newest record across rooms lazily.
    return list;
  }

  function persistMeta() {
    try {
      const counts = {};
      for (const [room, list] of rooms) counts[room] = list.length;
      writeFileSync(
        metaFile,
        JSON.stringify({ lastWrite, counts, savedAt: new Date().toISOString() }) + "\n"
      );
    } catch {
      /* best effort */
    }
  }

  // Eagerly load every existing room file so /health counts are exact.
  try {
    for (const name of readdirSync(roomsDir)) {
      if (name.endsWith(".jsonl")) {
        const room = name.slice(0, -".jsonl".length);
        if (ROOM_RE.test(room)) loadRoom(room);
      }
    }
  } catch {
    /* empty store: fine */
  }
  touchRoom("general");
  loadRoom("general");

  // Restore presence snapshot (ephemeral; entries still expire in 60s).
  try {
    const snap = JSON.parse(readFileSync(presenceFile, "utf8"));
    if (snap && typeof snap === "object") {
      for (const [room, roster] of Object.entries(snap)) {
        if (!ROOM_RE.test(room) || !roster || typeof roster !== "object") continue;
        touchRoom(room);
        const map = presence.get(room);
        for (const [nick, seen] of Object.entries(roster)) {
          if (typeof seen === "number" && Number.isFinite(seen)) map.set(nick, seen);
        }
      }
    }
  } catch {
    /* no snapshot yet */
  }

  function savePresence() {
    try {
      const snap = {};
      for (const [room, map] of presence) {
        snap[room] = Object.fromEntries(map);
      }
      writeFileSync(presenceFile, JSON.stringify(snap) + "\n");
    } catch {
      /* best effort */
    }
  }

  function liveNicks(room) {
    const map = presence.get(room) || new Map();
    const now = Date.now();
    const out = [];
    for (const [nick, seen] of map) {
      if (now - seen <= PRESENCE_TTL_MS) out.push(nick);
      else map.delete(nick);
    }
    return out.sort();
  }

  function lineOf(rec) {
    if (rec.kind === "notify") {
      return (
        `board: NOTIFY:${rec.notifyId} ${rec.severity} [${rec.topic}] ` +
        `${rec.text} [ts:${rec.ts}]`
      );
    }
    return `${rec.nick}: ${rec.text} [ts:${rec.ts}]`;
  }

  // Single-writer chain: every append waits for the previous one (task 18).
  let writeQueue = Promise.resolve();
  function enqueueWrite(fn) {
    const run = writeQueue.then(fn, fn);
    // Keep the chain alive even if one write rejects.
    writeQueue = run.catch(() => {});
    return run;
  }

  function storeRecord(room, rec) {
    return enqueueWrite(() => {
      const list = loadRoom(room);
      rec.seq = list.length;
      list.push(rec);
      appendFileSync(roomFile(room), JSON.stringify(rec) + "\n");
      lastWrite = new Date().toISOString();
      persistMeta();
      logWrite(room, rec.id, "stored");
      broadcast(room, rec);
      return rec;
    });
  }

  function broadcast(room, rec) {
    const subs = streams.get(room);
    if (!subs || subs.size === 0) return;
    const payload = "data: " + JSON.stringify(publicItem(rec)) + "\n\n";
    for (const res of [...subs]) {
      try {
        res.write(payload);
      } catch {
        try {
          subs.delete(res);
        } catch {
          /* ignore */
        }
      }
    }
  }

  function publicItem(rec) {
    const out = {
      id: rec.id,
      seq: rec.seq,
      room: rec.room,
      nick: rec.nick,
      text: rec.text,
      ts: rec.ts,
      tsMs: rec.tsMs,
      kind: rec.kind,
      delivery: rec.delivery,
    };
    if (rec.kind === "notify") {
      out.severity = rec.severity;
      out.topic = rec.topic;
      out.notifyId = rec.notifyId;
    }
    if (rec.attachments) out.attachments = rec.attachments;
    return out;
  }

  function totalCount() {
    let n = 0;
    for (const list of rooms.values()) n += list.length;
    return n;
  }

  function checkAuth(req) {
    const header = req.headers["x-bus-token"];
    const auth = req.headers["authorization"];
    let presented = "";
    if (typeof header === "string" && header) presented = header.trim();
    else if (typeof auth === "string" && /^bearer /i.test(auth)) {
      presented = auth.replace(/^bearer /i, "").trim();
    }
    if (!presented) return { ok: false, code: "bus_auth_missing" };
    if (presented !== token) return { ok: false, code: "bus_auth_invalid" };
    return { ok: true };
  }

  function replyJson(res, status, payload) {
    const body = JSON.stringify(payload);
    res.writeHead(status, {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Length": Buffer.byteLength(body),
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Content-Type, X-Bus-Token, Authorization",
    });
    res.end(body);
  }

  function readRawBody(req, cap) {
    return new Promise((resolve, reject) => {
      const chunks = [];
      let total = 0;
      req.on("data", (chunk) => {
        total += chunk.length;
        if (total > cap) {
          reject(new Error("oversized body"));
          req.resume();
          return;
        }
        chunks.push(chunk);
      });
      req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      req.on("error", reject);
    });
  }

  async function readJson(req, res, cap) {
    let raw;
    try {
      raw = await readRawBody(req, cap);
    } catch {
      replyJson(res, 400, {
        error: "request body too large or unreadable",
        code: "bus_body_too_large",
        delivery: { state: "failed", reason: "request body too large or unreadable" },
      });
      return undefined;
    }
    try {
      return JSON.parse(raw);
    } catch {
      replyJson(res, 400, {
        error: "request body is not valid JSON",
        code: "bus_malformed_json",
        delivery: { state: "failed", reason: "request body is not valid JSON" },
      });
      return undefined;
    }
  }

  function needAuth(req, res) {
    const check = checkAuth(req);
    if (!check.ok) {
      replyJson(res, 401, {
        error:
          check.code === "bus_auth_missing"
            ? "missing bus token: send x-bus-token (see <dataDir>/token, mode 0600)"
            : "invalid bus token",
        code: check.code,
        delivery: { state: "failed", reason: check.code },
      });
      return false;
    }
    return true;
  }

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://127.0.0.1");
      const segments = url.pathname
        .split("/")
        .filter((segment) => segment.length > 0);

      if (req.method === "OPTIONS") {
        res.writeHead(204, {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-Bus-Token, Authorization",
          "Access-Control-Max-Age": "600",
        });
        res.end();
        return;
      }

      if (req.method === "GET" && url.pathname === "/") {
        replyJson(res, 200, {
          ok: true,
          service: "metaos-bus",
          board_compat: [
            "GET /rooms/<room>/messages?since=<n>",
            "POST /rooms/<room>/messages { nick, text }",
            "POST /rooms/<room>/notify { severity, topic, text }",
          ],
          dataDir,
          rooms: rooms.size,
        });
        return;
      }

      if (req.method === "GET" && url.pathname === "/health") {
        const counts = {};
        for (const [room, list] of rooms) counts[room] = list.length;
        replyJson(res, 200, {
          ok: true,
          service: "metaos-bus",
          store: "file",
          dataDir,
          rooms: rooms.size,
          count: totalCount(),
          counts,
          lastWrite,
          uptimeSec: Math.floor((Date.now() - startedAt) / 1000),
          pageSize: PAGE_SIZE,
          maxLimit: MAX_LIMIT,
          presenceTtlMs: PRESENCE_TTL_MS,
          retentionMinKeep: RETENTION_MIN_KEEP,
        });
        return;
      }

      if (url.pathname === "/rooms" && req.method === "GET") {
        const list = [...rooms.entries()]
          .map(([room, lines]) => ({ room, count: lines.length }))
          .sort((a, b) => (a.room < b.room ? -1 : a.room > b.room ? 1 : 0));
        replyJson(res, 200, { rooms: list });
        return;
      }

      if (url.pathname === "/rooms" && req.method === "POST") {
        if (!needAuth(req, res)) return;
        const body = await readJson(req, res, MAX_BODY_BYTES);
        if (body === undefined) return;
        if (!ROOM_RE.test(String(body.room || ""))) {
          replyJson(res, 400, {
            error: "room name must match [a-z0-9-]{1,32}",
            code: "bus_bad_room",
            delivery: { state: "failed", reason: "bus_bad_room" },
          });
          return;
        }
        const existed = rooms.has(body.room);
        touchRoom(body.room);
        loadRoom(body.room);
        logWrite(body.room, "-", existed ? "room_exists" : "room_created");
        replyJson(res, existed ? 200 : 201, { room: body.room, created: !existed });
        return;
      }

      if (segments.length >= 2 && segments[0] === "rooms") {
        const room = decodeURIComponent(segments[1]);
        if (!ROOM_RE.test(room)) {
          replyJson(res, 400, {
            error: "room name must match [a-z0-9-]{1,32}",
            code: "bus_bad_room",
          });
          return;
        }
        touchRoom(room);

        // --- SSE stream: GET /rooms/<room>/events (tasks 16, 17) ---
        if (segments.length === 3 && segments[2] === "events" && req.method === "GET") {
          loadRoom(room);
          const list = rooms.get(room);
          let cursorSeq = -1;
          const rawCursor =
            url.searchParams.get("cursor") ?? req.headers["last-event-id"];
          if (rawCursor !== null && rawCursor !== undefined && String(rawCursor) !== "") {
            const asInt = Number.parseInt(String(rawCursor), 10);
            if (Number.isFinite(asInt)) {
              cursorSeq = asInt;
            } else {
              const idx = list.findIndex((r) => r.id === String(rawCursor));
              cursorSeq = idx >= 0 ? idx : -1;
            }
          }
          res.writeHead(200, {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache",
            Connection: "keep-alive",
            "Access-Control-Allow-Origin": "*",
          });
          if (res.flushHeaders) res.flushHeaders();
          // Reconnect replay: missed items first, then live (task 17).
          for (const rec of list.slice(cursorSeq + 1)) {
            res.write("id: " + rec.seq + "\n");
            res.write("data: " + JSON.stringify(publicItem(rec)) + "\n\n");
          }
          const subs = streams.get(room);
          subs.add(res);
          const heartbeat = setInterval(() => {
            try {
              res.write(": heartbeat\n\n");
            } catch {
              /* dead below */
            }
          }, 15000);
          req.on("close", () => {
            clearInterval(heartbeat);
            subs.delete(res);
            try {
              res.end();
            } catch {
              /* already closed */
            }
          });
          return;
        }

        // --- history (paged items): GET /rooms/<room>/history (task 6) ---
        if (segments.length === 3 && segments[2] === "history" && req.method === "GET") {
          const list = loadRoom(room);
          let limit = url.searchParams.get("limit");
          limit = limit === null ? PAGE_SIZE : Number.parseInt(limit, 10);
          if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
            replyJson(res, 400, {
              error: `limit must be an integer from 1 to ${MAX_LIMIT}`,
              code: "bus_bad_limit",
            });
            return;
          }
          const rawCursor = url.searchParams.get("cursor");
          let start = 0;
          if (rawCursor !== null && rawCursor !== "") {
            const asInt = Number.parseInt(rawCursor, 10);
            if (Number.isFinite(asInt)) start = asInt + 1;
            else {
              const idx = list.findIndex((r) => r.id === String(rawCursor));
              start = idx >= 0 ? idx + 1 : 0;
            }
          }
          if (start < 0) start = 0;
          const page = list.slice(start, start + limit).map(publicItem);
          const nextCursor = page.length ? page[page.length - 1].seq : start - 1;
          replyJson(res, 200, {
            room,
            total: list.length,
            pageSize: PAGE_SIZE,
            items: page,
            nextCursor,
          });
          return;
        }

        // --- search (task 7) ---
        if (segments.length === 3 && segments[2] === "search" && req.method === "GET") {
          const list = loadRoom(room);
          const q = url.searchParams.get("q") || "";
          if (!q || q.length > 500) {
            replyJson(res, 400, {
              error: "q is required (1-500 chars)",
              code: "bus_bad_query",
            });
            return;
          }
          let limit = url.searchParams.get("limit");
          limit = limit === null ? PAGE_SIZE : Number.parseInt(limit, 10);
          if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
            replyJson(res, 400, {
              error: `limit must be an integer from 1 to ${MAX_LIMIT}`,
              code: "bus_bad_limit",
            });
            return;
          }
          const needle = foldText(q);
          const hits = list
            .filter(
              (r) =>
                foldText(r.nick).includes(needle) || foldText(r.text).includes(needle)
            )
            .slice(-limit)
            .map(publicItem);
          replyJson(res, 200, { room, query: q, total: hits.length, items: hits });
          return;
        }

        // --- presence (task 8) ---
        if (segments.length === 3 && segments[2] === "presence") {
          if (req.method === "GET") {
            const online = liveNicks(room);
            replyJson(res, 200, { room, online, count: online.length });
            return;
          }
          if (req.method === "POST") {
            if (!needAuth(req, res)) return;
            const body = await readJson(req, res, MAX_BODY_BYTES);
            if (body === undefined) return;
            if (!singleLine(body.nick, MAX_NICK_CHARS)) {
              replyJson(res, 400, {
                error: `nick must be a single line of 1-${MAX_NICK_CHARS} chars`,
                code: "bus_bad_nick",
                delivery: { state: "failed", reason: "bus_bad_nick" },
              });
              return;
            }
            const action = String(body.action || "heartbeat");
            if (!["join", "leave", "heartbeat"].includes(action)) {
              replyJson(res, 400, {
                error: 'action must be one of "join", "leave", "heartbeat"',
                code: "bus_bad_presence_action",
                delivery: { state: "failed", reason: "bus_bad_presence_action" },
              });
              return;
            }
            const map = presence.get(room) || new Map();
            presence.set(room, map);
            if (action === "leave") map.delete(body.nick);
            else map.set(body.nick, Date.now());
            savePresence();
            logWrite(room, body.nick, "presence_" + action);
            replyJson(res, 200, {
              room,
              nick: body.nick,
              action,
              online: liveNicks(room),
            });
            return;
          }
        }

        // --- join alias (task 4) ---
        if (segments.length === 3 && segments[2] === "join" && req.method === "POST") {
          if (!needAuth(req, res)) return;
          const body = await readJson(req, res, MAX_BODY_BYTES);
          if (body === undefined) return;
          if (!singleLine(body.nick, MAX_NICK_CHARS)) {
            replyJson(res, 400, {
              error: `nick must be a single line of 1-${MAX_NICK_CHARS} chars`,
              code: "bus_bad_nick",
              delivery: { state: "failed", reason: "bus_bad_nick" },
            });
            return;
          }
          const map = presence.get(room) || new Map();
          presence.set(room, map);
          map.set(body.nick, Date.now());
          savePresence();
          loadRoom(room);
          logWrite(room, body.nick, "join");
          replyJson(res, 200, {
            room,
            nick: body.nick,
            online: liveNicks(room),
            count: loadRoom(room).length,
          });
          return;
        }

        // --- attachments (tasks 10, 11) ---
        if (segments.length === 3 && segments[2] === "attachments" && req.method === "POST") {
          if (!needAuth(req, res)) return;
          const body = await readJson(req, res, MAX_ATTACH_BODY_BYTES);
          if (body === undefined) return;
          const filename = String(body.filename || "");
          const mime = String(body.mime || "");
          const dataB64 = String(body.dataBase64 || body.dataUrl?.split(",").pop() || "");
          if (!singleLine(filename, MAX_FILENAME_CHARS) || filename.includes("/")) {
            replyJson(res, 400, {
              error: "filename must be a single line of 1-80 chars with no slashes",
              code: "attachment_filename_invalid",
              delivery: { state: "failed", reason: "attachment_filename_invalid" },
            });
            return;
          }
          if (!ATTACH_ALLOWLIST.has(mime)) {
            replyJson(res, 415, {
              error:
                "mime not allowed (allowlist: " +
                [...ATTACH_ALLOWLIST].join(", ") +
                ")",
              code: "attachment_mime_not_allowed",
              delivery: { state: "failed", reason: "attachment_mime_not_allowed" },
            });
            return;
          }
          let bytes;
          try {
            if (!/^[A-Za-z0-9+/=_-]*$/.test(dataB64.replace(/\s/g, "")) || !dataB64) {
              throw new Error("bad base64");
            }
            bytes = Buffer.from(dataB64, "base64");
          } catch {
            replyJson(res, 400, {
              error: "dataBase64 is not valid base64",
              code: "attachment_malformed",
              delivery: { state: "failed", reason: "attachment_malformed" },
            });
            return;
          }
          if (bytes.length === 0 || bytes.length > ATTACH_MAX_BYTES) {
            replyJson(res, 413, {
              error: `attachment is ${bytes.length} bytes; cap is ${ATTACH_MAX_BYTES}`,
              code: "attachment_too_large",
              delivery: { state: "failed", reason: "attachment_too_large" },
            });
            return;
          }
          const id =
            "att-" + createHash("sha256").update(room + "\n" + Date.now() + "\n" + randomBytes(8).toString("hex")).digest("hex").slice(0, 16);
          const roomAttachDir = path.join(attachDir, room);
          mkdirSync(roomAttachDir, { recursive: true });
          const diskName = id + "-" + safeFilename(filename);
          writeFileSync(path.join(roomAttachDir, diskName), bytes);
          const relPath = path.posix.join("attachments", room, diskName);
          const record = { id, room, filename: safeFilename(filename), mime, bytes: bytes.length, path: relPath };
          attachments.set(id, record);
          logWrite(room, id, "attachment_stored");
          replyJson(res, 201, record);
          return;
        }

        if (
          segments.length === 4 &&
          segments[2] === "attachments" &&
          req.method === "GET"
        ) {
          const id = decodeURIComponent(segments[3]);
          const meta = attachments.get(id);
          // Fall back to disk scan so restarts keep serving files.
          let filePath = null;
          let mime = "application/octet-stream";
          let filename = id;
          if (meta && meta.room === room) {
            filePath = path.join(dataDir, meta.path);
            mime = meta.mime;
            filename = meta.filename;
          } else {
            const roomAttachDir = path.join(attachDir, room);
            try {
              for (const name of readdirSync(roomAttachDir)) {
                if (name.startsWith(id + "-")) {
                  filePath = path.join(roomAttachDir, name);
                  filename = name.slice(id.length + 1);
                  break;
                }
              }
            } catch {
              filePath = null;
            }
          }
          if (!filePath || !existsSync(filePath)) {
            replyJson(res, 404, { error: "attachment not found", code: "bus_no_attachment" });
            return;
          }
          try {
            const bytes = readFileSync(filePath);
            res.writeHead(200, {
              "Content-Type": mime,
              "Content-Length": bytes.length,
              "Content-Disposition": 'inline; filename="' + filename.replace(/"/g, "") + '"',
              "Access-Control-Allow-Origin": "*",
            });
            res.end(bytes);
          } catch {
            replyJson(res, 500, { error: "attachment unreadable", code: "bus_attachment_io" });
          }
          return;
        }

        // --- retention-guarded prune (task 12) ---
        if (segments.length === 3 && segments[2] === "prune" && req.method === "POST") {
          if (!needAuth(req, res)) return;
          const body = await readJson(req, res, MAX_BODY_BYTES);
          if (body === undefined) return;
          const list = loadRoom(room);
          const before = Number(body.before);
          if (!Number.isInteger(before) || before < 0) {
            replyJson(res, 400, {
              error: "before must be a non-negative integer seq",
              code: "bus_bad_prune",
            });
            return;
          }
          const keepLast =
            body.keep_last === undefined ? RETENTION_MIN_KEEP : Number(body.keep_last);
          if (!Number.isInteger(keepLast) || keepLast < RETENTION_MIN_KEEP) {
            replyJson(res, 400, {
              error: `keep_last must be an integer >= ${RETENTION_MIN_KEEP}`,
              code: "bus_bad_keep_last",
            });
            return;
          }
          const doomed = list.filter((r) => r.seq < before);
          const remaining = list.length - doomed.length;
          if (remaining < RETENTION_MIN_KEEP) {
            replyJson(res, 409, {
              error: `refused: pruning to seq ${before} would leave ${remaining} messages (minimum ${RETENTION_MIN_KEEP})`,
              code: "retention_would_leave_fewer_than_500",
              total: list.length,
              wouldRemain: remaining,
            });
            return;
          }
          const kept = list.filter((r) => r.seq >= before);
          // Rewrite the JSONL atomically (tmp + rename); seqs are STABLE
          // (never renumbered) so cursors stay valid.
          const tmp = roomFile(room) + ".tmp-" + process.pid;
          writeFileSync(tmp, kept.map((r) => JSON.stringify(r)).join("") + (kept.length ? "\n" : ""));
          renameSync(tmp, roomFile(room));
          rooms.set(room, kept);
          persistMeta();
          logWrite(room, "prune:" + before, "pruned");
          replyJson(res, 200, { room, pruned: doomed.length, total: kept.length });
          return;
        }

        // --- board-compat messages (tasks 3, 5) ---
        if (segments.length === 3 && segments[2] === "messages") {
          if (req.method === "GET") {
            const list = loadRoom(room);
            const rawSince = url.searchParams.get("since");
            let since = rawSince === null ? -1 : Number.parseInt(rawSince, 10);
            if (!Number.isFinite(since) || since < -1) since = -1;
            const rawLimit = url.searchParams.get("limit");
            let limit = null;
            if (rawLimit !== null) {
              const parsed = Number(rawLimit);
              if (
                !Number.isInteger(parsed) ||
                parsed < 1 ||
                parsed > MAX_READ_LIMIT
              ) {
                replyJson(res, 400, {
                  error: `limit must be an integer from 1 to ${MAX_READ_LIMIT}`,
                  code: "bus_bad_limit",
                });
                return;
              }
              limit = parsed;
            }
            const slice = list.slice(since + 1);
            const capped = limit === null ? slice : slice.slice(0, limit);
            replyJson(res, 200, {
              room,
              total: list.length,
              messages: capped.map(lineOf),
              items: capped.map(publicItem),
            });
            return;
          }
          if (req.method === "POST") {
            if (!needAuth(req, res)) return;
            const body = await readJson(req, res, MAX_BODY_BYTES);
            if (body === undefined) return;
            if (!singleLine(body.nick, MAX_NICK_CHARS)) {
              replyJson(res, 400, {
                error: `nick must be a single line of 1-${MAX_NICK_CHARS} chars`,
                code: "bus_bad_nick",
                delivery: { state: "failed", reason: "bus_bad_nick" },
              });
              return;
            }
            if (!singleLine(body.text, MAX_TEXT_CHARS)) {
              replyJson(res, 400, {
                error: `text must be a single line of 1-${MAX_TEXT_CHARS} chars`,
                code: "bus_bad_text",
                delivery: { state: "failed", reason: "bus_bad_text" },
              });
              return;
            }
            let linked = [];
            if (body.attachmentIds !== undefined) {
              if (
                !Array.isArray(body.attachmentIds) ||
                body.attachmentIds.some((v) => typeof v !== "string")
              ) {
                replyJson(res, 400, {
                  error: "attachmentIds must be an array of attachment ids",
                  code: "bus_bad_attachments",
                  delivery: { state: "failed", reason: "bus_bad_attachments" },
                });
                return;
              }
              for (const aid of body.attachmentIds) {
                const meta = attachments.get(aid);
                if (!meta || meta.room !== room) {
                  replyJson(res, 400, {
                    error: `unknown attachment ${aid} for this room`,
                    code: "bus_no_attachment",
                    delivery: { state: "failed", reason: "bus_no_attachment" },
                  });
                  return;
                }
                linked.push(meta);
              }
            }
            const ts = nowSec();
            const rec = {
              id: messageId(room, loadRoom(room).length, randomBytes(8).toString("hex")),
              seq: -1, // assigned by storeRecord (stable thereafter)
              room,
              nick: body.nick,
              text: body.text,
              ts,
              tsMs: Date.now(),
              kind: "message",
              delivery: { state: "stored", reason: "appended to room log" },
            };
            if (linked.length) rec.attachments = linked;
            const stored = await storeRecord(room, rec);
            replyJson(res, 201, {
              index: stored.seq,
              id: stored.id,
              ts: stored.ts,
              delivery: stored.delivery,
            });
            return;
          }
        }

        // --- board-compat notify (task 3) ---
        if (segments.length === 3 && segments[2] === "notify" && req.method === "POST") {
          if (!needAuth(req, res)) return;
          const body = await readJson(req, res, MAX_BODY_BYTES);
          if (body === undefined) return;
          if (!SEVERITIES.has(body.severity)) {
            replyJson(res, 400, {
              error: 'severity must be one of "info", "warning", "critical"',
              code: "bus_bad_severity",
              delivery: { state: "failed", reason: "bus_bad_severity" },
            });
            return;
          }
          if (!singleLine(body.topic, MAX_TOPIC_CHARS)) {
            replyJson(res, 400, {
              error: `topic must be a single line of 1-${MAX_TOPIC_CHARS} chars`,
              code: "bus_bad_topic",
              delivery: { state: "failed", reason: "bus_bad_topic" },
            });
            return;
          }
          if (!singleLine(body.text, MAX_TEXT_CHARS)) {
            replyJson(res, 400, {
              error: `text must be a single line of 1-${MAX_TEXT_CHARS} chars`,
              code: "bus_bad_text",
              delivery: { state: "failed", reason: "bus_bad_text" },
            });
            return;
          }
          const id = notifyId(room, body.topic, body.severity, body.text);
          const ts = nowSec();
          const rec = {
            id: messageId(room, loadRoom(room).length, id),
            seq: -1,
            room,
            nick: "board",
            text: body.text,
            ts,
            tsMs: Date.now(),
            kind: "notify",
            severity: body.severity,
            topic: body.topic,
            notifyId: id,
            delivery: { state: "stored", reason: "appended to room log" },
          };
          const stored = await storeRecord(room, rec);
          replyJson(res, 201, { index: stored.seq, id, seq: stored.seq });
          return;
        }
      }

      replyJson(res, 404, { error: "not found", code: "bus_not_found" });
    } catch (err) {
      replyJson(res, 500, {
        error: `internal error: ${err.message}`,
        code: "bus_internal",
      });
    }
  });

  // Sweep stale presence every 10s (TTL is 60s; the sweep only GCs).
  const sweep = setInterval(() => {
    try {
      for (const [room] of presence) liveNicks(room);
    } catch {
      /* never crash on sweep */
    }
  }, 10_000);
  if (sweep.unref) sweep.unref();

  return server;
}

export function tokenForDir(dataDir) {
  return readFileSync(path.join(dataDir, "token"), "utf8").trim();
}

const invokedDirectly =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  const port = Number(process.env.BUS_PORT || process.env.BOARD_PORT || DEFAULT_PORT);
  let server;
  try {
    server = createBusServer();
  } catch (err) {
    console.error("bus: " + err.message);
    process.exit(2);
  }
  server.listen(port, "127.0.0.1", () => {
    const addr = server.address();
    console.log(
      `metaos-bus listening on http://${addr.address}:${addr.port} (store: file, dataDir: ${defaultDataDir()})`
    );
  });
}
