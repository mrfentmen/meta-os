#!/usr/bin/env node
// The Board — Meta OS's in-OS messaging board (Layer 6: shell and apps).
//
// The Board is the crew relay remade as a native board inside Meta OS.
// It speaks the same plain-text line protocol as relay/ ("Meta
// Nuntius"), which itself mirrors the external muse-relay crew bus:
//
//   message line : "<nick>: <text> [ts:<epoch-seconds>]"
//   notify line  : "board: NOTIFY:<id> <severity> [<topic>] <text>
//                   [ts:<epoch-seconds>]"
//   notify id    : "ntf-" + first 16 hex chars of sha256 over
//                  room + "\n" + topic + "\n" + severity + "\n" + text
//   severity     : one of "info" | "warning" | "critical"
//
// Lines are addressed by a per-room 0-based index. POST returns the
// index of the line it appended; GET /rooms/<room>/messages?since=<n>
// returns the lines after index n (since=-1, or no since, returns the
// whole room). Clients poll with a watermark instead of re-fetching.
//
// Endpoints:
//   GET  /                              the viewer (board.html)
//   GET  /health                        { ok, rooms, store }
//   GET  /rooms                         [{ room, count }, ...]
//   GET  /rooms/<room>/messages?since=n lines after index n
//   POST /rooms/<room>/messages         { nick, text } -> 201 { index }
//   POST /rooms/<room>/notify           { severity, topic, text }
//                                       -> 201 { index, id }
//
// Validation (every refusal is a 400 with a JSON error body):
//   room : /^[a-z0-9-]{1,32}$/
//   nick : 1-40 chars, single line, no control characters
//   text : 1-2000 chars, single line
//   topic: 1-64 chars, single line
//   request body: at most 16384 bytes of JSON
//
// Storage is in-memory unless BOARD_STORE_FILE is set. With a store
// file, each appended line is written as one JSONL record
// ({"room": ..., "line": ...}) and the file is replayed on boot, so
// the board survives a restart. A torn final record is skipped, never
// fatal.
//
// Run: node board/board.mjs     (port: BOARD_PORT, default 8790)
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

const BOARD_DIR = path.dirname(fileURLToPath(import.meta.url));
const VIEWER_FILE = path.join(BOARD_DIR, "board.html");

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

function nowStamp() {
  return `[ts:${Math.floor(Date.now() / 1000)}]`;
}

export function createBoardServer(options = {}) {
  const storeFile =
    options.storeFile !== undefined
      ? options.storeFile
      : process.env.BOARD_STORE_FILE || null;

  /** Room name -> ordered array of protocol lines. */
  const rooms = new Map();

  function linesOf(room) {
    if (!rooms.has(room)) rooms.set(room, []);
    return rooms.get(room);
  }

  if (storeFile && existsSync(storeFile)) {
    const records = readFileSync(storeFile, "utf8").split("\n");
    for (const record of records) {
      if (record.trim() === "") continue;
      let parsed;
      try {
        parsed = JSON.parse(record);
      } catch {
        console.error("Board: skipped an unparseable store record on boot");
        continue;
      }
      if (typeof parsed.room === "string" && typeof parsed.line === "string") {
        linesOf(parsed.room).push(parsed.line);
      }
    }
  }

  function append(room, line) {
    const lines = linesOf(room);
    lines.push(line);
    if (storeFile) {
      try {
        appendFileSync(storeFile, JSON.stringify({ room, line }) + "\n");
      } catch (err) {
        console.error(`Board: store append failed: ${err.message}`);
      }
    }
    return lines.length - 1;
  }

  function replyJson(res, status, payload) {
    const body = JSON.stringify(payload);
    res.writeHead(status, {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(body),
    });
    res.end(body);
  }

  function readRawBody(req) {
    return new Promise((resolve, reject) => {
      const chunks = [];
      let total = 0;
      req.on("data", (chunk) => {
        total += chunk.length;
        if (total > MAX_BODY_BYTES) {
          reject(new Error("oversized body"));
          req.destroy();
          return;
        }
        chunks.push(chunk);
      });
      req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      req.on("error", reject);
    });
  }

  // Returns the parsed body, or undefined after already sending a 400.
  async function readJson(req, res) {
    let raw;
    try {
      raw = await readRawBody(req);
    } catch {
      replyJson(res, 400, { error: "request body too large or unreadable" });
      return undefined;
    }
    try {
      return JSON.parse(raw);
    } catch {
      replyJson(res, 400, { error: "request body is not valid JSON" });
      return undefined;
    }
  }

  async function handlePost(req, res, room, action) {
    const body = await readJson(req, res);
    if (body === undefined) return;

    if (action === "messages") {
      if (!singleLine(body.nick, MAX_NICK_CHARS)) {
        replyJson(res, 400, {
          error: `nick must be a single line of 1-${MAX_NICK_CHARS} chars`,
        });
        return;
      }
      if (!singleLine(body.text, MAX_TEXT_CHARS)) {
        replyJson(res, 400, {
          error: `text must be a single line of 1-${MAX_TEXT_CHARS} chars`,
        });
        return;
      }
      const index = append(room, `${body.nick}: ${body.text} ${nowStamp()}`);
      replyJson(res, 201, { index });
      return;
    }

    // action === "notify"
    if (!SEVERITIES.has(body.severity)) {
      replyJson(res, 400, {
        error: 'severity must be one of "info", "warning", "critical"',
      });
      return;
    }
    if (!singleLine(body.topic, MAX_TOPIC_CHARS)) {
      replyJson(res, 400, {
        error: `topic must be a single line of 1-${MAX_TOPIC_CHARS} chars`,
      });
      return;
    }
    if (!singleLine(body.text, MAX_TEXT_CHARS)) {
      replyJson(res, 400, {
        error: `text must be a single line of 1-${MAX_TEXT_CHARS} chars`,
      });
      return;
    }
    const id = notifyId(room, body.topic, body.severity, body.text);
    const line =
      `board: NOTIFY:${id} ${body.severity} [${body.topic}] ` +
      `${body.text} ${nowStamp()}`;
    replyJson(res, 201, { index: append(room, line), id });
  }

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://127.0.0.1");
      const segments = url.pathname
        .split("/")
        .filter((segment) => segment.length > 0);

      if (req.method === "GET" && url.pathname === "/") {
        let html;
        try {
          html = readFileSync(VIEWER_FILE, "utf8");
        } catch {
          res.writeHead(500, { "Content-Type": "text/plain" });
          res.end("board.html is missing beside board.mjs");
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
        replyJson(res, 200, {
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
        replyJson(res, 200, { rooms: list });
        return;
      }

      if (segments.length === 3 && segments[0] === "rooms") {
        const room = decodeURIComponent(segments[1]);
        const action = segments[2];
        if (!ROOM_RE.test(room)) {
          replyJson(res, 400, {
            error: "room name must match [a-z0-9-]{1,32}",
          });
          return;
        }

        if (
          req.method === "POST" &&
          (action === "messages" || action === "notify")
        ) {
          await handlePost(req, res, room, action);
          return;
        }

        if (req.method === "GET" && action === "messages") {
          const rawSince = url.searchParams.get("since");
          let since = rawSince === null ? -1 : Number.parseInt(rawSince, 10);
          if (!Number.isFinite(since) || since < -1) since = -1;
          const lines = rooms.get(room) || [];
          replyJson(res, 200, {
            room,
            total: lines.length,
            messages: lines.slice(since + 1),
          });
          return;
        }
      }

      replyJson(res, 404, { error: "not found" });
    } catch (err) {
      replyJson(res, 500, { error: `internal error: ${err.message}` });
    }
  });

  return server;
}

const invokedDirectly =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  const port = Number(process.env.BOARD_PORT || 8790);
  createBoardServer().listen(port, () => {
    const store = process.env.BOARD_STORE_FILE ? "file" : "memory";
    console.log(`Meta OS Board listening on port ${port} (store: ${store})`);
  });
}
