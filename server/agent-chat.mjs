// Text conversation with the same model transport the assessment path uses.
//
// The division pages each carry a small console where the operator can ask
// the agent what it is looking at. That is a text call, not an image
// assessment, so it gets its own module instead of bending /api/assess into
// a shape it was not built for.
//
// It obeys the same three rules as server/model.mjs:
//   1. ASSESS_LIVE_MODEL=1 must be set, or the call is refused as "held".
//   2. SPARK_API_KEY must be present, or it is refused as "not_configured".
//   3. The shared budget ledger is checked before the call and written after.
// Nothing here reads a key from a request, logs one, or invents a reply.

import { ModelError, modelConfig } from "./model.mjs";
import { checkBudget, recordBudgetCall } from "./budget.mjs";

export const AGENT_ENDPOINT = "https://api.meta.ai/v1/chat/completions";
export const AGENT_MODEL = "muse-spark-1.3";
export const MAX_QUESTION_CHARS = 2000;

const SYSTEM_PROMPT = [
  "You are the duty agent inside Meta OS, the operating system's own agent layer.",
  "The operator is looking at a live camera board for one division: Vigiles (police), Ignis (fire) or Medicus (EMS).",
  "Answer in at most four sentences of plain text. No markdown, no lists unless asked for one.",
  "Say only what the provided context supports. If the context does not answer the question, say what is missing instead of guessing.",
  "This system is situational awareness only. It never dispatches, never identifies people, and never states a cause of injury or fire.",
].join(" ");

export function validateAsk(payload) {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return { ok: false, error: "request body is not a JSON object" };
  }
  const question = typeof payload.question === "string" ? payload.question.trim() : "";
  if (!question) return { ok: false, error: "question: required and must not be empty" };
  if (question.length > MAX_QUESTION_CHARS) {
    return { ok: false, error: `question: must be at most ${MAX_QUESTION_CHARS} characters` };
  }
  const division = typeof payload.division === "string" ? payload.division.trim().toLowerCase() : "medicus";
  if (!["vigiles", "ignis", "medicus"].includes(division)) {
    return { ok: false, error: 'division: must be "vigiles", "ignis" or "medicus"' };
  }
  const context = typeof payload.context === "string" ? payload.context.slice(0, 4000) : "";
  return { ok: true, value: { question, division, context } };
}

function content(data) {
  const raw = data?.choices?.[0]?.message?.content;
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) {
    return raw.filter((p) => p && p.type === "text" && typeof p.text === "string").map((p) => p.text).join("");
  }
  return undefined;
}

export async function askAgent(payload, env = process.env, deps = {}) {
  const req = validateAsk(payload);
  if (!req.ok) return { status: 400, body: { error: req.error } };

  const cfg = modelConfig(env);
  if (!cfg.keyPresent) {
    return {
      status: 503,
      body: {
        error:
          "No model key is configured on this server. Set SPARK_API_KEY in the service environment and restart.",
        code: "not_configured",
      },
    };
  }
  if (!cfg.liveEnabled) {
    return {
      status: 503,
      body: {
        error:
          "Live model calls are held. Set ASSESS_LIVE_MODEL=1 in the service environment to let this box talk to the model.",
        code: "held",
      },
    };
  }

  try {
    checkBudget(deps.budgetPath);
  } catch (err) {
    return { status: 402, body: { error: err && err.message ? err.message : String(err), code: "budget" } };
  }

  const fetchFn = deps.fetch ?? globalThis.fetch;
  if (typeof fetchFn !== "function") {
    return { status: 500, body: { error: "No fetch implementation available." } };
  }

  const startedAt = Date.now();
  let res;
  try {
    res = await fetchFn(AGENT_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.SPARK_API_KEY}`,
      },
      body: JSON.stringify({
        model: AGENT_MODEL,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          {
            role: "user",
            content:
              `Division: ${req.value.division}.\n` +
              (req.value.context ? `Board context:\n${req.value.context}\n\n` : "") +
              `Question: ${req.value.question}`,
          },
        ],
      }),
      signal: AbortSignal.timeout(45000),
    });
  } catch (err) {
    return {
      status: 502,
      body: { error: `Model request failed: ${err && err.message ? err.message : String(err)}`, code: "model_call_failed" },
    };
  }

  if (!res.ok) {
    return { status: 502, body: { error: `Model request failed with HTTP ${res.status}.`, code: "model_call_failed" } };
  }

  let data;
  try {
    data = await res.json();
  } catch {
    return { status: 502, body: { error: "Model response was not JSON.", code: "model_call_failed" } };
  }

  // Billable from here on, so record before answering, matching model.mjs.
  try {
    recordBudgetCall(
      `agent-chat:${req.value.division}`,
      data?.model ?? AGENT_MODEL,
      data?.usage,
      Date.now() - startedAt,
      deps.budgetPath,
    );
  } catch (err) {
    return {
      status: 502,
      body: {
        error: `Model answered but the spend ledger could not be written: ${err && err.message ? err.message : String(err)}`,
        code: "model_call_failed",
      },
    };
  }

  const reply = content(data);
  if (!reply || !reply.trim()) {
    return { status: 502, body: { error: "Model returned no text.", code: "model_call_failed" } };
  }
  return {
    status: 200,
    body: { reply: reply.trim(), model: data?.model ?? AGENT_MODEL, latency_ms: Date.now() - startedAt },
  };
}

export { ModelError };
