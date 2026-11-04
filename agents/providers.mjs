// agents/providers.mjs — R2-T3 Section C: provider/key/budget logic.
//
// One inventory for every model provider the runtime supports, the exact
// key env name for each, spend caps in provider-billed units (USD), and a
// stub transport for tests. This module never prints a key value: errors
// and logs name the key and the env file path, never the value.
//
// Key sources (task 48): the process environment first, then the machine
// env file (default /etc/metaos/agent.env, root 0600 in the image; tests
// pass a FAKE file in /tmp — never the real path).
//
// Real-call policy: a missing key refuses BEFORE any network call, naming
// the path and the key (task 49). The --probe entry point below makes one
// minimal real call ONLY with an explicit --spend flag; without it the
// probe refuses and touches no network (tasks 57-58). CI mode (CI=1)
// forces the stub and the stub transport throws on non-localhost (task 61).

import fs from "node:fs";
import path from "node:path";
import url from "node:url";

export const AGENT_ENV_PATH = "/etc/metaos/agent.env";

// Demo caps (tasks 50-51, 62). The outer $75 hard stop in
// server/queue/spark_guardrail.py is unchanged; these stricter caps bound
// one job and one day of demo work so the three demo jobs total under $1.
export const DEFAULT_JOB_CAP_USD = 0.25;
export const DEFAULT_DAY_CAP_USD = 1.0;
export const PROBE_TIMEOUT_MS = 90000;

// Task 47 — every provider the runtime supports, and the exact key env
// name for each. All Meta models bill to one account, so every entry
// names the same key: SPARK_API_KEY. METAOS_NOTIFY_WEBHOOK is NOT a model
// provider (optional relay webhook; empty means journal-only) and is
// listed here only to stop anyone from wiring a model call to it.
export const PROVIDERS = {
  "muse-spark-1.3": {
    keyEnv: "SPARK_API_KEY",
    surface: "POST /v1/chat/completions",
    role: "reasoning + vision assessment (production assess path)",
    usdRate: { inPerM: 1.25, outPerM: 4.25 },
    callable: true,
  },
  "muse-wonder-1.0": {
    keyEnv: "SPARK_API_KEY",
    surface: "POST /v1/chat/completions",
    role: "multimodal second reader",
    usdRate: null, // no published USD rate exposed by the provider
    callable: true,
  },
  "sam-3.1": {
    keyEnv: "SPARK_API_KEY",
    surface: "POST /v1/responses",
    role: "image segmentation (box + encoded mask)",
    usdRate: null, // bills images_processed, no USD/token rate published
    callable: true,
  },
  "muse-image-1.0": {
    keyEnv: "SPARK_API_KEY",
    surface: "POST /v1/responses",
    role: "image generation (base64 image_generation_call)",
    usdRate: null, // no published USD rate exposed by the provider
    callable: true,
  },
  "muse-voice-transcribe-1.0": {
    keyEnv: "SPARK_API_KEY",
    surface: null, // NOT RESOLVED (probed 2026-11-02: 404 / model_not_found)
    role: "speech transcription — listed on the account, no verified surface",
    usdRate: null,
    callable: false,
  },
};

export function providerList() {
  return Object.entries(PROVIDERS).map(([id, p]) => ({
    id,
    keyEnv: p.keyEnv,
    surface: p.surface,
    role: p.role,
    usdBilled: p.usdRate !== null,
    callable: p.callable,
  }));
}

// -- errors (named, never carrying a key value) ---------------------------

export class MissingKeyError extends Error {
  constructor(keyEnv, envPath) {
    super(
      `missing key: ${keyEnv} is not set (env or ${envPath}); ` +
        `no model call sent. Fill ${envPath} (root 0600) or export ${keyEnv}.`,
    );
    this.name = "MissingKeyError";
    this.code = "NO_KEY";
    this.keyEnv = keyEnv;
    this.envPath = envPath;
  }
}

export class BudgetError extends Error {
  constructor(message, code) {
    super(message);
    this.name = "BudgetError";
    this.code = code;
  }
}

export class ModelTimeoutError extends Error {
  constructor(timeoutMs) {
    super(`model call timed out after ${timeoutMs}ms (MODEL_TIMEOUT)`);
    this.name = "ModelTimeoutError";
    this.code = "MODEL_TIMEOUT";
    this.timeoutMs = timeoutMs;
  }
}

export class ProviderError extends Error {
  constructor(message, { status = null, code = "PROVIDER_ERROR" } = {}) {
    super(message);
    this.name = "ProviderError";
    this.code = code;
    this.status = status;
  }
}

export class EndpointUnresolvedError extends Error {
  constructor(providerId) {
    super(
      `${providerId} has no verified call surface; refusing to guess ` +
        `(ENDPOINT_UNRESOLVED).`,
    );
    this.name = "EndpointUnresolvedError";
    this.code = "ENDPOINT_UNRESOLVED";
  }
}

// -- key loading (task 48) -------------------------------------------------

export function envFileMode(filePath) {
  try {
    const st = fs.statSync(filePath);
    return (st.mode & 0o777).toString(8);
  } catch {
    return null;
  }
}

// Parse KEY=VALUE lines; ignore blanks and # comments; strip one layer of
// matching quotes. Returns { path, mode, values }. Never logs values.
export function loadAgentEnvFile(filePath = AGENT_ENV_PATH) {
  let text;
  try {
    text = fs.readFileSync(filePath, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") {
      return { path: filePath, mode: null, values: {}, missing: true };
    }
    throw error;
  }
  const values = {};
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const eq = t.indexOf("=");
    if (eq === -1) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    if (v.length >= 2 && ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))) {
      v = v.slice(1, -1);
    }
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(k)) values[k] = v;
  }
  return { path: filePath, mode: envFileMode(filePath), values, missing: false };
}

export function getKey(keyEnv, { env = process.env, fileValues = {} } = {}) {
  const fromEnv = typeof env[keyEnv] === "string" ? env[keyEnv].trim() : "";
  if (fromEnv) return { value: fromEnv, source: "env" };
  const fromFile = typeof fileValues[keyEnv] === "string" ? fileValues[keyEnv].trim() : "";
  if (fromFile) return { value: fromFile, source: "file" };
  return { value: "", source: "none" };
}

// Resolve a provider to its key WITHOUT touching the network (task 49).
// Throws MissingKeyError (names path + key) or EndpointUnresolvedError.
export function resolveProvider(providerId, { env = process.env, envFile = AGENT_ENV_PATH, fileValues = null } = {}) {
  const spec = PROVIDERS[providerId];
  if (!spec) {
    throw new ProviderError(`unknown provider: ${providerId} (UNKNOWN_PROVIDER)`, {
      code: "UNKNOWN_PROVIDER",
    });
  }
  if (!spec.callable || !spec.surface) throw new EndpointUnresolvedError(providerId);
  const fv = fileValues !== null ? fileValues : loadAgentEnvFile(envFile).values;
  const found = getKey(spec.keyEnv, { env, fileValues: fv });
  if (!found.value) throw new MissingKeyError(spec.keyEnv, envFile);
  return {
    id: providerId,
    keyEnv: spec.keyEnv,
    envPath: envFile,
    keySource: found.source, // "env" or "file" — never the value
    surface: spec.surface,
    endpoint:
      spec.surface === "POST /v1/chat/completions"
        ? "https://api.meta.ai/v1/chat/completions"
        : "https://api.meta.ai/v1/responses",
  };
}

// -- budgets (tasks 50-51) -------------------------------------------------
// All caps are USD — the unit the provider bills Spark in ($/M tokens).
// Models with no published USD rate cannot be preflighted (task 52); their
// live calls still count against the caps at their estimated USD (Spark
// rate) when recorded, or at 0 with unknown:true when no rate applies.

export function assertBudget({
  jobBudgetUsd,
  jobCapUsd = DEFAULT_JOB_CAP_USD,
  daySpentUsd = 0,
  dayCapUsd = DEFAULT_DAY_CAP_USD,
} = {}) {
  if (typeof jobBudgetUsd !== "number" || !(jobBudgetUsd > 0)) {
    throw new BudgetError(
      `refused: job budget ${String(jobBudgetUsd)} is not above zero ` +
        `(BUDGET_ZERO; per-job cap $${jobCapUsd.toFixed(2)} USD)`,
      "BUDGET_ZERO",
    );
  }
  if (jobBudgetUsd > jobCapUsd) {
    throw new BudgetError(
      `refused: job budget $${jobBudgetUsd.toFixed(4)} exceeds the per-job cap ` +
        `$${jobCapUsd.toFixed(2)} USD (OVER_JOB_CAP)`,
      "OVER_JOB_CAP",
    );
  }
  if (daySpentUsd + jobBudgetUsd > dayCapUsd) {
    throw new BudgetError(
      `refused: $${daySpentUsd.toFixed(4)} spent + $${jobBudgetUsd.toFixed(4)} ` +
        `would exceed the daily cap $${dayCapUsd.toFixed(2)} USD (OVER_DAY_CAP)`,
      "OVER_DAY_CAP",
    );
  }
  return { ok: true, jobBudgetUsd, jobCapUsd, daySpentUsd, dayCapUsd };
}

// Durable per-day ledger: { date: "YYYY-MM-DD", spentUsd, calls }.
export function readDaySpend(statePath, today = new Date().toISOString().slice(0, 10)) {
  try {
    const data = JSON.parse(fs.readFileSync(statePath, "utf8"));
    if (data && data.date === today) {
      return { date: data.date, spentUsd: Number(data.spentUsd) || 0, calls: Number(data.calls) || 0 };
    }
  } catch { /* missing or corrupt ledger starts the day at zero */ }
  return { date: today, spentUsd: 0, calls: 0 };
}

export function addDaySpend(statePath, usd, today = new Date().toISOString().slice(0, 10)) {
  const cur = readDaySpend(statePath, today);
  const next = {
    date: today,
    spentUsd: Math.round((cur.spentUsd + usd) * 1e6) / 1e6,
    calls: cur.calls + 1,
  };
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(next) + "\n");
  return next;
}

// -- preflight (task 52): estimate ONLY when the provider exposes a rate --

export function estimateCost(providerId, usage) {
  const spec = PROVIDERS[providerId];
  if (!spec) {
    throw new ProviderError(`unknown provider: ${providerId} (UNKNOWN_PROVIDER)`, {
      code: "UNKNOWN_PROVIDER",
    });
  }
  if (!spec.usdRate) {
    return {
      unknown: true,
      usd: null,
      unit: "USD",
      reason: `${providerId} exposes no published USD rate; cost unknown, never invented`,
    };
  }
  const promptTokens = Number(usage?.prompt_tokens ?? usage?.input_tokens ?? 0);
  const completionTokens = Number(usage?.completion_tokens ?? usage?.output_tokens ?? 0);
  const usd =
    (promptTokens / 1e6) * spec.usdRate.inPerM + (completionTokens / 1e6) * spec.usdRate.outPerM;
  return { unknown: false, usd: Math.round(usd * 1e6) / 1e6, unit: "USD", estimated: true };
}

// -- redaction (task 55): names stay, values go -----------------------------

const SECRET_PATTERNS = [
  /\b(sk-|LLM_)[A-Za-z0-9_-]{6,}/g,
  /(Bearer\s+)[A-Za-z0-9._~+/-]{8,}/g,
];

// extraValues: exact planted/known key values to scrub (tests plant one).
// Output carries key NAMES (e.g. SPARK_API_KEY) but never values.
export function redactSecrets(text, extraValues = []) {
  let out = String(text ?? "");
  for (const v of extraValues) {
    if (typeof v === "string" && v.length >= 4) out = out.split(v).join("[REDACTED]");
  }
  out = out.replace(SECRET_PATTERNS[0], "[REDACTED]");
  out = out.replace(SECRET_PATTERNS[1], "$1[REDACTED]");
  return out;
}

// -- timeout (task 53) + retry (task 54) -------------------------------------

export async function callWithTimeout(fn, timeoutMs) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new ModelTimeoutError(timeoutMs)), timeoutMs);
  });
  try {
    return await Promise.race([fn(), timeout]);
  } finally {
    clearTimeout(timer);
  }
}

const TRANSIENT_CODES = new Set(["ECONNRESET", "ETIMEDOUT", "EAI_AGAIN", "ENETUNREACH", "FETCH_FAILED"]);

export function isTransient(error) {
  if (!error || typeof error !== "object") return false;
  if (error.status === 429) return true;
  if (typeof error.status === "number" && error.status >= 500 && error.status < 600) return true;
  if (typeof error.code === "string" && TRANSIENT_CODES.has(error.code)) return true;
  return false;
}

// One retry on a transient network error (2 attempts total), then fail with
// the provider code intact (status/code preserved on the thrown error).
export async function callWithRetry(fn, { retries = 1, isTransientFn = isTransient } = {}) {
  let last;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const result = await fn(attempt);
      return { result, attempts: attempt + 1 };
    } catch (error) {
      last = error;
      if (attempt >= retries || !isTransientFn(error)) throw error;
    }
  }
  throw last;
}

// -- stub provider (task 59): deterministic, no network, ever ---------------

export function stubCall(providerId, prompt = "") {
  const text = String(prompt ?? "");
  // Deterministic: same (provider, prompt) => same text and usage.
  const promptTokens = Math.max(1, Math.ceil(text.length / 4));
  const completionTokens = 16;
  return {
    transport: "stub",
    model: providerId,
    text: `STUB ${providerId} :: prompt-chars=${text.length} :: reply-ok`,
    usage: { prompt_tokens: promptTokens, completion_tokens: completionTokens },
    latencyMs: 0,
  };
}

// Stub transport for tests: throws on anything but loopback (task 61), so a
// test that accidentally aims at the real API fails loudly instead of
// spending. Loopback returns a canned stub payload with no socket use.
export function stubFetch(targetUrl) {
  let host = "";
  try {
    host = new URL(String(targetUrl)).hostname;
  } catch {
    throw new ProviderError(`stub refuses unparseable URL (STUB_NO_NETWORK)`, {
      code: "STUB_NO_NETWORK",
    });
  }
  if (host !== "localhost" && host !== "127.0.0.1" && host !== "::1") {
    throw new ProviderError(
      `stub refuses non-localhost ${host} (STUB_NO_NETWORK): no real network in tests`,
      { code: "STUB_NO_NETWORK" },
    );
  }
  return { stubbed: true, host };
}

// -- transport selection (tasks 60-61) ---------------------------------------

export function isCiMode(env = process.env) {
  return env.CI === "1" || env.CI === "true" || env.METAOS_CI === "1";
}

// Stub is the default when no key exists; the run is labeled `stub`.
// CI mode forces the stub even when a key is present.
export function resolveTransport({ env = process.env, envFile = AGENT_ENV_PATH, fileValues = null } = {}) {
  if (isCiMode(env)) {
    return { mode: "stub", label: "stub", reason: "CI mode forces the stub (CI=1)" };
  }
  const fv = fileValues !== null ? fileValues : loadAgentEnvFile(envFile).values;
  const found = getKey("SPARK_API_KEY", { env, fileValues: fv });
  if (!found.value) {
    return { mode: "stub", label: "stub", reason: `no SPARK_API_KEY (env or ${envFile})` };
  }
  return { mode: "live", label: "live", reason: `SPARK_API_KEY present via ${found.source}` };
}

// -- usage + receipts (task 56) -----------------------------------------------

export function sumUsage(runs) {
  let prompt = 0;
  let completion = 0;
  for (const r of runs || []) {
    const u = r.usage || r;
    prompt += Number(u.prompt_tokens ?? u.input_tokens ?? 0);
    completion += Number(u.completion_tokens ?? u.output_tokens ?? 0);
  }
  return { prompt_tokens: prompt, completion_tokens: completion, calls: (runs || []).length };
}

export function buildReceipt({ kind = "model-call", model, transport = "stub", usage = null, latencyMs = 0 } = {}) {
  const est = model === "muse-spark-1.3" && usage ? estimateCost(model, usage) : null;
  return {
    kind,
    model,
    transport, // "stub" or "live" — every stub run is labeled (task 60)
    usage,
    latency_ms: latencyMs,
    est_cost_usd: est && !est.unknown ? est.usd : null,
  };
}

export function writeReceiptLine(receiptPath, record) {
  fs.mkdirSync(path.dirname(receiptPath), { recursive: true });
  fs.appendFileSync(receiptPath, JSON.stringify(record) + "\n");
  return record;
}

// -- --probe CLI (tasks 57-58) -------------------------------------------------
// Order of gates (both before any network):
//   1. --probe without --spend => refuse (exit 2), no network.
//   2. --probe --spend without a key => missing-key refusal naming path+key
//      (exit 4), no network.
//   3. --probe --spend with a key => one minimal real call (never run in
//      tests; no key on the box, so only paths 1-2 are proven here).

function cliArg(argv, flag) {
  const i = argv.indexOf(flag);
  return i !== -1 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : null;
}

async function probeMain(argv, env) {
  const providerId = cliArg(argv, "--provider") || "muse-spark-1.3";
  const envFile = cliArg(argv, "--env-file") || AGENT_ENV_PATH;
  const timeoutMs = Number(cliArg(argv, "--timeout-ms") || PROBE_TIMEOUT_MS);
  const spend = argv.includes("--spend");

  if (!spend) {
    process.stderr.write(
      "probe refused: --probe makes a real billed call only with an explicit --spend flag.\n" +
        "re-run as: node agents/providers.mjs --probe --spend [--provider ID]\n" +
        "no network touched, no key read.\n",
    );
    return 2;
  }

  // --spend given: the key gate still runs BEFORE any network (task 49).
  let resolved;
  try {
    resolved = resolveProvider(providerId, { env, envFile });
  } catch (error) {
    process.stderr.write(redactSecrets(`probe refused: ${error.message}\n`));
    return error instanceof MissingKeyError || error.code === "NO_KEY" ? 4 : 3;
  }

  const body = {
    model: providerId,
    messages: [{ role: "user", content: "Reply with exactly: PROBEOK" }],
    max_tokens: 16,
    temperature: 0,
  };
  const started = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  // The key value is used here ONLY as the request credential and is never
  // printed, logged, or placed in any output (redactSecrets guards the rest).
  const fileVals = loadAgentEnvFile(envFile).values;
  const credential = getKey(resolved.keyEnv, { env, fileValues: fileVals }).value;
  try {
    const res = await fetch(resolved.endpoint, {
      method: "POST",
      headers: { authorization: "Bearer " + credential, "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const text = await res.text();
    if (!res.ok) {
      process.stderr.write(
        redactSecrets(`probe failed: model HTTP ${res.status}: ${text.slice(0, 200)}\n`),
      );
      return 3;
    }
    process.stdout.write(`probe ok: ${providerId} answered in ${Date.now() - started}ms\n`);
    return 0;
  } catch (error) {
    if (error && error.name === "AbortError") {
      process.stderr.write(`probe failed: ${new ModelTimeoutError(timeoutMs).message}\n`);
      return 3;
    }
    process.stderr.write(redactSecrets(`probe failed: ${error && error.message ? error.message : error}\n`));
    return 3;
  } finally {
    clearTimeout(timer);
  }
}

if (typeof process.argv[1] === "string" && import.meta.url === url.pathToFileURL(process.argv[1]).href) {
  const argv = process.argv.slice(2);
  if (!argv.includes("--probe")) {
    process.stderr.write(
      "usage: node agents/providers.mjs --probe [--spend] [--provider ID] [--env-file PATH] [--timeout-ms N]\n" +
        "providers: " +
        providerList()
          .map((p) => `${p.id} [${p.keyEnv}]`)
          .join(", ") +
        "\n",
    );
    process.exit(2);
  }
  // NOTE: with --spend and a real key this performs one minimal billed
  // request. Nothing in this repo runs that path in tests.
  process.exit(await probeMain(argv, process.env));
}
