// Meta OS agent layer — the tool gateway (AGENTIC build, P0).
//
// A tool call is not a function call with a promise attached. It is a permissioned action that
// must leave a receipt. This module is the one place a read, write, append, exec, network call,
// spend, or wall-clock check passes through: the grant is checked BEFORE the action, the action
// is recorded AFTER it, and a refusal is recorded too. A receipt is what makes `recordResult`
// evidence checkable instead of prose.
//
// The kernel does not enforce this. Its frozen ABI is syscalls 0-5 (exit, write, sleep, pid,
// yield, read_key) with no file, network, or spawn; agent policy lives at L5 in userspace, on
// the host today. See docs/AGENT_LAYER_SPEC.md.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { assertGranted, grantDigest, normalizeGrants } from "./grants.mjs";
import { appendLoud, writeFileLoud } from "./safe-write.mjs";
import { contractDigest, openStep } from "./contract.mjs";

export const TOOL_KINDS = ["read", "write", "append", "exec", "network", "spend", "wall"];
const MAX_OUTPUT_BYTES = 8 * 1024 * 1024;

export class ToolError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "ToolError";
    this.code = code;
    for (const [key, value] of Object.entries(detail)) if (!(key in this)) this[key] = value;
  }
}

function isText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function sha256(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

function stripQuery(target) {
  try {
    const url = new URL(target);
    return url.origin + url.pathname;
  } catch {
    return String(target);
  }
}

function sanitize(request) {
  if (!request || typeof request !== "object") return {};
  if (request.kind === "write" || request.kind === "append") {
    const data = request.kind === "write" ? request.data : request.text;
    return { path: request.path == null ? null : String(request.path), bytes: Buffer.byteLength(data == null ? "" : String(data)) };
  }
  if (request.kind === "exec") {
    return { argv: Array.isArray(request.argv) ? request.argv.map(String) : null, cwd: request.cwd == null ? null : String(request.cwd) };
  }
  if (request.kind === "network") {
    return { url: request.url == null ? null : stripQuery(request.url), method: request.method || "GET" };
  }
  if (request.kind === "spend") return { usd: request.usd, reason: request.reason || null };
  if (request.kind === "wall") return {};
  return { path: request.path == null ? null : String(request.path) };
}

function readReceipts(file) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return { entries: [], torn: 0 };
  }
  const entries = [];
  let torn = 0;
  for (const line of text.split("\n")) {
    if (!line) continue;
    try {
      entries.push(JSON.parse(line));
    } catch {
      torn += 1;
    }
  }
  return { entries, torn };
}

// The gateway is bound to one run directory. Receipts are append-only JSONL, and the spend
// total is reconstructed from them, never from a caller-supplied number.
export function createToolGateway({
  grants,
  root = process.cwd(),
  runDir,
  runId = null,
  agent = "agent",
  contract = null,
  env = process.env,
  now = () => Date.now(),
  fetchImpl = fetch,
} = {}) {
  if (!isText(runDir)) throw new ToolError("run-dir-required", "gateway: a run directory is required");
  const normalized = normalizeGrants(grants || {}, { root });
  const receiptsFile = path.join(runDir, "receipts.jsonl");
  fs.mkdirSync(runDir, { recursive: true });
  const existing = readReceipts(receiptsFile);
  let seq = existing.entries.reduce((max, entry) => (Number.isInteger(entry.seq) && entry.seq > max ? entry.seq : max), 0);
  let spentUsd = existing.entries
    .filter((entry) => entry.kind === "spend" && entry.ok === true && Number.isFinite(entry.usd))
    .reduce((sum, entry) => sum + entry.usd, 0);
  const startedAt = now();
  const grantHash = grantDigest(normalized);

  function record(entry) {
    seq += 1;
    const step = contract ? openStep(contract) : null;
    const receipt = {
      id: "tool-" + seq + "-" + crypto.randomBytes(3).toString("hex"),
      seq,
      at: new Date(now()).toISOString(),
      run: runId,
      agent,
      grant: grantHash,
      ...(contract ? { contract: contractDigest(contract), step: step ? step.id : null } : {}),
      ...entry,
    };
    appendLoud(receiptsFile, JSON.stringify(receipt) + "\n");
    return receipt;
  }

  function refuse(kind, code, message, request, detail = {}) {
    const receipt = record({ kind, ok: false, code, request: sanitize(request), ...detail });
    throw new ToolError(code, kind + " refused: " + message, { receipt });
  }

  function granted(kind, request, grantRequest) {
    try {
      return assertGranted(normalized, grantRequest);
    } catch (error) {
      if (error && error.code) refuse(kind, error.code, error.message, request, { detail: error.code });
      throw error;
    }
  }

  async function call(request = {}) {
    if (!request || typeof request !== "object" || !TOOL_KINDS.includes(request.kind)) {
      throw new ToolError("tool-kind-invalid", "gateway: request.kind must be one of " + TOOL_KINDS.join(", "));
    }
    const kind = request.kind;

    if (kind === "read") {
      if (!isText(request.path)) refuse(kind, "path-required", "a path is required", request);
      const target = path.resolve(root, request.path);
      granted(kind, request, { kind: "read", path: target, root });
      let data;
      try {
        data = fs.readFileSync(target);
      } catch (error) {
        refuse(kind, "read-failed", String(error.message || error), request, { path: target });
      }
      const receipt = record({ kind, ok: true, path: target, bytes: data.length, sha256: sha256(data) });
      return { receipt, result: { data, encoding: "buffer" } };
    }

    if (kind === "write" || kind === "append") {
      if (!isText(request.path)) refuse(kind, "path-required", "a path is required", request);
      const data = kind === "write" ? request.data : request.text;
      if (data == null || (typeof data !== "string" && !Buffer.isBuffer(data))) {
        refuse(kind, "data-required", "data must be a string or Buffer", request);
      }
      const target = path.resolve(root, request.path);
      granted(kind, request, { kind: "write", path: target, root });
      const buffer = Buffer.isBuffer(data) ? data : Buffer.from(String(data));
      try {
        if (kind === "write") writeFileLoud(target, buffer);
        else appendLoud(target, buffer);
      } catch (error) {
        refuse(kind, "write-failed", String(error.message || error), request, { path: target });
      }
      const receipt = record({ kind, ok: true, path: target, bytes: buffer.length, sha256: sha256(buffer) });
      return { receipt, result: { path: target, bytes: buffer.length } };
    }

    if (kind === "exec") {
      if (!Array.isArray(request.argv) || request.argv.length === 0) {
        refuse(kind, "command-required", "argv must be a non-empty array", request);
      }
      const argv = request.argv.map(String);
      const cwd = request.cwd == null ? root : path.resolve(root, request.cwd);
      // A caller-supplied cwd is a filesystem claim; the default cwd is the root this gateway
      // already runs in and is not a new permission.
      if (request.cwd != null) granted(kind, request, { kind: "read", path: cwd, root });
      granted(kind, request, { kind: "exec", argv, root, env });
      const timeoutMs = Math.min(Number(request.timeoutMs) > 0 ? Number(request.timeoutMs) : 120000, normalized.maxWallMs || 120000);
      const started = now();
      const result = spawnSync(argv[0], argv.slice(1), {
        cwd,
        env,
        timeout: timeoutMs,
        encoding: "utf8",
        maxBuffer: MAX_OUTPUT_BYTES,
      });
      let exit;
      if (result.error && result.error.code === "ETIMEDOUT") exit = 124;
      else if (result.error) exit = 127;
      else exit = result.status == null ? 1 : result.status;
      const stdout = result.stdout || "";
      const stderr = result.stderr || "";
      const receipt = record({
        kind,
        ok: exit === 0,
        argv,
        cwd,
        exit,
        signal: result.signal || null,
        stdoutBytes: Buffer.byteLength(stdout),
        stderrBytes: Buffer.byteLength(stderr),
        stdoutSha256: sha256(stdout),
        stderrSha256: sha256(stderr),
        durationMs: now() - started,
      });
      return { receipt, result: { exit, signal: result.signal || null, stdout, stderr } };
    }

    if (kind === "network") {
      let url;
      try {
        url = new URL(String(request.url));
      } catch {
        refuse(kind, "url-invalid", "a valid URL is required", request);
      }
      if (url.protocol !== "http:" && url.protocol !== "https:") {
        refuse(kind, "url-scheme-refused", "only http and https are allowed", request);
      }
      const port = Number(url.port || (url.protocol === "https:" ? 443 : 80));
      granted(kind, request, { kind: "network", host: url.hostname, port });
      const timeoutMs = Math.min(Number(request.timeoutMs) > 0 ? Number(request.timeoutMs) : 30000, normalized.maxWallMs || 30000);
      const started = now();
      let response, body;
      try {
        response = await fetchImpl(url, {
          method: request.method || "GET",
          headers: request.headers || {},
          body: request.body == null ? undefined : request.body,
          redirect: "manual",
          signal: AbortSignal.timeout(timeoutMs),
        });
        if (response.status >= 300 && response.status < 400) {
          refuse(kind, "network-redirect", "a redirect is not followed; grant the final host explicitly", request, {
            status: response.status,
            url: stripQuery(String(url)),
          });
        }
        body = await response.text();
      } catch (error) {
        // A redirect refusal is already a recorded receipt; do not reclassify it as a
        // transport failure on the way out.
        if (error instanceof ToolError) throw error;
        const code = error && (error.name === "TimeoutError" || error.name === "AbortError") ? "network-timeout" : "network-failed";
        refuse(kind, code, String((error && error.message) || error), request, { url: stripQuery(String(url)) });
      }
      const buffer = Buffer.from(body);
      const receipt = record({
        kind,
        ok: true,
        method: request.method || "GET",
        url: stripQuery(String(url)),
        status: response.status,
        bytes: buffer.length,
        sha256: sha256(buffer),
        durationMs: now() - started,
      });
      return { receipt, result: { status: response.status, body, contentType: response.headers.get("content-type") } };
    }

    if (kind === "spend") {
      const verdict = granted(kind, request, { kind: "spend", usd: request.usd, spentUsd });
      spentUsd += Number(request.usd);
      const receipt = record({ kind, ok: true, usd: Number(request.usd), spentUsd, capUsd: verdict.capUsd });
      return { receipt, result: { usd: Number(request.usd), spentUsd, capUsd: verdict.capUsd } };
    }

    // wall
    const verdict = granted(kind, request, { kind: "wall", elapsedMs: now() - startedAt });
    const receipt = record({ kind, ok: true, elapsedMs: now() - startedAt, capMs: verdict.capMs });
    return { receipt, result: { elapsedMs: now() - startedAt, capMs: verdict.capMs } };
  }

  return {
    call,
    receipts: () => readReceipts(receiptsFile).entries,
    receiptsFile,
    spentUsd: () => spentUsd,
    grants: normalized,
    root,
    runDir,
  };
}

// The evidence string a contract result should carry when the action was tool-backed. The
// receipt id is the part that can be checked; the hash is the part that can be compared.
export function receiptEvidence(receipt) {
  if (!receipt || !isText(receipt.id)) throw new ToolError("receipt-required", "evidence: a receipt is required");
  const hash = receipt.sha256 ? " sha256:" + receipt.sha256 : "";
  return "tool:" + receipt.id + hash;
}
