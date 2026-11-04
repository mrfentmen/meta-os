// The bot roster and the rooms it answers in.
//
// Three things made the desk one voice per app before this: every page asked
// "the agent", nothing remembered the last question, and nothing said who
// answered. These tests pin the behaviour that replaces it — a roster of named
// bots, mention/lead routing that reports why it chose, and a thread that
// survives the panel closing.
//
// Nothing here fires a live call: the transport is a stub fetch and the spend
// ledger is a temp file, so the suite cannot cost money.

import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  AGENT_MODEL,
  APP_IDS,
  askAgent,
  buildChatBody,
  chooseResponder,
  systemPromptFor,
  validateAsk,
} from "../server/agent-chat.mjs";
import {
  BOT_IDS,
  BOT_MODELS,
  SHIPPED_BOTS,
  buildRoster,
  loadRoster,
  parseMention,
  pickResponder,
  resolveBot,
  stateDir,
} from "../server/bot-roster.mjs";
import {
  appendTurn,
  formatTranscript,
  listThreads,
  readThread,
  validThreadId,
} from "../server/agent-thread.mjs";

const GATE_AND_KEY = { ASSESS_LIVE_MODEL: "1", SPARK_API_KEY: "test-key-not-real" };

function tempDir() {
  return mkdtempSync(join(tmpdir(), "metaos-agents-"));
}

function statePath() {
  return join(tempDir(), "spark_guardrail_state.json");
}

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

const ANSWER = {
  model: AGENT_MODEL,
  choices: [{ message: { content: "  Two cameras are watched; the third is not.  " }, finish_reason: "stop" }],
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

// -------------------------------------------------------------------- roster

test("the shipped roster covers every app the chat knows, with one lead per desk", () => {
  const roster = buildRoster({});
  assert.equal(roster.bots.length, SHIPPED_BOTS.length);
  assert.equal(new Set(BOT_IDS).size, BOT_IDS.length, "bot ids must be unique");
  for (const bot of roster.bots) {
    assert.ok(APP_IDS.includes(bot.app), `${bot.id} points at an app the chat does not know: ${bot.app}`);
    assert.match(bot.name, /^[A-Z][A-Za-z]{2,}$/, `${bot.id} needs a one-word name a person can @mention`);
    assert.ok(bot.voice.length > 20, `${bot.id} has no standing instruction`);
  }
  const apps = roster.bots.map((b) => b.app);
  assert.equal(new Set(apps).size, apps.length, "two bots must not claim the same app as lead");
});

test("roster.json can change a title, a voice and a model, and nothing else", () => {
  const roster = buildRoster({
    bots: {
      beaker: { title: "Wet lab", voice: "Answer with the formula first.", model: "muse-spark-1.3", id: "hacked", app: "ignis" },
    },
  });
  const beaker = resolveBot(roster, "beaker");
  assert.equal(beaker.title, "Wet lab");
  assert.equal(beaker.voice, "Answer with the formula first.");
  assert.equal(beaker.model, "muse-spark-1.3");
  // Identity is not an override: a roster file cannot move a bot to another desk
  // or rename it out from under a page that addresses it.
  assert.equal(beaker.id, "beaker");
  assert.equal(beaker.app, "science");
});

test("a model outside the known list falls back to the server default, with a note", () => {
  const roster = buildRoster({ bots: { ember: { model: "gpt-9-ultra" } } });
  assert.equal(resolveBot(roster, "ember").model, null);
  assert.ok(roster.notes.some((n) => /gpt-9-ultra/.test(n)), "the bad model is reported, not silently dropped");
  assert.ok(BOT_MODELS.includes(AGENT_MODEL));
});

test("a broken or missing roster file never takes the desk down", () => {
  const dir = tempDir();
  // Missing: the shipped table.
  assert.equal(loadRoster(dir).bots.length, SHIPPED_BOTS.length);
  writeFileSync(join(dir, "roster.json"), "{ this is not json");
  const broken = loadRoster(dir);
  assert.equal(broken.bots.length, SHIPPED_BOTS.length);
  assert.ok(broken.notes.some((n) => /roster\.json could not be read/.test(n)));
  writeFileSync(join(dir, "roster.json"), JSON.stringify({ bots: { wire: { title: "Sockets" } } }));
  assert.equal(resolveBot(loadRoster(dir), "wire").title, "Sockets");
});

test("the state directory follows METAOS_AGENTS_STATE, then METAOS_STATE", () => {
  assert.match(stateDir({ METAOS_AGENTS_STATE: "/tmp/agents-here" }), /agents-here$/);
  assert.match(stateDir({ METAOS_STATE: "/tmp/metaos-state" }), /metaos-state\/agents$/);
  assert.match(stateDir({}), /\.local\/state\/metaos\/agents$/);
});

// ------------------------------------------------------------------ mentions

test("@Name is read, a mail address is not", () => {
  assert.deepEqual(parseMention("@Watch is the gate clear?").ids, ["watch"]);
  assert.deepEqual(parseMention("ask @watch and @Beaker").ids, ["watch", "beaker"]);
  assert.deepEqual(parseMention("write to ops@example.com").ids, []);
  assert.equal(parseMention("@everyone status").all, true);
  assert.deepEqual(parseMention("no names here").ids, []);
});

// ------------------------------------------------------------------- routing

const ROSTER = buildRoster({});

test("a mention beats the lead, and the answer says a person named it", () => {
  const picked = chooseResponder({ app: "ignis", question: "@Beaker how many atoms are in caffeine?" }, ROSTER);
  assert.equal(picked.bot.id, "beaker");
  assert.equal(picked.picked_by, "mention");
});

test("nothing named: the page's own bot answers, as the lead", () => {
  for (const app of ["vigiles", "ignis", "medicus", "aegis", "nervus"]) {
    const picked = chooseResponder({ app, question: "what am I looking at?" }, ROSTER);
    assert.equal(picked.bot.app, app, `${app} did not answer with its own bot`);
    assert.equal(picked.picked_by, "lead");
  }
});

test("a question that clearly belongs to another desk is routed there, and marked as routed", () => {
  const picked = chooseResponder({ app: "ignis", question: "how much memory and cpu load does the machine have?" }, ROSTER);
  assert.equal(picked.bot.id, "gauge");
  assert.equal(picked.picked_by, "routing");
  assert.ok(picked.score >= 2);
});

test("one stray keyword is not enough to move the answer off the lead", () => {
  const picked = chooseResponder({ app: "ignis", question: "is there a fire in the molecule lab?" }, ROSTER);
  // "fire" is the lead's own desk; "molecule" alone is one point for Beaker.
  assert.equal(picked.bot.id, "ember");
});

test("@everyone is answered once, by the lead, and says so", () => {
  const picked = chooseResponder({ app: "medicus", question: "@everyone anything to review?" }, ROSTER);
  assert.equal(picked.bot.app, "medicus");
  assert.equal(picked.picked_by, "everyone-to-lead");
});

test("a chip for another room's bot is honoured", () => {
  const picked = chooseResponder({ app: "ignis", requestedBot: "sentry", question: "status?" }, ROSTER);
  assert.equal(picked.bot.id, "sentry");
  assert.equal(picked.picked_by, "chosen");
});

test("a typed @name beats the chip the box happens to have lit", () => {
  const picked = chooseResponder(
    { app: "science", requestedBot: "beaker", question: "@Watch is the gate clear?" },
    ROSTER,
  );
  assert.equal(picked.bot.id, "watch");
  assert.equal(picked.picked_by, "mention");
});

test("an unknown chip falls back to the lead and says the name was not found", () => {
  const picked = chooseResponder({ app: "ignis", requestedBot: "ghost", question: "status?" }, ROSTER);
  assert.equal(picked.bot.id, "ember");
  assert.equal(picked.picked_by, "unknown-bot");
});

test("the bot's own name and voice reach the model, on top of the app persona", () => {
  const prompt = systemPromptFor("science", resolveBot(ROSTER, "beaker"));
  assert.match(prompt, /You are Beaker, Molecule lab · Science/);
  assert.match(prompt, /Say when the file does not carry the property/);
  assert.match(prompt, /cannot open apps/);
});

// -------------------------------------------------------------------- threads

test("a thread is appended in order and read back in order", () => {
  const dir = tempDir();
  appendTurn(dir, "ignis-desk", { role: "operator", text: "anything burning?" });
  appendTurn(dir, "ignis-desk", { role: "bot", bot: "Ember", text: "One frame flagged." });
  const out = readThread(dir, "ignis-desk");
  assert.equal(out.turns.length, 2);
  assert.equal(out.turns[0].role, "operator");
  assert.equal(out.turns[1].bot, "Ember");
  assert.equal(out.turns[1].text, "One frame flagged.");
  assert.equal(out.turns[0].at.length, 24, "each turn carries its own timestamp");
  assert.deepEqual(listThreads(dir).map((t) => t.id), ["ignis-desk"]);
});

test("thread ids are the only door into the state directory", () => {
  for (const bad of ["../escape", "a/b", "", "UPPER", "-lead", "x".repeat(65), "a b"]) {
    assert.equal(validThreadId(bad), false, `${JSON.stringify(bad)} should be refused`);
    assert.throws(() => readThread(tempDir(), bad));
  }
  assert.equal(validThreadId("ignis-desk-01"), true);
});

test("a half-written line is skipped, not fatal", () => {
  const dir = tempDir();
  appendTurn(dir, "room", { role: "operator", text: "one" });
  const file = join(dir, "threads", "room.ndjson");
  writeFileSync(file, `${readFileSync(file, "utf8")}{"half":`);
  const out = readThread(dir, "room");
  assert.equal(out.turns.length, 1);
  assert.equal(out.skipped, 1);
});

test("the transcript the model sees is labelled by speaker and keeps the newest lines", () => {
  const text = formatTranscript(
    [
      { role: "operator", text: "first" },
      { role: "bot", bot: "Ember", text: "second" },
      { role: "error", text: "the model request failed" },
    ],
    200,
  );
  assert.match(text, /^Operator: first\nEmber: second\nSystem: the model request failed$/);
  const clipped = formatTranscript(
    Array.from({ length: 40 }, (_, i) => ({ role: "operator", text: `line ${i} ${"x".repeat(60)}` })),
    300,
  );
  assert.match(clipped, /line 39/);
  assert.doesNotMatch(clipped, /Operator: line 0 /);
});

// --------------------------------------------------------------- the endpoint

test("an ask with a thread writes the question before the call and the reply after it", async () => {
  const dir = tempDir();
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent(
    { app: "vigiles", question: "anything flagged?", thread: "vigiles-desk" },
    GATE_AND_KEY,
    { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir },
  );
  assert.equal(out.status, 200);
  assert.equal(out.body.bot.name, "Watch");
  assert.equal(out.body.picked_by, "lead");
  assert.equal(out.body.thread, "vigiles-desk");
  assert.equal(out.body.history_turns, 0);
  const turns = readThread(dir, "vigiles-desk").turns;
  assert.deepEqual(turns.map((t) => t.role), ["operator", "bot"]);
  assert.equal(turns[1].bot, "Watch");
  assert.equal(turns[1].text, "Two cameras are watched; the third is not.");
});

test("the next question in the same room carries the earlier turns", async () => {
  const dir = tempDir();
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const deps = { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir };
  await askAgent({ app: "vigiles", question: "anything flagged?", thread: "vigiles-desk" }, GATE_AND_KEY, deps);
  const second = await askAgent(
    { app: "vigiles", question: "and the third camera?", thread: "vigiles-desk" },
    GATE_AND_KEY,
    deps,
  );
  assert.equal(second.body.history_turns, 2);
  const prompt = fetchFn.calls[1].body.messages[1].content;
  assert.match(prompt, /Earlier in this room \(oldest first\):/);
  assert.match(prompt, /Operator: anything flagged\?/);
  assert.match(prompt, /Watch: Two cameras are watched; the third is not\./);
  assert.match(prompt, /Question: and the third camera\?/);
  assert.equal(readThread(dir, "vigiles-desk").turns.length, 4);
});

test("a mention in the box gets that bot's answer and that bot's name back", async () => {
  const dir = tempDir();
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent(
    { app: "vigiles", question: "@Beaker how many atoms are in caffeine?", thread: "vigiles-desk" },
    GATE_AND_KEY,
    { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir },
  );
  assert.equal(out.body.bot.id, "beaker");
  assert.equal(out.body.picked_by, "mention");
  assert.match(fetchFn.calls[0].body.messages[0].content, /You are Beaker/);
  assert.match(fetchFn.calls[0].body.messages[0].content, /Molecule lab/);
  assert.equal(readThread(dir, "vigiles-desk").turns[1].bot, "Beaker");
});

test("a failed model call leaves a line saying it failed, not a silent question", async () => {
  const dir = tempDir();
  const fetchFn = async () => {
    throw new Error("connect ECONNREFUSED");
  };
  const out = await askAgent(
    { app: "ignis", question: "smoke at the dock?", thread: "ignis-desk" },
    GATE_AND_KEY,
    { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir },
  );
  assert.equal(out.status, 502);
  assert.match(out.body.error, /ECONNREFUSED/);
  const turns = readThread(dir, "ignis-desk").turns;
  assert.deepEqual(turns.map((t) => t.role), ["operator", "error"]);
  assert.match(turns[1].text, /model request failed/);
});

test("an HTTP failure from the model is recorded and reported", async () => {
  const dir = tempDir();
  const fetchFn = stubFetch(jsonResponse({ error: "overloaded" }, 529));
  const out = await askAgent(
    { app: "ignis", question: "smoke?", thread: "ignis-desk" },
    GATE_AND_KEY,
    { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir },
  );
  assert.equal(out.status, 502);
  assert.match(readThread(dir, "ignis-desk").turns[1].text, /HTTP 529/);
});

test("a thread id that is not a thread id is ignored rather than used as a path", async () => {
  const dir = tempDir();
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent(
    { app: "aegis", question: "how many secrets?", thread: "../../etc/passwd" },
    GATE_AND_KEY,
    { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir },
  );
  assert.equal(out.status, 200);
  assert.equal(out.body.thread, null);
  assert.equal(existsSync(join(dir, "threads")), false);
});

test("a bot with its own model uses it, and the roster file is read per call", async () => {
  const dir = tempDir();
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "roster.json"), JSON.stringify({ bots: { beaker: { model: "muse-spark-1.3" } } }));
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  await askAgent(
    { app: "science", question: "how many atoms in caffeine?" },
    GATE_AND_KEY,
    { fetch: fetchFn, budgetPath: statePath(), rosterDir: dir },
  );
  assert.equal(fetchFn.calls[0].body.model, "muse-spark-1.3");
});

test("without a thread the request is identical to before: no history, no files", async () => {
  const dir = tempDir();
  const fetchFn = stubFetch(jsonResponse(ANSWER));
  const out = await askAgent({ app: "boards", question: "which room carries EMS?" }, GATE_AND_KEY, {
    fetch: fetchFn,
    budgetPath: statePath(),
    rosterDir: dir,
  });
  assert.equal(out.status, 200);
  assert.equal(out.body.thread, null);
  assert.equal(out.body.history_turns, 0);
  assert.doesNotMatch(fetchFn.calls[0].body.messages[1].content, /Earlier in this room/);
  assert.equal(existsSync(join(dir, "threads")), false);
  // No bot means no roster lookup failure: the old call shape still answers.
  assert.equal((readdirSync(dir).filter((f) => f.endsWith(".json")).length), 0);
});

test("validateAsk still rejects the shapes it always rejected", () => {
  assert.match(validateAsk({ app: "ignis", question: "  " }).error, /question: required/);
  assert.match(validateAsk({ question: "hi" }).error, /app: required/);
  const ok = validateAsk({ app: "ignis", question: "hi", bot: "Beaker", thread: "ignis-desk" });
  assert.equal(ok.ok, true);
  assert.equal(ok.value.requestedBot, "beaker");
  assert.equal(ok.value.thread, "ignis-desk");
  const badThread = validateAsk({ app: "ignis", question: "hi", thread: "../x" });
  assert.equal(badThread.value.thread, null);
  assert.equal(badThread.value.threadRejected, true);
});

test("buildChatBody only adds a bot persona when a bot is given", () => {
  const plain = buildChatBody({ app: "ignis", question: "status?" }, {});
  assert.doesNotMatch(plain.messages[0].content, /one of the agents on the Meta OS desk/);
  const withBot = buildChatBody({ app: "ignis", question: "status?" }, {}, { bot: resolveBot(ROSTER, "ember") });
  assert.match(withBot.messages[0].content, /You are Ember/);
  const crossDesk = buildChatBody(
    { app: "ignis", question: "atoms?", context: "ignis: 2 frames watched" },
    {},
    { bot: resolveBot(ROSTER, "beaker") },
  );
  assert.match(crossDesk.messages[0].content, /Molecule lab/, "a bot from another desk keeps its own persona");
  // The page context is still this page's, labelled as what the screen shows.
  assert.match(crossDesk.messages[1].content, /What this app shows right now:\nignis: 2 frames watched/);
});
