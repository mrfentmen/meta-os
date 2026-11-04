// The in-app agent chat: one endpoint behind the chat box every app carries.
//
// The box the operator types into is js/agent-chat.js (floating, one per page)
// or the console the three division pages draw inline (trio/agent.js). Both
// POST the same shape here, so a fix in this file is a fix in every app:
//
//   POST /api/agent/ask  { app, question, context? }
//   -> 200 { reply, app, model, latency_ms, spend }
//   -> 4xx/5xx { error, code }
//
// This module used to know only Vigiles, Ignis and Medicus ("division"), which
// is why the chat box existed on three pages out of twelve: every other app
// would have been refused with "division: must be ...". The app id is now the
// unit, each id carries its own persona, and "division" is still accepted so
// the three division pages keep working unchanged.
//
// It obeys the same three rules as server/model.mjs:
//   1. ASSESS_LIVE_MODEL=1 must be set, or the call is refused as "held".
//   2. SPARK_API_KEY must be present, or it is refused as "not_configured".
//   3. The shared budget ledger is checked before the call and written after.
// Nothing here reads a key from a request, logs one, or invents a reply.

import { ModelError, modelConfig } from "./model.mjs";
import { budgetStatus, checkBudget, recordBudgetCall } from "./budget.mjs";

export const AGENT_ENDPOINT = "https://api.meta.ai/v1/chat/completions";
// The contributor variant, not muse-spark-1.3: same API, same shape, cheaper
// per token, and the chat box only ever asks for a short plain-text answer.
// METAOS_CHAT_MODEL overrides it without touching code.
export const AGENT_MODEL = "muse-spark-1.3-contributor";
export const MAX_QUESTION_CHARS = 2000;
export const MAX_CONTEXT_CHARS = 4000;
// muse-spark is a reasoning model: it bills its own thinking against the
// completion budget, and the thinking is the expensive, variable part.
// Measured against the live endpoint on 2026-11-04: a one-sentence answer cost
// 337 reasoning tokens, a 64-token cap returned content:null, and 1200 was
// still not enough for 3 of 14 app questions (each burned 1198 reasoning
// tokens and returned nothing). 3000 covers that spread; the cap only limits
// what is produced, so a short answer still bills short.
export const DEFAULT_MAX_TOKENS = 3000;
export const DEFAULT_TIMEOUT_MS = 45000;

// One persona per app in the dock. `role` says what the app is for; `scope`
// says what the agent may talk about there. Both are claims about this machine
// only — the agent is never told it can act.
export const APP_PROFILES = {
  vigiles: {
    label: "Vigiles",
    role: "The operator is looking at the police camera board: which cameras are watched, and what the assessment model recorded on each frame.",
    scope: "Visual event awareness for a police division. A flag is a reason for a human to look, never a dispatch, and never an identification of a person.",
  },
  ignis: {
    label: "Ignis",
    role: "The operator is looking at the fire division's board: the camera timeline, the frames assessed, and the results on them.",
    scope: "Visible fire and smoke only. A flag is a reason to look, not a report of an incident, and the agent never states a cause.",
  },
  medicus: {
    label: "Medicus",
    role: "The operator is looking at the EMS board: the camera layer, the queued frames, and the scene notes recorded on them.",
    scope: "Scene and casualty awareness. Triage here sorts frames for review, not patients, and the agent never diagnoses.",
  },
  science: {
    label: "Science Lab",
    role: "The operator is in the molecule lab, which draws structures from the local SDF packs beside the page.",
    scope: "Molecules on this machine: atoms, bonds, formulas, and what the loaded file records. Say when a file does not carry the property asked about.",
  },
  musica: {
    label: "Musica",
    role: "The operator is in the music app, which plays the session takes that ship on this machine.",
    scope: "The tracks, sessions and takes on this machine. The agent does not claim to hear audio; it reads what the session records say.",
  },
  officina: {
    label: "Officina",
    role: "The operator is in Officina, the engineering and design system: blueprint pages, dimension callouts and build records.",
    scope: "The figures on the page and the records behind them. Figures are records from the merged tree, not live telemetry.",
  },
  custos: {
    label: "Custos",
    role: "The operator is in Custos, the oversight view: what the agents did, what the queue holds, and what was spent.",
    scope: "Agent records, receipts and spend estimates on this machine. Never present an estimate as a bill.",
  },
  boards: {
    label: "Boards",
    role: "The operator is on the dispatch boards page: the board sections, incidents and the rooms they post into.",
    scope: "What the boards show and which room carries which thread. The agent does not dispatch anyone.",
  },
  aegis: {
    label: "Aegis",
    role: "The operator is in Aegis, the security review surface: sweeps, findings, manifests and secret counts.",
    scope: "Findings that were recorded, with their file and reason. Do not invent a finding and do not call an unproven one confirmed.",
  },
  nervus: {
    label: "Nervus",
    role: "The operator is in Nervus, the machine's service view: ports, trays and which backend answered.",
    scope: "Services on 127.0.0.1, their ports and their health as the page reads them. Say when a port did not answer.",
  },
  messages: {
    label: "Messages",
    role: "The operator is in Messages, the one messaging app: rooms on the Board, and the NOTIFY lines the agents post.",
    scope: "Rooms and lines the Board returns. The agent does not speak as another person and does not send messages.",
  },
  monitor: {
    label: "Monitor",
    role: "The operator is in the monitor, which reads machine facts from the local facts service.",
    scope: "CPU, memory, disk and uptime as the page last read them. Say when the reading is stale.",
  },
  notes: {
    label: "3D Notes",
    role: "The operator is in 3D Notes, the piano-roll lab: sessions rendered as notes over time.",
    scope: "Sessions and notes on this machine as the page draws them. The agent does not claim to hear the take.",
  },
  general: {
    label: "Meta OS",
    role: "The operator is somewhere in Meta OS and the page did not name an app.",
    scope: "The Meta OS applications that ship on this machine. Say plainly when the question needs an app that is not open.",
  },
};

export const APP_IDS = Object.keys(APP_PROFILES);

// The three division pages post { division } instead of { app }. Mapped rather
// than special-cased so one persona table serves both callers.
const DIVISION_TO_APP = { vigiles: "vigiles", ignis: "ignis", medicus: "medicus" };

const SHARED_RULES = [
  "Answer in at most four sentences of plain text. No markdown, no headings, no bullet lists unless the question asks for one.",
  "Say only what the provided context supports. If the context does not answer the question, name what is missing instead of guessing.",
  "You are a read-only assistant: you cannot open apps, move the pointer, change the board, or send anything. Never claim you did.",
  "This is situational awareness inside one machine. Never identify a person, never state a cause of injury or fire, and never present yourself as emergency services.",
].join(" ");

export function profileFor(app) {
  return APP_PROFILES[app] || APP_PROFILES.general;
}

export function systemPromptFor(app) {
  const profile = profileFor(app);
  return [
    `You are the ${profile.label} agent inside Meta OS, the operating system's own agent layer, running on this machine.`,
    profile.role,
    profile.scope,
    SHARED_RULES,
  ].join(" ");
}

export function validateAsk(payload) {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return { ok: false, error: "request body is not a JSON object" };
  }
  const question = typeof payload.question === "string" ? payload.question.trim() : "";
  if (!question) return { ok: false, error: "question: required and must not be empty" };
  if (question.length > MAX_QUESTION_CHARS) {
    return { ok: false, error: `question: must be at most ${MAX_QUESTION_CHARS} characters` };
  }
  // app wins; division is the older name the division pages still send.
  const rawApp = typeof payload.app === "string" ? payload.app.trim().toLowerCase() : "";
  const rawDivision = typeof payload.division === "string" ? payload.division.trim().toLowerCase() : "";
  let app = rawApp || DIVISION_TO_APP[rawDivision] || "";
  if (!app) {
    return {
      ok: false,
      error: `app: required and must be one of ${APP_IDS.join(", ")}`,
    };
  }
  if (!APP_PROFILES[app]) {
    // An unknown id is the general persona, not a 400: a page built later must
    // still get an answer instead of a dead chat box. The id is echoed back so
    // it is obvious which page fell back.
    app = "general";
  }
  const context = typeof payload.context === "string" ? payload.context.slice(0, MAX_CONTEXT_CHARS) : "";
  return { ok: true, value: { question, app, requestedApp: rawApp || rawDivision || null, context } };
}

function content(data) {
  const raw = data?.choices?.[0]?.message?.content;
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) {
    return raw.filter((p) => p && p.type === "text" && typeof p.text === "string").map((p) => p.text).join("");
  }
  return undefined;
}

export function chatModel(env = process.env) {
  const model = typeof env.METAOS_CHAT_MODEL === "string" && env.METAOS_CHAT_MODEL.trim()
    ? env.METAOS_CHAT_MODEL.trim()
    : AGENT_MODEL;
  const configured = Number(env.METAOS_CHAT_MAX_TOKENS);
  const maxTokens = Number.isFinite(configured) && configured > 0 ? Math.min(configured, 8000) : DEFAULT_MAX_TOKENS;
  return { model, maxTokens };
}

// The request shape the model gets. Exported so a test can assert the persona
// and the token cap without firing a call.
export function buildChatBody(value, env = process.env) {
  const { model, maxTokens } = chatModel(env);
  return {
    model,
    messages: [
      { role: "system", content: systemPromptFor(value.app) },
      {
        role: "user",
        content:
          (value.context ? `What this app shows right now:\n${value.context}\n\n` : "") +
          `Question: ${value.question}`,
      },
    ],
    // 0, not a "personality" temperature: this answers from the context it was
    // handed, and a demo wants the same answer twice.
    temperature: 0,
    max_tokens: maxTokens,
  };
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

  const body = buildChatBody(req.value, env);
  const startedAt = Date.now();
  let res;
  try {      res = await fetchFn(chatEndpoint(env), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.SPARK_API_KEY}`,
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(Number(env.METAOS_CHAT_TIMEOUT_MS) || DEFAULT_TIMEOUT_MS),
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
      `agent-chat:${req.value.app}`,
      data?.model ?? body.model,
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
    // The one failure that used to read as a bug in the chat box: a reasoning
    // model that spent the whole budget thinking returns content:null. Name it.
    const finish = data?.choices?.[0]?.finish_reason;
    const reasoning = data?.usage?.completion_tokens_details?.reasoning_tokens;
    const why = finish === "length"
      ? `it used all ${body.max_tokens} completion tokens (${reasoning ?? "?"} on reasoning) before writing an answer`
      : "it returned no text";
    return {
      status: 502,
      body: {
        error: `Model returned no reply text: ${why}. Raise METAOS_CHAT_MAX_TOKENS on the server and try again.`,
        code: "model_call_failed",
      },
    };
  }

  let spend = null;
  try {
    const s = budgetStatus(deps.budgetPath);
    spend = { calls: s.calls, est_cost_usd: s.est_cost_usd, remaining_usd: s.remaining_usd };
  } catch {
    spend = null; // Ledger unreadable after the fact is a missing line, not a failed answer.
  }

  return {
    status: 200,
    body: {
      reply: reply.trim(),
      app: req.value.app,
      model: data?.model ?? body.model,
      latency_ms: Date.now() - startedAt,
      spend,
    },
  };
}

// The endpoint can be pointed at a local OpenAI-compatible server (the same
// hook agents/model_client.mjs has) so a demo can run without the cloud.
function chatEndpoint(env) {
  const custom = typeof env.METAOS_CHAT_ENDPOINT === "string" ? env.METAOS_CHAT_ENDPOINT.trim() : "";
  return custom || AGENT_ENDPOINT;
}

export { ModelError };
