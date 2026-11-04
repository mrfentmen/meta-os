// Meta model client — the one place the OS talks to api.meta.ai.
//
// Why this file exists: the relay could spawn processes but nothing in it could
// *think*. Every call here is bounded (tokens, time, cost) and the key is read
// from the environment only, never written to disk or to a log.
//
//   SPARK_API_KEY            required; absent => ModelUnavailable, loud
//   METAOS_MODEL             default muse-spark-1.3
//   METAOS_MODEL_ENDPOINT    default https://api.meta.ai/v1/chat/completions
//
// The model is a reasoning model: a small max_tokens can be eaten entirely by
// reasoning tokens and return content: null. Callers must treat that as a
// failure with a named reason, never as an empty success.

export const DEFAULT_ENDPOINT = "https://api.meta.ai/v1/chat/completions";
// Contributor tier by default (cheaper, same endpoint); METAOS_MODEL overrides.
export const DEFAULT_MODEL = "muse-spark-1.3-contributor";

export class ModelUnavailable extends Error {
  constructor(message) {
    super(message);
    this.name = "ModelUnavailable";
    this.code = "model-unavailable";
  }
}

export class ModelError extends Error {
  constructor(message, { status = null, body = null } = {}) {
    super(message);
    this.name = "ModelError";
    this.code = "model-error";
    this.status = status;
    this.body = body;
  }
}

export function modelConfig(env = process.env) {
  const key = typeof env.SPARK_API_KEY === "string" ? env.SPARK_API_KEY.trim() : "";
  return {
    keyPresent: key.length > 0,
    endpoint: env.METAOS_MODEL_ENDPOINT || DEFAULT_ENDPOINT,
    model: env.METAOS_MODEL || DEFAULT_MODEL,
  };
}

// Prices are a local estimate, not billing. The hackathon key is on a small
// budget, so the loop caps itself on this number and says "estimate" wherever
// it is printed.
export const PRICE = {
  inPerMTok: Number(process.env.METAOS_PRICE_IN_PER_MTOK || 0.25),
  outPerMTok: Number(process.env.METAOS_PRICE_OUT_PER_MTOK || 1.0),
};

export function usageCosts(usage) {
  const promptTokens = Number(usage?.prompt_tokens || 0);
  const completionTokens = Number(usage?.completion_tokens || 0);
  const usd =
    (promptTokens / 1e6) * PRICE.inPerMTok + (completionTokens / 1e6) * PRICE.outPerMTok;
  return { promptTokens, completionTokens, usd: Math.round(usd * 1e6) / 1e6 };
}

/**
 * One bounded chat completion. Returns { content, usage, model, latencyMs }.
 * Throws ModelUnavailable when no key is set, ModelError on transport/HTTP/
 * empty-content, so no caller can mistake a failed call for an empty answer.
 */
export async function chat(messages, opts = {}) {
  const env = opts.env || process.env;
  const cfg = modelConfig(env);
  const key = typeof env.SPARK_API_KEY === "string" ? env.SPARK_API_KEY.trim() : "";
  if (!cfg.keyPresent) {
    throw new ModelUnavailable(
      "SPARK_API_KEY is not set in this environment; the Meta model cannot be called",
    );
  }
  const body = {
    model: opts.model || cfg.model,
    messages,
    // 4000, not 900: muse-spark-1.3 is a reasoning model and bills its
    // internal reasoning against completion tokens. Measured against the live
    // endpoint on 2026-11-04: a one-sentence question burned 380-400 reasoning
    // tokens, so a 900-token cap returned content:null / finish_reason:length
    // and the loop reported "model returned no content" on a perfectly good
    // key. 4000 leaves room for the reasoning plus a real answer.
    max_tokens: opts.maxTokens || 4000,
    temperature: opts.temperature ?? 0,
  };
  if (opts.jsonMode) body.response_format = { type: "json_object" };

  const started = Date.now();
  const attempts = Math.max(1, opts.attempts || 3);
  let res = null;
  let lastTransport = null;
  for (let n = 1; n <= attempts; n += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), opts.timeoutMs || 90000);
    try {
      res = await fetch(opts.endpoint || cfg.endpoint, {
        method: "POST",
        headers: {
          authorization: "Bearer " + key,
          "content-type": "application/json",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (error) {
      lastTransport = error.name === "AbortError" ? "timed out" : error.message;
      res = null;
    } finally {
      clearTimeout(timer);
    }
    // 5xx and transport failures are the backend being briefly unavailable,
    // not the request being wrong: retry those, never a 4xx.
    const retryable = res === null || res.status >= 500 || res.status === 429;
    if (!retryable || n === attempts) break;
    await new Promise((r) => setTimeout(r, 700 * n));
  }
  if (res === null) {
    throw new ModelError("model transport failed after " + attempts + " attempts: " + lastTransport, {
      body: null,
    });
  }

  const text = await res.text();
  if (!res.ok) {
    // The body may quote the key back in an error; strip anything key-shaped.
    const safe = text.slice(0, 300).replace(/(sk-|LLM_)[A-Za-z0-9_-]{6,}/g, "[REDACTED]");
    throw new ModelError("model HTTP " + res.status + ": " + safe, {
      status: res.status,
      body: safe,
    });
  }
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new ModelError("model returned non-JSON envelope", { status: res.status });
  }
  const choice = data?.choices?.[0];
  const content = choice?.message?.content;
  if (typeof content !== "string" || content.trim() === "") {
    const finish = choice?.finish_reason || "unknown";
    throw new ModelError(
      "model returned no content (finish_reason=" + finish + "); raise max_tokens",
      { status: res.status },
    );
  }
  return {
    content,
    usage: data.usage || null,
    model: data.model || body.model,
    latencyMs: Date.now() - started,
  };
}
