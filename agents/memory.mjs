// Meta OS agent layer — per-agent memory (AGENT_LAYER_SPEC.md §8).
//
// An agent may persist three things: its job records, its baton state and its
// ledger. Nothing else. Memory lives under the layer's own root, one directory
// per agent, and a registry field caps its size.
//
// Records are append-only by construction: this module exposes no call that
// truncates or rewrites a ledger, so an agent cannot rewrite its own history.
// `writeRecord` exists for the two things that legitimately change in place —
// baton.json and a job record — and it still refuses a path outside the
// allowlist and any write that would cross the cap.
//
//   node agents/memory.mjs check <dir> [maxBytes] [--json]
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

export const DEFAULT_MAX_BYTES = 5 * 1024 * 1024;
export const RECORD_FILES = ["baton.json", "ledger.jsonl"];
export const JOBS_DIR = "jobs";

export class MemoryError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "MemoryError";
    this.code = code;
    Object.assign(this, detail);
  }
}

// One directory per agent, and the name is checked because it becomes a path:
// a name like "../root" would write outside the layer's own tree.
export function memoryDir(root, agent) {
  if (typeof agent !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(agent)) {
    throw new MemoryError("memory-name", "memory: bad agent name " + JSON.stringify(agent));
  }
  return path.join(root, "memory", agent);
}

// The cap is registry data, not agent judgment. A missing field takes the
// default, which is deliberate: every existing entry predates the field, and
// refusing them would make the layer unable to start.
export function capFor(agent) {
  const cap = agent && agent.memory ? agent.memory.maxBytes : undefined;
  if (cap == null) return DEFAULT_MAX_BYTES;
  if (!Number.isInteger(cap) || cap <= 0) {
    throw new MemoryError(
      "memory-cap",
      "registry: " + (agent && agent.name) + " bad memory.maxBytes"
    );
  }
  return cap;
}

function normalise(rel) {
  if (typeof rel !== "string" || rel.trim() === "") {
    throw new MemoryError("memory-path", "memory: empty path");
  }
  if (path.isAbsolute(rel)) {
    throw new MemoryError("memory-path", "memory: absolute path refused: " + rel);
  }
  const norm = path.normalize(rel).replace(/\\/g, "/");
  if (norm === ".." || norm.startsWith("../") || norm.includes("/../")) {
    throw new MemoryError("memory-path", "memory: path escapes the agent directory: " + rel);
  }
  const allowed =
    RECORD_FILES.includes(norm) ||
    (norm.startsWith(JOBS_DIR + "/") && norm !== JOBS_DIR + "/");
  if (!allowed) {
    throw new MemoryError(
      "memory-record",
      "memory: not an allowed record: " + norm + " (allowed: " +
        RECORD_FILES.join(", ") + ", " + JOBS_DIR + "/)"
    );
  }
  return norm;
}

export function usage(dir) {
  const total = { files: 0, bytes: 0 };
  const walk = (current) => {
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile()) {
        total.files += 1;
        total.bytes += fs.statSync(full).size;
      }
    }
  };
  walk(dir);
  return total;
}

// Write a record that legitimately changes in place. The size check runs
// BEFORE the write, so a refused write leaves the directory byte-identical.
export function writeRecord(dir, rel, data, { maxBytes = DEFAULT_MAX_BYTES } = {}) {
  const norm = normalise(rel);
  const body = typeof data === "string" ? data : JSON.stringify(data, null, 2) + "\n";
  const target = path.join(dir, norm);
  const now = usage(dir);
  const existing = fs.existsSync(target) ? fs.statSync(target).size : 0;
  const after = now.bytes - existing + Buffer.byteLength(body);
  if (after > maxBytes) {
    throw new MemoryError(
      "memory-cap",
      "memory: write refused, " + after + " > " + maxBytes + " bytes",
      { usage: now.bytes, cap: maxBytes }
    );
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, body);
  return { path: target, bytes: after };
}

// Append one JSONL line. No rewrite path exists, on purpose.
export function appendLedger(dir, entry, { maxBytes = DEFAULT_MAX_BYTES } = {}) {
  if (!entry || typeof entry !== "object") {
    throw new MemoryError("memory-entry", "memory: ledger entry must be an object");
  }
  const line = JSON.stringify(entry) + "\n";
  const now = usage(dir);
  const size = Buffer.byteLength(line);
  if (now.bytes + size > maxBytes) {
    throw new MemoryError(
      "memory-cap",
      "memory: ledger append refused, " + (now.bytes + size) + " > " + maxBytes + " bytes",
      { usage: now.bytes, cap: maxBytes }
    );
  }
  fs.mkdirSync(dir, { recursive: true });
  const target = path.join(dir, "ledger.jsonl");
  fs.appendFileSync(target, line);
  return { path: target, bytes: now.bytes + size };
}

export function readLedger(dir) {
  const target = path.join(dir, "ledger.jsonl");
  if (!fs.existsSync(target)) return [];
  const out = [];
  for (const line of fs.readFileSync(target, "utf8").split("\n")) {
    if (!line) continue;
    try {
      out.push(JSON.parse(line));
    } catch {
      // A torn last line is a crash, not permission to drop the whole history.
    }
  }
  return out;
}

export function check(dir, maxBytes = DEFAULT_MAX_BYTES) {
  const used = usage(dir);
  return {
    dir,
    files: used.files,
    bytes: used.bytes,
    cap: maxBytes,
    ok: used.bytes <= maxBytes,
    overBy: Math.max(0, used.bytes - maxBytes),
  };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const args = process.argv.slice(2);
  const json = args.includes("--json");
  const rest = args.filter((a) => a !== "--json");
  const [cmd, dir, limit] = rest;
  if (cmd !== "check" || !dir) {
    console.error("usage: memory.mjs check <dir> [maxBytes] [--json]");
    process.exit(1);
  }
  const cap = limit ? Number(limit) : DEFAULT_MAX_BYTES;
  if (!Number.isInteger(cap) || cap <= 0) {
    console.error("memory: maxBytes must be a positive integer");
    process.exit(1);
  }
  const result = check(dir, cap);
  if (json) console.log(JSON.stringify(result, null, 2));
  else {
    console.log(
      "memory: " + result.files + " file(s), " + result.bytes + " of " + cap + " bytes" +
        (result.ok ? "" : " — OVER by " + result.overBy)
    );
  }
  process.exit(result.ok ? 0 : 2);
}
