// Meta Trio assessment server (Rowan's lane). Zero dependencies: plain
// node:http, matching the repo's no-build-step rule.
//
//   node server/server.mjs            # or: npm start
//   PORT=8080 (default — the native app's default endpoint is
//   http://localhost:8080/api/assess, and the web app's default endpoint
//   is the relative /api/assess, which this server satisfies by also
//   serving the static web frontend from the repo root.)
//
// Routes:
//   POST /api/assess   the v2 assessment endpoint (see assess.mjs)
//   GET  /api/health   { ok, service, products, model: {configured,
//                      live_enabled} } — never exposes the key itself
//   GET  /api/crew/status  read-only agent-crew status for the
//                      Command view's loop feed (see crew-status.mjs)
//   GET  /<static>     index.html, styles.css, js/* from the repo root
//
// Environment: SPARK_API_KEY (key slot, server-side only),
// ASSESS_LIVE_MODEL=1 (test-phase gate; leave unset during the build —
// Del's Spark ruling), PORT. See server/README.md.

import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { handleAssess } from "./assess.mjs";
import { modelStatus } from "./model.mjs";
import { readCrewStatus } from "./crew-status.mjs";
import { PRODUCT_IDS } from "../js/products.js";

const MAX_BODY_BYTES = 12 * 1024 * 1024; // JSON envelope cap (image cap is in assess.mjs)
const STATIC_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

function sendJson(res, status, body) {
  const text = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(text),
    "Access-Control-Allow-Origin": "*",
  });
  res.end(text);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on("data", (chunk) => {
      total += chunk.length;
      if (total > MAX_BODY_BYTES) {
        reject(Object.assign(new Error(`request body exceeds ${MAX_BODY_BYTES} bytes`), { status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function serveStatic(res, urlPath) {
  const rel = urlPath === "/" ? "index.html" : urlPath.replace(/^\/+/, "");
  const ext = path.extname(rel);
  if (!Object.hasOwn(CONTENT_TYPES, ext)) {
    sendJson(res, 404, { error: `not found: ${urlPath}` });
    return;
  }
  const filePath = path.resolve(STATIC_ROOT, rel);
  if (!filePath.startsWith(STATIC_ROOT + path.sep)) {
    sendJson(res, 404, { error: `not found: ${urlPath}` });
    return;
  }
  try {
    const data = await readFile(filePath);
    res.writeHead(200, {
      "Content-Type": CONTENT_TYPES[ext],
      "Content-Length": data.length,
      "Access-Control-Allow-Origin": "*",
    });
    res.end(data);
  } catch {
    sendJson(res, 404, { error: `not found: ${urlPath}` });
  }
}

export function createAssessServer(deps = {}) {
  const env = deps.env ?? process.env;
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://localhost");
      if (req.method === "OPTIONS") {
        res.writeHead(204, {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        });
        res.end();
        return;
      }
      if (url.pathname === "/api/assess") {
        if (req.method !== "POST") {
          sendJson(res, 405, { error: "method not allowed: use POST" });
          return;
        }
        let raw;
        try {
          raw = await readBody(req);
        } catch (err) {
          sendJson(res, err.status ?? 400, { error: err.message });
          return;
        }
        let payload;
        try {
          payload = JSON.parse(raw);
        } catch {
          sendJson(res, 400, { error: "request body is not valid JSON" });
          return;
        }
        const { status, body } = await handleAssess(payload, deps);
        sendJson(res, status, body);
        return;
      }
      if (url.pathname === "/api/health") {
        if (req.method !== "GET") {
          sendJson(res, 405, { error: "method not allowed: use GET" });
          return;
        }
        sendJson(res, 200, {
          ok: true,
          service: "meta-trio-assess",
          products: PRODUCT_IDS,
          model: modelStatus(env),
        });
        return;
      }
      if (url.pathname === "/api/crew/status") {
        if (req.method !== "GET") {
          sendJson(res, 405, { error: "method not allowed: use GET" });
          return;
        }
        // Read-only projection of the agent crew's records (patrol
        // heartbeat, event feed, incidents, simulated dispatch log)
        // for the Command view's loop feed. deps.crewStatus is the
        // test seam; production reads the crew data directory.
        const read = deps.crewStatus ?? readCrewStatus;
        sendJson(res, 200, await read());
        return;
      }
      if (url.pathname.startsWith("/api/")) {
        sendJson(res, 404, { error: `unknown route: ${url.pathname}` });
        return;
      }
      if (req.method !== "GET") {
        sendJson(res, 405, { error: "method not allowed" });
        return;
      }
      await serveStatic(res, url.pathname);
    } catch (err) {
      sendJson(res, 500, { error: `internal error: ${err && err.message ? err.message : String(err)}` });
    }
  });
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const port = Number(process.env.PORT ?? 8080);
  const server = createAssessServer();
  server.listen(port, () => {
    const status = modelStatus();
    console.log(`meta-trio-assess listening on http://localhost:${port}`);
    console.log(`POST /api/assess  GET /api/health  static web app on /`);
    console.log(
      `model: key ${status.configured ? "configured" : "NOT configured"}, live calls ${status.live_enabled ? "ENABLED (test phase)" : "held (Spark rule)"}`,
    );
  });
}
