// Meta OS agent layer — enforced grants (AGENTIC build order, item 3).
//
// `capabilities` in the registry says which lane an agent belongs to. That is a dispatch
// label, not a permission. This file is the permission side: a grant set is checked BEFORE a
// tool call, it denies by default, and composition can only narrow it. A child run cannot be
// granted more than its parent — widening throws instead of quietly succeeding.
//
// Grant shape (normalized):
//   {
//     read: ["/abs/root", ...],
//     write: ["/abs/root", ...],
//     commands: ["node", "/abs/program", ...],
//     hosts: [{ host: "api.example.com" | "*.example.com", ports: [443] }],
//     maxSpendUsd: 2 | null,
//     maxWallMs: 60000 | null
//   }
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { appendLoud, writeFileLoud } from "./safe-write.mjs";

export class GrantError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "GrantError";
    this.code = code;
    for (const [k, v] of Object.entries(detail)) if (!(k in this)) this[k] = v;
  }
}

function isText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function toList(value, name) {
  if (value == null) return [];
  if (!Array.isArray(value)) throw new GrantError("invalid-grant", "grants: " + name + " must be an array");
  return value.map((entry) => {
    if (!isText(entry)) throw new GrantError("invalid-grant", "grants: " + name + " entries must be non-empty strings");
    return entry.trim();
  });
}

// Resolve a path even when its leaf does not exist yet. The nearest existing ancestor is
// realpath'd, so a symlinked parent cannot smuggle a write outside a granted root.
export function realpathLoose(target) {
  const resolved = path.resolve(target);
  let current = resolved;
  const missing = [];
  while (true) {
    try {
      const real = fs.realpathSync(current);
      return missing.length ? path.join(real, ...missing.reverse()) : real;
    } catch {
      const parent = path.dirname(current);
      if (parent === current) return resolved;
      missing.push(path.basename(current));
      current = parent;
    }
  }
}

export function insideRoot(root, target) {
  const rel = path.relative(path.resolve(root), path.resolve(target));
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

function normalizeRoots(value, name, root) {
  return [...new Set(toList(value, name).map((entry) => realpathLoose(path.resolve(root, entry))))];
}

function validHost(host) {
  if (!isText(host)) return false;
  if (/\s|\/|\\/.test(host)) return false;
  const bare = host.startsWith("*.") ? host.slice(2) : host;
  if (bare.length === 0 || bare.startsWith(".") || bare.endsWith(".")) return false;
  return true;
}

function normalizeHosts(rawHosts, fallbackPorts) {
  if (rawHosts == null) return [];
  if (!Array.isArray(rawHosts)) throw new GrantError("invalid-grant", "grants: hosts must be an array");
  return rawHosts.map((entry) => {
    const host = typeof entry === "string" ? entry : entry && entry.host;
    const ports = (typeof entry === "object" && entry && entry.ports) || fallbackPorts;
    if (!validHost(host)) throw new GrantError("invalid-grant", "grants: bad host " + JSON.stringify(host));
    if (!Array.isArray(ports) || ports.length === 0) {
      throw new GrantError(
        "network-ports-required",
        "grants: host " + host + " needs explicit ports; a silent default would grant more than written",
      );
    }
    for (const port of ports) {
      if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new GrantError("invalid-grant", "grants: bad port " + JSON.stringify(port) + " for " + host);
      }
    }
    return { host: String(host).toLowerCase().replace(/\.$/, ""), ports: [...new Set(ports)].sort((a, b) => a - b) };
  });
}

export function normalizeGrants(raw = {}, { root = process.cwd() } = {}) {
  if (raw == null) raw = {};
  if (typeof raw !== "object" || Array.isArray(raw)) {
    throw new GrantError("invalid-grant", "grants: an object is required");
  }
  const read = normalizeRoots(raw.read !== undefined ? raw.read : raw.paths && raw.paths.read, "read", root);
  const write = normalizeRoots(raw.write !== undefined ? raw.write : raw.paths && raw.paths.write, "write", root);
  const commands = [...new Set(toList(raw.commands !== undefined ? raw.commands : raw.exec, "commands"))];

  const network = raw.network || {};
  const hosts = normalizeHosts(
    network.hosts !== undefined ? network.hosts : raw.hosts,
    network.ports !== undefined ? network.ports : raw.ports,
  );

  const spendRaw = raw.spend && raw.spend.maxUsd !== undefined ? raw.spend.maxUsd : raw.maxSpendUsd;
  const maxSpendUsd = spendRaw == null ? null : Number(spendRaw);
  if (maxSpendUsd !== null && (!Number.isFinite(maxSpendUsd) || maxSpendUsd < 0)) {
    throw new GrantError("invalid-grant", "grants: maxSpendUsd must be a non-negative number");
  }

  const wallRaw = raw.wall && raw.wall.maxMs !== undefined ? raw.wall.maxMs : raw.maxWallMs;
  const maxWallMs = wallRaw == null ? null : Number(wallRaw);
  if (maxWallMs !== null && (!Number.isFinite(maxWallMs) || maxWallMs <= 0)) {
    throw new GrantError("invalid-grant", "grants: maxWallMs must be a positive number");
  }

  return { read, write, commands, hosts, maxSpendUsd, maxWallMs };
}

export function resolveProgram(name, { root = process.cwd(), env = process.env } = {}) {
  if (!isText(name)) return null;
  const hasSeparator = name.includes("/") || name.includes("\\");
  if (hasSeparator) {
    const candidate = path.isAbsolute(name) ? name : path.resolve(root, name);
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return realpathLoose(candidate);
    } catch {
      return null;
    }
  }
  const exts = process.platform === "win32" ? (env.PATHEXT || ".EXE;.CMD;.BAT;.COM").split(";") : [""];
  for (const dir of String(env.PATH || "").split(path.delimiter)) {
    if (!dir) continue;
    for (const ext of exts) {
      const candidate = path.join(dir, name + ext);
      try {
        fs.accessSync(candidate, fs.constants.X_OK);
        return realpathLoose(candidate);
      } catch {
        // keep looking
      }
    }
  }
  return null;
}

export function checkPath(grants, mode, target, { root = process.cwd() } = {}) {
  if (mode !== "read" && mode !== "write") {
    throw new GrantError("bad-path-mode", "grants: path mode must be read or write");
  }
  if (!isText(target)) throw new GrantError("path-required", "grants: a path is required");
  const allowed = (grants && grants[mode]) || [];
  const resolved = realpathLoose(path.resolve(root, target));
  if (allowed.length === 0) {
    return { ok: false, code: "path-not-granted", mode, target: resolved };
  }
  for (const granted of allowed) {
    if (resolved === granted || insideRoot(granted, resolved)) {
      return { ok: true, code: null, mode, target: resolved, root: granted };
    }
  }
  return { ok: false, code: "path-outside-grant", mode, target: resolved, roots: allowed };
}

export function checkCommand(grants, argv, { root = process.cwd(), env = process.env } = {}) {
  // argv[0] is the program and must be named. Later arguments may legitimately be empty
  // (for example `node -e ""`), so only their type is constrained.
  if (!Array.isArray(argv) || argv.length === 0 || !isText(argv[0]) || !argv.every((part) => typeof part === "string")) {
    throw new GrantError("command-required", "grants: argv must be a non-empty array with a named program");
  }
  const allowed = (grants && grants.commands) || [];
  if (allowed.length === 0) {
    return { ok: false, code: "command-not-granted", program: argv[0] };
  }
  const program = resolveProgram(argv[0], { root, env });
  if (!program) return { ok: false, code: "command-not-found", program: argv[0] };
  for (const entry of allowed) {
    const resolved = resolveProgram(entry, { root, env });
    if (resolved && resolved === program) return { ok: true, code: null, program };
  }
  return { ok: false, code: "command-not-granted", program, allowed };
}

export function checkNetwork(grants, { host, port } = {}) {
  if (!validHost(host)) throw new GrantError("host-required", "grants: a host is required");
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new GrantError("port-required", "grants: port must be an integer in 1..65535");
  }
  const allowed = (grants && grants.hosts) || [];
  if (allowed.length === 0) return { ok: false, code: "network-not-granted", host, port };
  const name = String(host).toLowerCase().replace(/\.$/, "");
  for (const entry of allowed) {
    const hostOk = entry.host.startsWith("*.")
      ? name.endsWith(entry.host.slice(1)) && name.length > entry.host.length - 1
      : name === entry.host;
    if (hostOk && entry.ports.includes(port)) {
      return { ok: true, code: null, host: name, port };
    }
  }
  return { ok: false, code: "network-outside-grant", host: name, port, allowed };
}

export function checkSpend(grants, { usd, spentUsd = 0 } = {}) {
  const amount = Number(usd);
  const spent = Number(spentUsd);
  if (!Number.isFinite(amount) || amount < 0) {
    throw new GrantError("spend-invalid", "grants: usd must be a non-negative number");
  }
  if (!Number.isFinite(spent) || spent < 0) {
    throw new GrantError("spend-invalid", "grants: spentUsd must be a non-negative number");
  }
  if (amount === 0) return { ok: true, code: null, usd: 0, spentUsd: spent };
  const cap = grants ? grants.maxSpendUsd : null;
  if (cap == null) return { ok: false, code: "spend-not-granted", usd: amount };
  if (spent + amount > cap + 1e-9) {
    return { ok: false, code: "spend-cap", usd: amount, spentUsd: spent, capUsd: cap };
  }
  return { ok: true, code: null, usd: amount, spentUsd: spent, capUsd: cap };
}

export function checkWall(grants, { elapsedMs } = {}) {
  const elapsed = Number(elapsedMs);
  if (!Number.isFinite(elapsed) || elapsed < 0) {
    throw new GrantError("wall-invalid", "grants: elapsedMs must be a non-negative number");
  }
  const cap = grants ? grants.maxWallMs : null;
  if (cap == null) return { ok: false, code: "wall-not-granted", elapsedMs: elapsed };
  if (elapsed > cap) return { ok: false, code: "wall-cap", elapsedMs: elapsed, capMs: cap };
  return { ok: true, code: null, elapsedMs: elapsed, capMs: cap };
}

// One entry point for the runtime. It returns a verdict and never does the action itself.
export function assertGranted(grants, request = {}) {
  if (!request || typeof request !== "object" || !isText(request.kind)) {
    throw new GrantError("grant-request-invalid", "grants: request.kind is required");
  }
  let verdict;
  switch (request.kind) {
    case "read":
    case "write":
      verdict = checkPath(grants, request.kind, request.path, { root: request.root });
      break;
    case "exec":
      verdict = checkCommand(grants, request.argv, { root: request.root, env: request.env });
      break;
    case "network":
      verdict = checkNetwork(grants, { host: request.host, port: request.port });
      break;
    case "spend":
      verdict = checkSpend(grants, { usd: request.usd, spentUsd: request.spentUsd });
      break;
    case "wall":
      verdict = checkWall(grants, { elapsedMs: request.elapsedMs });
      break;
    default:
      throw new GrantError("unknown-grant-kind", "grants: unknown request kind " + JSON.stringify(request.kind));
  }
  if (!verdict.ok) {
    throw new GrantError(verdict.code, "grant refused: " + verdict.code + " for " + request.kind, verdict);
  }
  return verdict;
}

function coveredRoot(baseRoots, target) {
  return baseRoots.some((root) => target === root || insideRoot(root, target));
}

function commandCovered(baseCommands, entry, options) {
  if (baseCommands.includes(entry)) return true;
  const resolved = resolveProgram(entry, options);
  if (!resolved) return false;
  return baseCommands.some((base) => resolveProgram(base, options) === resolved);
}

function hostCovered(baseHosts, entry) {
  return baseHosts.some((base) => {
    if (!entry.ports.every((port) => base.ports.includes(port))) return false;
    if (base.host === entry.host) return true;
    if (base.host.startsWith("*.")) {
      const suffix = base.host.slice(1);
      if (entry.host.startsWith("*.")) return entry.host.slice(1).endsWith(suffix);
      return entry.host.endsWith(suffix) && entry.host.length > suffix.length;
    }
    return false;
  });
}

// The child's grant may only shrink the parent's. An omitted category inherits; a category
// present in the request is checked entry by entry, and a widening request throws.
export function narrowGrants(base, requested = {}, { root = process.cwd(), env = process.env } = {}) {
  const parent = normalizeGrants(base, { root });
  const raw = requested == null ? {} : requested;
  if (typeof raw !== "object" || Array.isArray(raw)) {
    throw new GrantError("invalid-grant", "grants: narrowing request must be an object");
  }
  const child = normalizeGrants(raw, { root });

  const readAsked = raw.read !== undefined || (raw.paths && raw.paths.read !== undefined);
  const writeAsked = raw.write !== undefined || (raw.paths && raw.paths.write !== undefined);
  const commandsAsked = raw.commands !== undefined || raw.exec !== undefined;
  const hostsAsked = raw.hosts !== undefined || (raw.network && raw.network.hosts !== undefined);
  const spendAsked = raw.maxSpendUsd !== undefined || (raw.spend && raw.spend.maxUsd !== undefined);
  const wallAsked = raw.maxWallMs !== undefined || (raw.wall && raw.wall.maxMs !== undefined);

  for (const target of readAsked ? child.read : []) {
    if (!coveredRoot(parent.read, target)) {
      throw new GrantError("grant-widening", "grants: read root " + target + " is outside the parent grant");
    }
  }
  for (const target of writeAsked ? child.write : []) {
    if (!coveredRoot(parent.write, target)) {
      throw new GrantError("grant-widening", "grants: write root " + target + " is outside the parent grant");
    }
  }
  for (const entry of commandsAsked ? child.commands : []) {
    if (!commandCovered(parent.commands, entry, { root, env })) {
      throw new GrantError("grant-widening", "grants: command " + entry + " is outside the parent grant");
    }
  }
  for (const entry of hostsAsked ? child.hosts : []) {
    if (!hostCovered(parent.hosts, entry)) {
      throw new GrantError("grant-widening", "grants: host " + entry.host + " is outside the parent grant");
    }
  }
  if (spendAsked && child.maxSpendUsd != null) {
    if (parent.maxSpendUsd == null) {
      throw new GrantError("grant-widening", "grants: the parent has no spend grant; the child cannot create one");
    }
    if (child.maxSpendUsd > parent.maxSpendUsd) {
      throw new GrantError("grant-widening", "grants: child spend cap exceeds the parent");
    }
  }
  if (wallAsked && child.maxWallMs != null) {
    if (parent.maxWallMs == null) {
      throw new GrantError("grant-widening", "grants: the parent has no wall grant; the child cannot create one");
    }
    if (child.maxWallMs > parent.maxWallMs) {
      throw new GrantError("grant-widening", "grants: child wall cap exceeds the parent");
    }
  }

  return normalizeGrants(
    {
      read: readAsked ? child.read : parent.read,
      write: writeAsked ? child.write : parent.write,
      commands: commandsAsked ? child.commands : parent.commands,
      hosts: hostsAsked ? child.hosts : parent.hosts,
      maxSpendUsd: spendAsked ? child.maxSpendUsd : parent.maxSpendUsd,
      maxWallMs: wallAsked ? child.maxWallMs : parent.maxWallMs,
    },
    { root },
  );
}

export function grantDigest(grants) {
  return crypto.createHash("sha256").update(JSON.stringify(grants)).digest("hex").slice(0, 16);
}

export function loadGrants(file, options = {}) {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    throw new GrantError("grants-unreadable", "grants: cannot read " + file + ": " + err.message);
  }
  return normalizeGrants(raw, options);
}

export function saveGrants(file, grants, options = {}) {
  const normalized = normalizeGrants(grants, options);
  writeFileLoud(file, JSON.stringify(normalized, null, 2) + "\n");
  return normalized;
}

// The guarded tools are the enforcement point, not a convention. Each one checks the grant
// BEFORE the filesystem or the process is touched, so a refusal leaves no partial artifact
// and no orphan command. A nonzero exit is returned as a result; only a grant refusal throws.
export function guardedWrite(grants, file, data, { root = process.cwd(), fsImpl = fs } = {}) {
  assertGranted(grants, { kind: "write", path: file, root });
  return writeFileLoud(file, data, { fsImpl });
}

export function guardedAppend(grants, file, text, { root = process.cwd(), fsImpl = fs } = {}) {
  assertGranted(grants, { kind: "write", path: file, root });
  return appendLoud(file, text, { fsImpl });
}

export function guardedExec(grants, argv, options = {}) {
  const root = options.root || process.cwd();
  const env = options.env || process.env;
  assertGranted(grants, { kind: "exec", argv, root, env });
  const result = spawnSync(argv[0], argv.slice(1), {
    cwd: options.cwd || root,
    env,
    timeout: options.timeoutMs == null ? 120000 : options.timeoutMs,
    encoding: "utf8",
    maxBuffer: options.maxBuffer == null ? 8 * 1024 * 1024 : options.maxBuffer,
  });
  let exit;
  if (result.error && result.error.code === "ETIMEDOUT") exit = 124;
  else if (result.error) exit = 127;
  else exit = result.status == null ? 1 : result.status;
  return {
    argv,
    exit,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    signal: result.signal || null,
  };
}
