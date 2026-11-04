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
// file, each appended line or post is written as one JSONL record and
// the file is replayed on boot. A corrupted record, wrong shape, or a
// path that is a directory raises the board's named error instead of
// returning a partial board as if it were good.
//
// GET /rooms/<room>/posts?limit=<1-1000> returns the oldest posts first.
// renderPost / renderBoard / escapeHtml are exported pure render helpers;
// messageToNote adapts a relay message line with the nick as author.
//
// Run: node board/board.mjs     (port: BOARD_PORT, default 8790)
// Stdlib only: node:http, node:fs, node:crypto, node:path, node:url.

import { createHash } from "node:crypto";
import { appendFileSync, existsSync, readFileSync, statSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOM_RE = /^[a-z0-9-]{1,32}$/;
export const SEVERITIES = new Set(["info", "warning", "critical"]);
export const MAX_BODY_BYTES = 16384;
export const MAX_NICK_CHARS = 40;
export const MAX_TEXT_CHARS = 2000;
export const MAX_TITLE_CHARS = 200;
export const MAX_TOPIC_CHARS = 64;
export const MAX_READ_LIMIT = 1000;

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

const HTML_ESCAPES = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

export function escapeHtml(value) {
  return String(value === undefined || value === null ? "" : value).replace(
    /[&<>"']/g,
    (character) => HTML_ESCAPES[character]
  );
}

export const EMPTY_BOARD_HTML =
  '<section id="board" class="empty"><p>No notes yet.</p></section>';

export function renderPost(post) {
  return (
    `<article class="post" data-id="${escapeHtml(post.id)}">` +
    `<header><h3>${escapeHtml(post.title)}</h3>` +
    `<span class="author">${escapeHtml(post.author)}</span></header>` +
    `<p>${escapeHtml(post.text)}</p></article>`
  );
}

export function renderBoard(posts) {
  const visible = (Array.isArray(posts) ? posts : []).filter(
    (post) => post && !post.deleted
  );
  if (visible.length === 0) return EMPTY_BOARD_HTML;
  return `<section id="board">${visible.map(renderPost).join("")}</section>`;
}

export function sortPosts(posts) {
  return (Array.isArray(posts) ? posts.slice() : []).sort(
    (a, b) => (Number(a.ts) || 0) - (Number(b.ts) || 0)
  );
}

export function messageToNote(line, room = "main") {
  const match = /^(.*): (.*) \[ts:(\d+)\]$/.exec(String(line));
  if (!match) {
    throw new Error("cannot adapt malformed relay message line");
  }
  const nick = match[1];
  const text = match[2];
  const id = "note-" + createHash("sha256")
    .update([room, line].join("\n"))
    .digest("hex")
    .slice(0, 16);
  return {
    id,
    room,
    title: `Message from ${nick}`,
    author: nick,
    text,
    ts: Number(match[3]),
    deleted: false,
  };
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

  /** Room name -> ordered post records (tombstones included). */
  const posts = new Map();

  function postsOf(room) {
    if (!posts.has(room)) posts.set(room, []);
    return posts.get(room);
  }

  function touchRoom(room) {
    if (!rooms.has(room)) rooms.set(room, []);
  }

  if (storeFile && existsSync(storeFile)) {
    if (statSync(storeFile).isDirectory()) {
      throw new Error(`board store path is a directory: ${storeFile}`);
    }
    const records = readFileSync(storeFile, "utf8").split("\n");
    records.forEach((record, lineNumber) => {
      if (record.trim() === "") return;
      let parsed;
      try {
        parsed = JSON.parse(record);
      } catch {
        throw new Error(
          `board store corrupted: line ${lineNumber + 1} is not valid JSON`
        );
      }
      const isPost =
        parsed &&
        typeof parsed === "object" &&
        typeof parsed.room === "string" &&
        parsed.post &&
        typeof parsed.post === "object" &&
        typeof parsed.post.id === "string";
      const isLine =
        parsed &&
        typeof parsed === "object" &&
        typeof parsed.room === "string" &&
        typeof parsed.line === "string";
      if (!isPost && !isLine) {
        throw new Error(
          `board store corrupted: line ${lineNumber + 1} is not a {room,line} or {room,post} record`
        );
      }
      if (isPost) {
        const list = postsOf(parsed.room);
        const index = list.findIndex((p) => p && p.id === parsed.post.id);
        if (index >= 0) list[index] = parsed.post;
        else list.push(parsed.post);
        touchRoom(parsed.room);
      } else {
        linesOf(parsed.room).push(parsed.line);
      }
    });
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

  function savePost(room, post) {
    touchRoom(room);
    const list = postsOf(room);
    const index = list.findIndex((p) => p.id === post.id);
    if (index >= 0) list[index] = post;
    else list.push(post);
    if (storeFile) {
      try {
        appendFileSync(storeFile, JSON.stringify({ room, post }) + "\n");
      } catch (err) {
        console.error(`Board: store append failed: ${err.message}`);
      }
    }
  }

  function replyJson(res, status, payload) {
    const body = JSON.stringify(payload);
    res.writeHead(status, {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(body),
      // The product pages (Custos, Officina, the two labs) are served from
      // the site root on another port, and each carries the Board chat box.
      // Without this header their reads and posts are blocked by the browser.
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Content-Type",
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
          req.resume(); // drain so the 400 response can still be sent
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

    if (action === "posts") {
      if (!singleLine(body.title, MAX_TITLE_CHARS)) {
        replyJson(res, 400, {
          error: `title must be a single line of 1-${MAX_TITLE_CHARS} chars`,
        });
        return;
      }
      if (!singleLine(body.author, MAX_NICK_CHARS)) {
        replyJson(res, 400, {
          error: `author must be a single line of 1-${MAX_NICK_CHARS} chars`,
        });
        return;
      }
      const text = body.text === undefined ? "" : body.text;
      if (text !== "" && !singleLine(text, MAX_TEXT_CHARS)) {
        replyJson(res, 400, {
          error: `text must be a single line of 0-${MAX_TEXT_CHARS} chars`,
        });
        return;
      }
      const list = postsOf(room);
      const id = "post-" + createHash("sha256")
        .update([room, body.author, body.title, text, String(Date.now()), String(list.length)].join("\n"))
        .digest("hex")
        .slice(0, 16);
      const post = {
        id, room, title: body.title, author: body.author, text,
        ts: Math.floor(Date.now() / 1000), deleted: false,
      };
      savePost(room, post);
      replyJson(res, 201, { post });
      return;
    }

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

      // CORS preflight for the chat box on the product pages (other port).
      if (req.method === "OPTIONS") {
        res.writeHead(204, {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "600",
        });
        res.end();
        return;
      }

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
          .map(([room, lines]) => ({ room, count: lines.length, posts: postsOf(room).length }))
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
          (action === "messages" || action === "notify" || action === "posts")
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

        if (req.method === "GET" && action === "posts") {
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
              });
              return;
            }
            limit = parsed;
          }
          const list = sortPosts(postsOf(room));
          replyJson(res, 200, {
            room,
            total: list.length,
            posts: limit === null ? list : list.slice(0, limit),
          });
          return;
        }
      }

      if (segments.length === 4 && segments[0] === "rooms" && segments[2] === "posts") {
        const room = decodeURIComponent(segments[1]);
        const id = decodeURIComponent(segments[3]);
        if (!ROOM_RE.test(room)) {
          replyJson(res, 400, { error: "room name must match [a-z0-9-]{1,32}" });
          return;
        }
        if (req.method === "PATCH" || req.method === "DELETE") {
          const body = await readJson(req, res);
          if (body === undefined) return;
          const post = postsOf(room).find((p) => p.id === id);
          if (!post || post.deleted) {
            replyJson(res, 404, { error: "post not found" });
            return;
          }
          if (!singleLine(body.author, MAX_NICK_CHARS) || body.author !== post.author) {
            replyJson(res, 403, { error: "author does not own this post" });
            return;
          }
          if (req.method === "PATCH") {
            if (!singleLine(body.title, MAX_TITLE_CHARS)) {
              replyJson(res, 400, {
                error: `title must be a single line of 1-${MAX_TITLE_CHARS} chars`,
              });
              return;
            }
            const text = body.text === undefined ? post.text : body.text;
            if (text !== "" && !singleLine(text, MAX_TEXT_CHARS)) {
              replyJson(res, 400, {
                error: `text must be a single line of 0-${MAX_TEXT_CHARS} chars`,
              });
              return;
            }
            const updated = { ...post, title: body.title, text, edited_at: Math.floor(Date.now() / 1000) };
            savePost(room, updated);
            replyJson(res, 200, { post: updated });
            return;
          }
          const tombstone = {
            ...post, deleted: true, deleted_by: body.author,
            deleted_at: Math.floor(Date.now() / 1000),
          };
          savePost(room, tombstone);
          replyJson(res, 200, { post: tombstone });
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
