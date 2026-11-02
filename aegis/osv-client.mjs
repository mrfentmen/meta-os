// Meta Aegis — the OSV client (AEGIS_SPEC.md, "Sweep" v1).
//
// Aegis is allowed to contact OSV only through the boss's own OSV server
// (os-build/aegis/README.md: "the first build is allowed to contact OSV only through the
// boss's own MCP servers"). The server in his gateway config is `osv-mcp`; this file speaks
// MCP to an instance of it over stdio, so the data still arrives through that server and not
// by calling api.osv.dev directly.
//
// Not in this file: no HTTP, no scraping, no fallback endpoint. If the server is not there,
// the caller gets an error and the sweep is recorded as blocked -- a fallback that quietly
// reaches a different source would make every report's "source" line a guess.
import { spawn } from "node:child_process";

export class OsvError extends Error {}

// One line of JSON per message, per the MCP stdio framing.
export function openOsv({ serverPath, args = [], timeoutMs = 60000 } = {}) {
  if (!serverPath) throw new OsvError("osv: serverPath is required (the osv-mcp entry point)");
  const child = spawn(process.execPath, [serverPath, ...args], { stdio: ["pipe", "pipe", "pipe"] });
  let buf = "";
  let nextId = 1;
  let closed = false;
  const pending = new Map();
  const stderr = [];

  const failAll = (err) => {
    for (const [, p] of pending) p.reject(err);
    pending.clear();
  };

  child.stdout.on("data", (d) => {
    buf += d.toString();
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 1);
      if (!line) continue;
      let msg;
      try { msg = JSON.parse(line); } catch { continue; }   // a non-JSON line is not a reply
      const p = msg.id != null ? pending.get(msg.id) : null;
      if (!p) continue;
      pending.delete(msg.id);
      if (msg.error) p.reject(new OsvError("osv: " + (msg.error.message || JSON.stringify(msg.error))));
      else p.resolve(msg.result);
    }
  });
  child.stderr.on("data", (d) => { if (stderr.length < 20) stderr.push(d.toString().slice(0, 400)); });
  child.on("exit", (code, signal) => {
    closed = true;
    failAll(new OsvError("osv: server exited (code " + code + ", signal " + signal + ")" +
      (stderr.length ? " :: " + stderr.join("").slice(0, 600) : "")));
  });

  const request = (method, params) => new Promise((resolve, reject) => {
    if (closed) return reject(new OsvError("osv: server is closed"));
    const id = nextId++;
    pending.set(id, { resolve, reject });
    const timer = setTimeout(() => {
      if (pending.delete(id)) reject(new OsvError("osv: " + method + " timed out after " + timeoutMs + "ms"));
    }, timeoutMs);
    const settle = (fn) => (v) => { clearTimeout(timer); fn(v); };
    const p = pending.get(id);
    p.resolve = settle(p.resolve);
    p.reject = settle(p.reject);
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });

  const notify = (method, params) => {
    if (!closed) child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");
  };

  const client = {
    async init() {
      const res = await request("initialize", {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "aegis-sweep", version: "1" },
      });
      notify("notifications/initialized");
      return res && res.serverInfo ? res.serverInfo : { name: "unknown", version: "unknown" };
    },
    async listTools() {
      const res = await request("tools/list", {});
      return (res && res.tools) || [];
    },
    async callTool(name, args) {
      const res = await request("tools/call", { name, arguments: args });
      if (res && res.isError) {
        const text = (res.content || []).map((c) => c.text || "").join(" ").slice(0, 400);
        throw new OsvError("osv: " + name + " returned an error: " + text);
      }
      // MCP tools answer with content parts; osv-mcp puts one JSON document in the text part.
      const text = (res && res.content || []).filter((c) => c.type === "text").map((c) => c.text).join("\n");
      if (!text) return res && res.structuredContent ? res.structuredContent : null;
      try { return JSON.parse(text); } catch { return { text }; }
    },
    close() {
      if (!closed) { closed = true; child.stdin.end(); child.kill(); }
    },
  };
  return client;
}
