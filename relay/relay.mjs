#!/usr/bin/env node
// Meta Nuntius — the Trio / Meta OS layer's own message relay.
//
// A small, dependency-free reimplementation of the muse-relay line
// protocol, built during the hackathon so the OS-operates-the-Trio
// layer has a standalone bus inside this repo. It mirrors only the
// protocol concepts of the crew's pre-existing external bus (plain
// text lines, named rooms, send-time stamps, NOTIFY lines) — no code
// is shared with it, and this service does not replace it.
//
// Protocol:
//   message line : "<nick>: <text> [ts:<epoch-seconds>]"
//   notify line  : "relay: NOTIFY:<id> <severity> [<topic>] <text>
//                   [ts:<epoch-seconds>]"
//   notify id    : "ntf-" + first 16 hex chars of sha256 over
//                  room + "\n" + topic + "\n" + severity + "\n" + text
//   severity     : one of "info" | "warning" | "critical"
//
// Polling is watermark-based: POST returns the new line's 0-based
// index in its room; GET ?since=<n> returns the lines after index n
// (since=-1, or no since, returns the whole room).
//
// Validation caps (refusals are 400 JSON errors):
//   room : /^[a-z0-9-]{1,32}$/
//   nick : 1-40 chars, single line, no control characters
//   text : 1-2000 chars, single line
//   topic: 1-64 chars, single line
//   request body: at most 16384 bytes of JSON
//   since: -1 or a non-negative integer; lower values are refused
//   limit: 1-1000, applied to the oldest pending lines
//
// Each room keeps at most MAX_ROOM_LINES lines (default 1000). When the
// cap is exceeded the oldest lines are dropped, never below
// MIN_RETAINED_LINES. POST /messages returns {index, id}; the id is a
// stable digest of room + index + line.
//
// Storage is in-memory by default. If RELAY_STORE_FILE is set, every
// appended line is also written to that file as one JSON record per
// line ({"room": ..., "line": ...}) and the file is reloaded on
// boot, so rooms survive a restart.
//
// Run: node relay/relay.mjs        (port: RELAY_PORT, default 8787)
// Stdlib only: node:http, node:fs, node:crypto, node:path, node:url.

import { createHash } from "node:crypto";
import { appendFileSync, existsSync, readFileSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOM_RE = /^[a-z0-9-]{1,32}$/;
export const SEVERITIES = new Set(["info", "warning", "critical"]);
export const MAX_BODY_BYTES = 16384;
export const MAX_NICK_CHARS = 40;
export const MAX_TEXT_CHARS = 2000;
export const MAX_TOPIC_CHARS = 64;
export const MAX_ROOM_LINES = 1000;
export const MIN_RETAINED_LINES = 10;
export const MAX_READ_LIMIT = 1000;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VIEWER_PATH = path.join(HERE, "viewer.html");

function isSingleLine(value, max) {
  return (
    typeof value === "string" &&
    value.length >= 1 &&
    value.length <= max &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

export function validateMessage(payload) {
  if (!payload || typeof payload !== "object") {
    return { ok: false, error: "request body must be a JSON object" };
  }
  if (!isSingleLine(payload.nick, MAX_NICK_CHARS)) {
    return {
      ok: false,
      error: `nick must be a single line of 1-${MAX_NICK_CHARS} chars`,
    };
  }
  if (!isSingleLine(payload.text, MAX_TEXT_CHARS)) {
    return {
      ok: false,
      error: `text must be a single line of 1-${MAX_TEXT_CHARS} chars`,
    };
  }
  return { ok: true };
}

export function validateNotify(payload) {
  if (!payload || typeof payload !== "object") {
    return { ok: false, error: "request body must be a JSON object" };
  }
  if (!SEVERITIES.has(payload.severity)) {
    return {
      ok: false,
      error: 'severity must be one of "info", "warning", "critical"',
    };
  }
  if (!isSingleLine(payload.topic, MAX_TOPIC_CHARS)) {
    return {
      ok: false,
      error: `topic must be a single line of 1-${MAX_TOPIC_CHARS} chars`,
    };
  }
  if (!isSingleLine(payload.text, MAX_TEXT_CHARS)) {
    return {
      ok: false,
      error: `text must be a single line of 1-${MAX_TEXT_CHARS} chars`,
    };
  }
  return { ok: true };
}

export function formatMessage(nick, text, tsSeconds) {
  const ts = tsSeconds === undefined ? Math.floor(Date.now() / 1000) : tsSeconds;
  return `${nick}: ${text} [ts:${ts}]`;
}

export function parseMessageLine(line) {
  const match = /^(.*): (.*) \[ts:(\d+)\]$/.exec(String(line));
  if (!match) {
    throw new Error(
      "malformed message line: expected '<nick>: <text> [ts:<seconds>]'"
    );
  }
  return { nick: match[1], text: match[2], ts: Number(match[3]) };
}

export function messageId(room, index, line) {
  const basis = `${room}\n${index}\n${line}`;
  return "msg-" + createHash("sha256").update(basis).digest("hex").slice(0, 16);
}

export function trimLines(lines, maxLines = MAX_ROOM_LINES) {
  if (!Array.isArray(lines)) {
    throw new TypeError("trimLines requires an array of lines");
  }
  const requested = Number(maxLines);
  const cap = Number.isFinite(requested)
    ? Math.max(1, Math.floor(requested))
    : MAX_ROOM_LINES;
  const keep = Math.max(cap, MIN_RETAINED_LINES);
  return lines.length <= keep ? lines.slice() : lines.slice(lines.length - keep);
}

export function notifyId(room, topic, severity, text) {
  const basis = `${room}\n${topic}\n${severity}\n${text}`;
  return "ntf-" + createHash("sha256").update(basis).digest("hex").slice(0, 16);
}

export function createRelayServer(options = {}) {
  const storeFile =
    options.storeFile !== undefined
      ? options.storeFile
      : process.env.RELAY_STORE_FILE || null;

  /** @type {Map<string, string[]>} room name -> lines */
  const rooms = new Map();
  const configuredCap = Number(options.maxLinesPerRoom);
  const roomCap = Number.isFinite(configuredCap)
    ? configuredCap
    : MAX_ROOM_LINES;

  if (storeFile && existsSync(storeFile)) {
    for (const raw of readFileSync(storeFile, "utf8").split("\n")) {
      if (!raw.trim()) continue;
      try {
        const rec = JSON.parse(raw);
        if (typeof rec.room === "string" && typeof rec.line === "string") {
          if (!rooms.has(rec.room)) rooms.set(rec.room, []);
          rooms.get(rec.room).push(rec.line);
        }
      } catch {
        // A torn final record must not stop the relay from booting.
        console.error("Meta Nuntius: skipped an unparseable store record");
      }
    }
  }

  function appendLine(room, line) {
    if (!rooms.has(room)) rooms.set(room, []);
    const lines = rooms.get(room);
    lines.push(line);
    if (lines.length > roomCap) {
      const kept = trimLines(lines, roomCap);
      lines.splice(0, lines.length, ...kept);
    }
    const index = lines.length - 1;
    if (storeFile) {
      try {
        appendFileSync(storeFile, JSON.stringify({ room, line }) + "\n");
      } catch (err) {
        console.error(`Meta Nuntius: store append failed: ${err.message}`);
      }
    }
    return index;
  }

  function sendJson(res, status, obj) {
    const body = JSON.stringify(obj);
    res.writeHead(status, {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(body),
    });
    res.end(body);
  }

  function readBody(req) {
    return new Promise((resolve, reject) => {
      const chunks = [];
      let size = 0;
      req.on("data", (chunk) => {
        size += chunk.length;
        if (size > MAX_BODY_BYTES) {
          reject(new Error("request body too large"));
          req.resume(); // drain so the 400 response can still be sent
          return;
        }
        chunks.push(chunk);
      });
      req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      req.on("error", reject);
    });
  }

  async function readJsonBody(req, res) {
    let raw;
    try {
      raw = await readBody(req);
    } catch {
      sendJson(res, 400, {
        error: `request body too large (max ${MAX_BODY_BYTES} bytes) or unreadable`,
      });
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch {
      sendJson(res, 400, { error: "request body is not valid JSON" });
      return null;
    }
  }

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://127.0.0.1");
      const parts = url.pathname.split("/").filter((p) => p.length > 0);

      if (req.method === "GET" && url.pathname === "/") {
        let html;
        try {
          html = readFileSync(VIEWER_PATH, "utf8");
        } catch {
          res.writeHead(500, { "Content-Type": "text/plain" });
          res.end("viewer.html is missing beside relay.mjs");
          return;
        }
        res.writeHead(200, {
          "Content-Type": "text/html; charset=utf-8",
          "Content-Length": Buffer.byteLength(html),
        });
        res.end(html);
        return;
      }

      if (req.method === "GET" && url.pathname === "/health") {
        sendJson(res, 200, {
          ok: true,
          rooms: rooms.size,
          store: storeFile ? "file" : "memory",
        });
        return;
      }

      if (req.method === "GET" && url.pathname === "/rooms") {
        const list = [...rooms.entries()]
          .map(([room, lines]) => ({ room, count: lines.length }))
          .sort((a, b) => (a.room < b.room ? -1 : a.room > b.room ? 1 : 0));
        sendJson(res, 200, { rooms: list });
        return;
      }

      if (parts.length === 3 && parts[0] === "rooms") {
        const room = decodeURIComponent(parts[1]);
        const action = parts[2];
        if (!ROOM_RE.test(room)) {
          sendJson(res, 400, {
            error: "room name must match [a-z0-9-]{1,32}",
          });
          return;
        }

        if (req.method === "POST" && action === "messages") {
          const body = await readJsonBody(req, res);
          if (body === null) return;
          const checked = validateMessage(body);
          if (!checked.ok) {
            sendJson(res, 400, { error: checked.error });
            return;
          }
          const line = formatMessage(body.nick, body.text);
          const index = appendLine(room, line);
          sendJson(res, 201, { index, id: messageId(room, index, line) });
          return;
        }

        if (req.method === "POST" && action === "notify") {
          const body = await readJsonBody(req, res);
          if (body === null) return;
          const checked = validateNotify(body);
          if (!checked.ok) {
            sendJson(res, 400, { error: checked.error });
            return;
          }
          const { severity, topic, text } = body;
          const id = notifyId(room, topic, severity, text);
          const line =
            `relay: NOTIFY:${id} ${severity} [${topic}] ${text} ` +
            `[ts:${Math.floor(Date.now() / 1000)}]`;
          sendJson(res, 201, { index: appendLine(room, line), id });
          return;
        }

        if (req.method === "GET" && action === "messages") {
          const rawSince = url.searchParams.get("since");
          let since = -1;
          if (rawSince !== null) {
            const parsed = Number(rawSince);
            if (!Number.isInteger(parsed) || parsed < -1) {
              sendJson(res, 400, {
                error: "since must be -1 or a non-negative integer",
              });
              return;
            }
            since = parsed;
          }
          const rawLimit = url.searchParams.get("limit");
          let limit = null;
          if (rawLimit !== null) {
            const parsed = Number(rawLimit);
            if (
              !Number.isInteger(parsed) ||
              parsed < 1 ||
              parsed > MAX_READ_LIMIT
            ) {
              sendJson(res, 400, {
                error: `limit must be an integer from 1 to ${MAX_READ_LIMIT}`,
              });
              return;
            }
            limit = parsed;
          }
          const lines = rooms.get(room) || [];
          let messages = lines.slice(since + 1);
          if (limit !== null) messages = messages.slice(0, limit);
          sendJson(res, 200, {
            room,
            total: lines.length,
            messages,
          });
          return;
        }
      }

      sendJson(res, 404, { error: "not found" });
    } catch (err) {
      sendJson(res, 500, { error: `internal error: ${err.message}` });
    }
  });

  return server;
}

const isMain =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMain) {
  const port = Number(process.env.RELAY_PORT || 8787);
  const server = createRelayServer();
  server.listen(port, () => {
    const store = process.env.RELAY_STORE_FILE ? "file" : "memory";
    console.log(
      `Meta Nuntius relay listening on port ${port} (store: ${store})`
    );
  });
}
