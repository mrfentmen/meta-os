// The in-app agent chat (/api/agent/ask) had no test at all, which is how it
// shipped answering only three of the twelve apps and returning "no text" when
// a reasoning model spent its budget thinking. These tests pin the three
// things that make the box work on every page: the app id is accepted for
// every app, the request carries that app's persona and an explicit token cap,
// and every refusal is a named error instead of an empty answer.
//
// No test fires a live call: the transport is a stub fetch and the budget
// ledger is a temp file, so nothing here can spend money.

import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  AGENT_ENDPOINT,
  AGENT_MODEL,
  APP_IDS,
  APP_PROFILES,
  DEFAULT_MAX_TOKENS,
  askAgent,
  buildChatBody,
  validateAsk,
} from "../server/agent-chat.mjs";

function tempStatePath() {
  return join(mkdtempSync(join(tmpdir(), "trio-chat-")), "spark_guardrail_state.json");
}

const GATE_AND_KEY = { ASSESS_LIVE_MODEL: "1", SPARK_API_KEY: "test-key-not-real" };

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

const ANSWER = {
  model: AGENT_MODEL,
  choices: [{ message: { content: "  The board has two watched cameras.  " }, finish_reason: "stop" }],
  usage: { prompt_tokens: 120, completion_tokens: 40, total_tokens: 160 },
};

function stubFetch(response) {
  const calls = [];
  const fn = async (url, opts) => {
    calls.push({ url, opts, body: JSON.parse(opts.body) });
    return response;
  };
  fn.calls = calls;
  return fn;
}

// ---------------------------------------------------------------- validation

test("every app in the dock is a valid chat target", () => {
  const expected = [
    "vigiles",
    "ignis",
    "medicus",
    "science",
    "musica",
    "officina",
    "custos",
    "boards",
    "aegis",
    "nervus",
    "messages",
    "monitor",
    "notes",
  ];
  for (const app of expected) {
    assert.ok(APP_IDS.includes(app), `${app} missing from APP_PROFILES`);
    const req = validateAsk({ app, question: "what am I looking at?" });
    assert.equal(req.ok, true, `${app} was refused`);
    assert.equal(req.value.app, app);
  }
});

test("the three division pages keep working: division maps to app", () => {
  for (const division of ["vigiles", "ignis", "medicus"]) {
    const req = validateAsk({ division, question: "status?" });
    assert.equal(req.ok, true);
    assert.equal(req.value.app, division);
  }
});

test("app wins over division when both are sent", () => {
  const req = validateAsk({ app: "aegis", division: "ignis", question: "status?" });
  assert.equal(req.ok, true);
  assert.equal(req.value.app, "aegis");
});

test("an unknown app falls back to the general persona instead of refusing", () => {
  const req = validateAsk({ app: "app-that-ships-next-week", question: "hello" });
  assert.equal(req.ok, true);
  assert.equal(req.value.app, "general");
  assert.equal(req.value.requestedApp, "app-that-ships-next-week");
});

test("no app and no division is a 400-shaped refusal", () => {
  const req = validateAsk({ question: "hello" });
  assert.equal(req.ok, false);
  assert.match(req.error, /app: required/);
});

test("an empty or oversized question is refused, and context is capped", () => {
  assert.match(validateAsk({ app: "boards", question: "   " }).error, /question: required/);
  assert.match(validateAsk({ app: "boards", question: "x".repeat(2001) }).error, /at most 2000/);
  const req = validateAsk({ app: "boards", question: "ok", context: "c".repeat(9000) });
  assert.equal(req.ok, true);
  assert.equal(req.value.context.length, 4000);
});

test("a non-object body is refused, not thrown", () => {
  for (const body of [null, [], "string", 7]) {
    const req = validateAsk(body);
    assert.equal(req.ok, false);
    assert.match(req.error, /not a JSON object/);
  }
});

// ------------------------------------------------------------- request shape

test("the request uses the cheap contributor model with an explicit token cap", () => {
  const body = buildChatBody({ app: "science", question: "how many atoms?", context: "" }, {});
  assert.equal(body.model, AGENT_MODEL);
  assert.equal(body.model, "muse-spark-1.3-contributor");
  assert.equal(body.max_tokens, DEFAULT_MAX_TOKENS);
  assert.equal(body.temperature, 0);
  assert.equal(body.messages.length, 2);
  assert.match(body.messages[1].content, /Question: how many atoms\?/);
});

test("the model, the token cap and the endpoint are env-overridable", async () => {
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const env = {
    ...GATE_AND_KEY,
    METAOS_CHAT_MODEL: "muse-spark-1.3",
    METAOS_CHAT_MAX_TOKENS: "3000",
    METAOS_CHAT_ENDPOINT: "http://127.0.0.1:11434/v1/chat/completions",
  };
  await askAgent({ app: "boards", question: "hi" }, env, { fetch: fetchFn, budgetPath: tempStatePath() });
  assert.equal(fetchFn.calls[0].url, "http://127.0.0.1:11434/v1/chat/completions");
  assert.equal(fetchFn.calls[0].body.model, "muse-spark-1.3");
  assert.equal(fetchFn.calls[0].body.max_tokens, 3000);
});

test("each app's own persona reaches the model, and the shared rules are always there", () => {
  for (const app of APP_IDS) {
    const body = buildChatBody({ app, question: "what is this?", context: "" }, {});
    const system = body.messages[0].content;
    assert.ok(
      system.includes(APP_PROFILES[app].label),
      `${app} persona does not name ${APP_PROFILES[app].label}`,
    );
    assert.match(system, /cannot open apps, move the pointer, change the board, or send anything/);
    assert.match(system, /Never identify a person/);
  }
});

test("the page's context is put in front of the question", () => {
  const body = buildChatBody({ app: "monitor", question: "what is the load?", context: "cpu: 12%" }, {});
  assert.match(body.messages[1].content, /What this app shows right now:\ncpu: 12%/);
  assert.match(body.messages[1].content, /Question: what is the load\?/);
});

// ---------------------------------------------------------------- the answers

test("a real-shaped answer comes back as reply text, trimmed, with spend", async () => {
  const statePath = tempStatePath();
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent({ app: "vigiles", question: "anything flagged?" }, GATE_AND_KEY, {
    fetch: fetchFn,
    budgetPath: statePath,
  });
  assert.equal(out.status, 200);
  assert.equal(out.body.reply, "The board has two watched cameras.");
  assert.equal(out.body.app, "vigiles");
  assert.equal(out.body.model, AGENT_MODEL);
  assert.equal(fetchFn.calls[0].url, AGENT_ENDPOINT);
  assert.equal(fetchFn.calls[0].opts.headers.Authorization, "Bearer test-key-not-real");
  // The call was counted in the shared ledger, not just answered.
  assert.equal(out.body.spend.calls, 1);
  assert.ok(out.body.spend.est_cost_usd > 0);
  const ledger = JSON.parse(readFileSync(statePath, "utf8"));
  assert.equal(ledger.calls, 1);
  assert.equal(ledger.log[0].kind, "agent-chat:vigiles");
});

test("the same endpoint answers for every app id", async () => {
  const statePath = tempStatePath();
  for (const app of APP_IDS) {
    const fetchFn = stubFetch(jsonResponse(ANSWER));
    const out = await askAgent({ app, question: "status?" }, GATE_AND_KEY, {
      fetch: fetchFn,
      budgetPath: statePath,
    });
    assert.equal(out.status, 200, `${app} did not answer: ${JSON.stringify(out.body)}`);
    assert.equal(out.body.reply, "The board has two watched cameras.");
    assert.equal(fetchFn.calls.length, 1, `${app} fired ${fetchFn.calls.length} calls`);
  }
});

test("no key is a 503 naming the variable, and no call is sent", async () => {
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent({ app: "boards", question: "hi" }, { ASSESS_LIVE_MODEL: "1" }, {
    fetch: fetchFn,
    budgetPath: tempStatePath(),
  });
  assert.equal(out.status, 503);
  assert.equal(out.body.code, "not_configured");
  assert.match(out.body.error, /SPARK_API_KEY/);
  assert.equal(fetchFn.calls.length, 0);
});

test("the live gate is still a gate: no ASSESS_LIVE_MODEL means held", async () => {
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent({ app: "boards", question: "hi" }, { SPARK_API_KEY: "k" }, {
    fetch: fetchFn,
    budgetPath: tempStatePath(),
  });
  assert.equal(out.status, 503);
  assert.equal(out.body.code, "held");
  assert.match(out.body.error, /ASSESS_LIVE_MODEL=1/);
  assert.equal(fetchFn.calls.length, 0);
});

test("an exhausted budget refuses before any call", async () => {
  const statePath = tempStatePath();
  writeFileSync(statePath, JSON.stringify({ calls: 9, est_cost_usd: 75, log: [] }));
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent({ app: "boards", question: "hi" }, GATE_AND_KEY, {
    fetch: fetchFn,
    budgetPath: statePath,
  });
  assert.equal(out.status, 402);
  assert.equal(out.body.code, "budget");
  assert.equal(fetchFn.calls.length, 0);
});

test("a model HTTP failure is a 502, not an empty reply", async () => {
  const out = await askAgent({ app: "boards", question: "hi" }, GATE_AND_KEY, {
    fetch: stubFetch(jsonResponse({}, 500)),
    budgetPath: tempStatePath(),
  });
  assert.equal(out.status, 502);
  assert.equal(out.body.code, "model_call_failed");
  assert.match(out.body.error, /HTTP 500/);
});

test("a non-JSON model response is a 502", async () => {
  const out = await askAgent({ app: "boards", question: "hi" }, GATE_AND_KEY, {
    fetch: async () => ({ ok: true, status: 200, json: async () => { throw new Error("bad json"); } }),
    budgetPath: tempStatePath(),
  });
  assert.equal(out.status, 502);
  assert.match(out.body.error, /not JSON/);
});

test("a reasoning model that never wrote an answer names the token cap", async () => {
  const out = await askAgent({ app: "boards", question: "hi" }, GATE_AND_KEY, {
    fetch: stubFetch(
      jsonResponse({
        model: AGENT_MODEL,
        choices: [{ message: { content: null }, finish_reason: "length" }],
        usage: { prompt_tokens: 90, completion_tokens: 4000, completion_tokens_details: { reasoning_tokens: 4000 } },
      }),
    ),
    budgetPath: tempStatePath(),
  });
  assert.equal(out.status, 502);
  assert.match(out.body.error, /METAOS_CHAT_MAX_TOKENS/);
  assert.match(out.body.error, /4000 on reasoning/);
});

test("a transport throw is a 502 with the message, and nothing is recorded", async () => {
  const statePath = tempStatePath();
  const out = await askAgent({ app: "boards", question: "hi" }, GATE_AND_KEY, {
    fetch: async () => {
      throw new Error("getaddrinfo ENOTFOUND api.meta.ai");
    },
    budgetPath: statePath,
  });
  assert.equal(out.status, 502);
  assert.match(out.body.error, /ENOTFOUND/);
  // A failed call is not a billed call: the ledger file was never created.
  assert.equal(existsSync(statePath), false);
});
