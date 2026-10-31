// Model adapter for the Meta Trio assessment server (Rowan's lane).
//
// SPARK RULE (Del's ruling, 2026-10-28): no live model calls until the
// whole stack is built out and Del green-lights the test phase. This
// adapter is the single place a model call would ever leave the server,
// and it is wired so that cannot happen early:
//
//   1. Unless ASSESS_LIVE_MODEL=1 is set in the server environment, every
//      call is refused as "held" — even if a key is present.
//   2. With the gate open but no key, the call is refused as
//      "not_configured". The key slot is the SPARK_API_KEY environment
//      variable, server-side only; it is never read from a request, never
//      logged, and never committed.
//   3. With the gate open and a key present, the Spark transport runs:
//      POST https://api.meta.ai/v1/chat/completions, model muse-spark-1.3,
//      OpenAI-style content parts (text prompt plus an image_url carrying
//      the JPEG as a data URL). That exact shape was verified against the
//      real API by Pax after Del's test-phase green light (2026-10-30
//      00:23 EDT); the key travels only in the Authorization header.
//      Del puts SPARK_API_KEY in the server environment on the Mac
//      himself — it is never sent over the bus or committed.
//
//   4. Every direct call — including one made after server/assess.mjs
//      falls back from a failed queue attempt — passes the shared
//      spend guardrail first (server/budget.mjs, the Node mirror of
//      server/queue/spark_guardrail.py, same $75 ledger). The budget
//      is checked before the call and recorded after it; a reached
//      cap or an unreadable ledger fails closed with a ModelError
//      and no call is sent.
//
// In every state this adapter either returns a real model response or
// throws a typed ModelError. It never fabricates an assessment. Tests
// inject a stub fetch via deps; no test ever fires a live call.

import { PRODUCTS, PRODUCT_BY_ID } from "../js/products.js";
import { checkBudget, recordBudgetCall } from "./budget.mjs";

export class ModelError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ModelError";
    this.code = code; // "held" | "not_configured" | "model_call_failed"
  }
}

// Verified Spark transport shape (Pax, 2026-10-30, after Del's
// test-phase green light). Hardcoded, not guessed: the endpoint and the
// model id are the ones that answered the real smoke call.
export const SPARK_ENDPOINT = "https://api.meta.ai/v1/chat/completions";
export const SPARK_MODEL = "muse-spark-1.3";

// Per-product prompt profiles, derived from the shared product config
// (js/products.js) so the server and the clients can never drift on
// categories. The live transport consumes these in the test phase.
export const PRODUCT_PROFILES = Object.fromEntries(
  PRODUCTS.map((p) => [
    p.id,
    {
      product: p.id,
      display_name: p.displayName,
      department: p.department,
      categories: [...p.categories],
      limitations: p.limitations,
    },
  ]),
);

export function modelConfig(env = process.env) {
  return {
    keyPresent: typeof env.SPARK_API_KEY === "string" && env.SPARK_API_KEY.length > 0,
    liveEnabled: env.ASSESS_LIVE_MODEL === "1",
  };
}

export function modelStatus(env = process.env) {
  const cfg = modelConfig(env);
  return { configured: cfg.keyPresent, live_enabled: cfg.liveEnabled };
}

// Prompt for one product profile. The model must echo the request's
// product and timestamp exactly, pick assessment.category from the
// profile's own categories, and return JSON only; assess.mjs then
// validates whatever comes back against js/schema.js before it is sent,
// so an off-contract reply becomes a 502, never a passed-through answer.
export function buildSparkPrompt(profile, input) {
  const categories = profile.categories.join(", ");
  return [
    `You are the visual assessment model for ${profile.displayName} (${profile.department}).`,
    "Look at the attached image and return JSON ONLY, no prose, no markdown fences, matching this shape exactly:",
    "{",
    `  "product": "${input.product}",`,
    `  "timestamp": "${input.timestamp}",`,
    '  "observations": [{"category": "<one of the categories below>", "description": "<what is visible>", "evidence": "<where in the frame>", "confidence": <0..1 or null>}],',
    '  "assessment": {"category": "<one of the categories below>", "summary": "<one or two sentences>", "uncertainty": ["<anything unclear>"], "requires_human_review": <true|false>},',
    `  "processing": {"model": "${SPARK_MODEL}", "latency_ms": null}`,
    "}",
    `Categories (assessment.category and every observation category must be one of these): ${categories}.`,
    `Limits: ${profile.limitations}`,
    "Describe only what is visible in the image. This is supplementary awareness only: never dispatch, never claim certainty beyond what is visible. When unsure, use indeterminate and set requires_human_review to true.",
  ].join("\n");
}

// Message content from an OpenAI-style chat response: a string, or an
// array of parts whose text parts join. Anything else carries no content.
function messageContent(data) {
  const content = data && data.choices && data.choices[0] && data.choices[0].message
    ? data.choices[0].message.content
    : undefined;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((part) => part && part.type === "text" && typeof part.text === "string")
      .map((part) => part.text)
      .join("");
  }
  return undefined;
}

// Tolerate the two harmless wrappers models add around JSON — a
// ```json fence, and prose around the object — without ever guessing at
// the object itself: the brace slice is the model's own JSON, and a
// parse failure still throws instead of inventing a value.
function extractJson(content) {
  let text = content.trim();
  if (text.startsWith("```")) {
    const lines = text.split("\n");
    lines.shift();
    text = lines.join("\n").trim();
    if (text.endsWith("```")) text = text.slice(0, -3).trim();
  }
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start !== -1 && end !== -1 && end > start) text = text.slice(start, end + 1);
  return text;
}

// input: { product, timestamp, imageBytes (Buffer), mediaType }
// deps.fetch injects the transport for tests (production uses the
// global fetch). Returns a v2-contract assessment object from the real
// model, or throws ModelError. See the header for the refusal states.
export async function assessWithModel(input, env = process.env, deps = {}) {
  const profile = PRODUCT_BY_ID[input.product];
  if (!profile) {
    throw new ModelError("model_call_failed", `No prompt profile for product "${input.product}".`);
  }
  const cfg = modelConfig(env);
  if (!cfg.liveEnabled) {
    throw new ModelError(
      "held",
      "Live model calls are held: Spark stays off until the build is complete and Del green-lights the test phase.",
    );
  }
  if (!cfg.keyPresent) {
    throw new ModelError(
      "not_configured",
      "No model API key is configured on the server. Set SPARK_API_KEY in the server environment.",
    );
  }
  // Spend guardrail, checked before ANY direct Spark call on this
  // path. deps.budgetPath overrides the ledger location (tests);
  // undefined uses the shared default — the same file the Python
  // queue guardrail counts in.
  const budgetPath = deps.budgetPath;
  try {
    checkBudget(budgetPath);
  } catch (err) {
    throw new ModelError("model_call_failed", err && err.message ? err.message : String(err));
  }
  const fetchFn = deps.fetch ?? globalThis.fetch;
  if (typeof fetchFn !== "function") {
    throw new ModelError("model_call_failed", "No fetch implementation is available for the Spark transport.");
  }
  let imageBytes;
  try {
    imageBytes = Buffer.from(input.imageBytes);
  } catch {
    throw new ModelError("model_call_failed", "No image bytes were supplied for the Spark transport.");
  }
  if (imageBytes.length === 0) {
    throw new ModelError("model_call_failed", "No image bytes were supplied for the Spark transport.");
  }
  const imageUrl = `data:image/jpeg;base64,${imageBytes.toString("base64")}`;
  const startedAt = Date.now();
  let res;
  try {
    res = await fetchFn(SPARK_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.SPARK_API_KEY}`,
      },
      body: JSON.stringify({
        model: SPARK_MODEL,
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: buildSparkPrompt(profile, input) },
              { type: "image_url", image_url: { url: imageUrl } },
            ],
          },
        ],
      }),
      signal: AbortSignal.timeout(60000),
    });
  } catch (err) {
    if (err instanceof ModelError) throw err;
    throw new ModelError(
      "model_call_failed",
      `Spark request failed: ${err && err.message ? err.message : String(err)}`,
    );
  }
  if (!res.ok) {
    throw new ModelError("model_call_failed", `Spark request failed with HTTP ${res.status}.`);
  }
  let data;
  try {
    data = await res.json();
  } catch {
    throw new ModelError("model_call_failed", "Spark response was not JSON.");
  }
  // The call completed and is billable: count it in the shared
  // guardrail ledger, mirroring spark_gen.py, which records on
  // payload receipt, before content checks. A ledger that cannot
  // be written fails the request rather than letting spend go
  // uncounted.
  try {
    recordBudgetCall(
      `assess:${input.product}`,
      data && data.model ? data.model : SPARK_MODEL,
      data ? data.usage : undefined,
      Date.now() - startedAt,
      budgetPath,
    );
  } catch (err) {
    throw new ModelError(
      "model_call_failed",
      `Budget ledger record failed: ${err && err.message ? err.message : String(err)}`,
    );
  }
  const content = messageContent(data);
  if (typeof content !== "string" || content.trim().length === 0) {
    throw new ModelError("model_call_failed", "Spark response carried no message content.");
  }
  let parsed;
  try {
    parsed = JSON.parse(extractJson(content));
  } catch {
    throw new ModelError("model_call_failed", "Spark response content was not JSON.");
  }
  return parsed;
}
