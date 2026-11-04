// metaosd_store.mjs — durable file queue for the metaosd agent daemon.
//
// Why a new file instead of reusing server/queue/queue_service.py:
// queue_service.py (with trio_store.py) is the Trio service on :8935. Its
// store is trio-specific: Upstash Redis (or a local SQLite FALLBACK) keyed
// by namespace holding trio-assessment v1 envelopes (base64 JPEG frames
// with byteLength/sha256 verification). It cannot hold generic agent jobs
// {id, agent, input, budget, timeout, dry-run}, it lives behind an HTTP
// shape we must not break, and it is Python while the daemon is node.
// So the daemon persists here: one job file per id, atomic tmp+rename
// writes, under a data dir OUTSIDE the git tree
// ($METAOS_STATE/metaosd, else ~/.local/state/metaos/metaosd).
// Node stdlib only.

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));

export function defaultDataDir() {
  const base = process.env.METAOS_STATE
    ? process.env.METAOS_STATE
    : path.join(os.homedir(), ".local", "state", "metaos");
  return path.join(base, "metaosd");
}

export function schemaPath(checkout) {
  if (process.env.METAOS_CHECKOUT) {
    return path.join(process.env.METAOS_CHECKOUT, "agents", "job.schema.json");
  }
  if (checkout) return path.join(checkout, "agents", "job.schema.json");
  // server/queue/metaosd_store.mjs -> <root>/agents/job.schema.json
  return path.join(HERE, "..", "..", "agents", "job.schema.json");
}

export function loadSchema(file) {
  const f = file || schemaPath();
  let raw;
  try {
    raw = fs.readFileSync(f, "utf8");
  } catch (e) {
    throw new Error("metaosd: job schema not found at " + f);
  }
  return { file: f, schema: JSON.parse(raw) };
}

// Generic subset-validator driven by the schema FILE (single copy:
// field definitions live in agents/job.schema.json, never here).
// Returns { ok, errors[] }; unknown fields are refused BY NAME.
export function validateAgainstSchema(job, schema) {
  const errors = [];
  if (!job || typeof job !== "object" || Array.isArray(job)) {
    return { ok: false, errors: ["job must be a JSON object"] };
  }
  const props = schema.properties || {};
  const required = schema.required || [];
  for (const name of required) {
    if (job[name] === undefined) errors.push("missing required field \"" + name + "\"");
  }
  const allowed = new Set(Object.keys(props));
  // Top-level unknown fields refused by name (task 28).
  for (const key of Object.keys(job)) {
    if (!allowed.has(key)) errors.push("unknown field \"" + key + "\"");
  }
  const checkType = (value, spec, where) => {
    const types = Array.isArray(spec.type) ? spec.type : [spec.type];
    const okType = types.some((t) => {
      if (t === "string") return typeof value === "string";
      if (t === "number") return typeof value === "number" && Number.isFinite(value);
      if (t === "integer") return Number.isInteger(value);
      if (t === "boolean") return typeof value === "boolean";
      if (t === "object") return value !== null && typeof value === "object" && !Array.isArray(value);
      return false;
    });
    if (!okType) errors.push(where + " must be of type " + types.join("/"));
    return okType;
  };
  if (job.id !== undefined) {
    if (checkType(job.id, props.id, "\"id\"") && props.id.pattern) {
      if (!new RegExp(props.id.pattern).test(job.id)) {
        errors.push("\"id\" must match " + props.id.pattern);
      }
    }
  }
  if (job.agent !== undefined) {
    if (checkType(job.agent, props.agent, "\"agent\"") && job.agent.trim() === "") {
      errors.push("\"agent\" must be a non-empty string");
    }
  }
  if (job.input !== undefined) checkType(job.input, props.input, "\"input\"");
  if (job["dry-run"] !== undefined) checkType(job["dry-run"], props["dry-run"], "\"dry-run\"");
  if (job.timeout !== undefined) {
    if (checkType(job.timeout, props.timeout, "\"timeout\"") && job.timeout < 0) {
      errors.push("\"timeout\" must be >= 0");
    }
  }
  if (job.budget !== undefined) {
    const bspec = props.budget || {};
    if (checkType(job.budget, bspec, "\"budget\"")) {
      const bprops = bspec.properties || {};
      const ballowed = new Set(Object.keys(bprops));
      for (const key of Object.keys(job.budget)) {
        if (!ballowed.has(key)) errors.push("unknown budget field \"" + key + "\"");
      }
      for (const [key, spec] of Object.entries(bprops)) {
        const v = job.budget[key];
        if (v === undefined) continue;
        if (!checkType(v, spec, "\"budget." + key + "\"")) continue;
        if (spec.minimum != null && v < spec.minimum) {
          errors.push("\"budget." + key + "\" must be >= " + spec.minimum);
        }
        if (spec.exclusiveMinimum != null && !(v > spec.exclusiveMinimum)) {
          errors.push("\"budget." + key + "\" must be > " + spec.exclusiveMinimum);
        }
      }
    }
  }
  return { ok: errors.length === 0, errors };
}

export function validateJob(job, schemaFile) {
  const { schema } = loadSchema(schemaFile);
  return validateAgainstSchema(job, schema);
}

// ---- durable layout -------------------------------------------------
// <dataDir>/jobs/<id>.json      the run record (one file per job)
// <dataDir>/idem.json           { requestKey: jobId } idempotency map
// <dataDir>/runs/<id>/          per-run dir: output-attemptN.log, receipt.json
// <dataDir>/chain.jsonl         receipt chain (one JSON object per line)
// <dataDir>/receipt.key         HMAC key, 0600, created on first receipt
// <dataDir>/metaosd.lock        daemon lock {pid, startedAt}

export function dataPaths(dataDir) {
  return {
    root: dataDir,
    jobs: path.join(dataDir, "jobs"),
    runs: path.join(dataDir, "runs"),
    idem: path.join(dataDir, "idem.json"),
    chain: path.join(dataDir, "chain.jsonl"),
    key: path.join(dataDir, "receipt.key"),
    lock: path.join(dataDir, "metaosd.lock"),
  };
}

export function ensureDataDir(dataDir) {
  fs.mkdirSync(dataPaths(dataDir).jobs, { recursive: true });
  fs.mkdirSync(dataPaths(dataDir).runs, { recursive: true });
}

// Atomic write: tmp + rename so a kill -9 never leaves half a record.
export function atomicWrite(file, text) {
  const tmp = file + ".tmp-" + process.pid;
  fs.writeFileSync(tmp, text);
  fs.renameSync(tmp, file);
}

export function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

// ---- writable probe (task 45) ----
export function checkWritable(dataDir) {
  try {
    fs.mkdirSync(dataDir, { recursive: true });
    const probe = path.join(dataDir, ".writable-probe-" + process.pid);
    fs.writeFileSync(probe, "ok");
    fs.unlinkSync(probe);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String((e && e.message) || e) };
  }
}

// ---- lock (task 46) ----
function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

export function readLock(dataDir) {
  return readJson(dataPaths(dataDir).lock, null);
}

// On start: a lock whose pid is dead is stale -> remove it and REPORT
// what was removed. A lock whose pid is alive refuses the start.
export function cleanStaleLock(dataDir) {
  const lockFile = dataPaths(dataDir).lock;
  const existing = readLock(dataDir);
  if (!existing) return { removed: null, active: null };
  const pid = Number(existing.pid);
  if (Number.isInteger(pid) && pid > 0 && pidAlive(pid)) {
    return { removed: null, active: existing };
  }
  fs.unlinkSync(lockFile);
  return { removed: { path: lockFile, ...existing }, active: null };
}

export function takeLock(dataDir) {
  const cleaned = cleanStaleLock(dataDir);
  if (cleaned.active) {
    throw new Error("metaosd: already running (pid " + cleaned.active.pid + ")");
  }
  atomicWrite(dataPaths(dataDir).lock, JSON.stringify({
    pid: process.pid,
    startedAt: new Date().toISOString(),
  }) + "\n");
  return cleaned.removed; // null, or the stale lock that was removed (log it)
}

export function releaseLock(dataDir) {
  try {
    const cur = readLock(dataDir);
    if (cur && Number(cur.pid) === process.pid) fs.unlinkSync(dataPaths(dataDir).lock);
  } catch { /* best effort on shutdown */ }
}

// ---- idempotency map (task 34) ----
export function loadIdem(dataDir) {
  return readJson(dataPaths(dataDir).idem, {});
}

export function saveIdem(dataDir, map) {
  atomicWrite(dataPaths(dataDir).idem, JSON.stringify(map, null, 2) + "\n");
}

// ---- job records ----
export function jobFile(dataDir, id) {
  return path.join(dataPaths(dataDir).jobs, id + ".json");
}

export function loadJob(dataDir, id) {
  return readJson(jobFile(dataDir, id), null);
}

export function saveJob(dataDir, record) {
  atomicWrite(jobFile(dataDir, record.id), JSON.stringify(record, null, 2) + "\n");
}

export function listJobs(dataDir) {
  const dir = dataPaths(dataDir).jobs;
  let files = [];
  try {
    files = fs.readdirSync(dir).filter((n) => n.endsWith(".json")).sort();
  } catch {
    return [];
  }
  const out = [];
  for (const f of files) {
    const rec = readJson(path.join(dir, f), null);
    if (rec) out.push(rec);
  }
  return out;
}

// ---- receipt key + HMAC chain (tasks 40-42) ----
// receipts are HMAC-SHA256 over a canonical JSON of the receipt fields
// (minus hmac), chained via prev = previous receipt's hmac.
// receipt_validate.py is NOT suitable here (documented in R2_T3_B.md):
// it validates model-usage JSONL lines (model/surface/latency_ms/
// est_cost_usd with a Spark billing rule), not HMAC-chained job
// receipts, so job receipts carry their own verifier (this module +
// `metaosd.mjs verify[-chain]`).

export function loadOrCreateKey(dataDir) {
  const kf = dataPaths(dataDir).key;
  try {
    const existing = fs.readFileSync(kf, "utf8").trim();
    if (existing) return { key: existing, created: false, path: kf };
  } catch { /* create below */ }
  const fresh = crypto.randomBytes(32).toString("hex");
  fs.writeFileSync(kf, fresh + "\n", { mode: 0o600 });
  try {
    fs.chmodSync(kf, 0o600);
  } catch { /* non-POSIX fs: best effort */ }
  return { key: fresh, created: true, path: kf };
}

export function readKey(dataDir) {
  const kf = dataPaths(dataDir).key;
  try {
    const k = fs.readFileSync(kf, "utf8").trim();
    if (k) return { key: k, path: kf };
  } catch { /* missing */ }
  return { key: null, path: kf };
}

export function canonical(obj) {
  return JSON.stringify(obj, Object.keys(obj).sort());
}

export function receiptHmac(key, receiptFields) {
  return crypto.createHmac("sha256", key).update(canonical(receiptFields)).digest("hex");
}

export function chainPrev(dataDir) {
  const cf = dataPaths(dataDir).chain;
  try {
    const lines = fs.readFileSync(cf, "utf8").split("\n").filter((l) => l.trim());
    if (lines.length === 0) return "GENESIS";
    return JSON.parse(lines[lines.length - 1]).hmac || "GENESIS";
  } catch {
    return "GENESIS";
  }
}

export function appendChain(dataDir, entry) {
  fs.appendFileSync(dataPaths(dataDir).chain, JSON.stringify(entry) + "\n");
}

// Verify one receipt object (fields + .hmac) against key+expected prev.
export function verifyReceiptObject(key, receipt, expectedPrev) {
  if (!receipt || typeof receipt !== "object") return { ok: false, error: "receipt is not an object" };
  const { hmac, ...fields } = receipt;
  if (typeof hmac !== "string" || hmac.length === 0) {
    return { ok: false, error: "receipt has no hmac" };
  }
  if (expectedPrev != null && fields.prev !== expectedPrev) {
    return { ok: false, error: "chain break: prev " + JSON.stringify(fields.prev) + " != " + JSON.stringify(expectedPrev) };
  }
  const want = receiptHmac(key, fields);
  if (!crypto.timingSafeEqual(Buffer.from(want, "utf8"), Buffer.from(String(hmac), "utf8"))) {
    return { ok: false, error: "hmac mismatch: receipt was modified" };
  }
  return { ok: true };
}

// Offline whole-chain verify: reads dataDir/chain.jsonl, needs receipt.key.
export function verifyChain(dataDir) {
  const { key, path: keyPath } = readKey(dataDir);
  if (!key) {
    return { ok: false, error: "no receipt key at " + keyPath + " (refusing to verify without it)" };
  }
  const cf = dataPaths(dataDir).chain;
  let lines = [];
  try {
    lines = fs.readFileSync(cf, "utf8").split("\n").filter((l) => l.trim());
  } catch {
    return { ok: true, checked: 0, note: "no chain file yet" };
  }
  let prev = "GENESIS";
  let checked = 0;
  for (let i = 0; i < lines.length; i++) {
    let entry;
    try {
      entry = JSON.parse(lines[i]);
    } catch {
      return { ok: false, error: "chain line " + (i + 1) + ": not valid JSON" };
    }
    const v = verifyReceiptObject(key, entry, prev);
    if (!v.ok) return { ok: false, error: "chain line " + (i + 1) + ": " + v.error };
    prev = entry.hmac;
    checked++;
  }
  return { ok: true, checked };
}
