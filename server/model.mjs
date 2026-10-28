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
//   3. With the gate open and a key present, the Spark transport itself
//      is still landed during the test phase (its endpoint shape must be
//      verified against the real API before use), so the call is refused
//      as "transport_not_wired" rather than guessed at.
//
// In every state this adapter either returns a real model response or
// throws a typed ModelError. It never fabricates an assessment.

import { PRODUCTS, PRODUCT_BY_ID } from "../js/products.js";

export class ModelError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ModelError";
    this.code = code; // "held" | "not_configured" | "transport_not_wired" | "model_call_failed"
  }
}

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

// input: { product, timestamp, imageBytes (Buffer), mediaType }
// Returns a v2-contract assessment object from the real model, or throws
// ModelError. See the header for the three refusal states.
export async function assessWithModel(input, env = process.env) {
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
  throw new ModelError(
    "transport_not_wired",
    "The Spark transport is not wired yet; it lands in the test phase, verified against the real API. No assessment was fabricated in its place.",
  );
}
