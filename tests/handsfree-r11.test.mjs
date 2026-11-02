// Round 11 finish — Hands-Free: intake refusal (241), whole-sentence briefs (242), refusal
// catalogue (245), latency (246), failure voice (247), replayable session (248).
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { validateOrder, ORDER_REFUSALS } from "../handsfree/intake.mjs";
import { speakable, TOO_LONG_LINE } from "../handsfree/speak.mjs";
import { classifyUtterance, catalogueIds } from "../handsfree/refusals.mjs";
import { latencyOf, measureBoard, fileLatency } from "../handsfree/latency.mjs";
import { speakFailure, speakSuccess } from "../handsfree/voice.mjs";
import { buildSession, replay, writeSession, readSession } from "../handsfree/session.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "handsfree-r11-"));

test("R11-241 every malformed order is refused with its named reason", () => {
  assert.equal(validateOrder("no colon here").reason, "malformed-no-colon");
  assert.equal(validateOrder(": no agent").reason, "empty-agent");
  assert.equal(validateOrder("pax:").reason, "empty-order");
  assert.equal(validateOrder("   ").reason, "empty-order");
  assert.equal(validateOrder(42).reason, "not-a-string");
  assert.ok(Object.keys(ORDER_REFUSALS).every((k) => typeof ORDER_REFUSALS[k] === "string" && ORDER_REFUSALS[k].length));
  assert.deepEqual(validateOrder("pax: merge the branch"), { ok: true, agent: "pax", orders: "merge the branch" });
});

test("R11-242 an over-cap brief keeps whole sentences and never cuts mid-sentence", () => {
  const text = "One order ran. One finished, zero stopped, zero failed. Worker finished.";
  const one = speakable(text, { maxChars: 20 });
  assert.equal(one.summarized, true);
  assert.equal(one.text, "One order ran.");
  assert.ok(one.text.endsWith("."));
  assert.ok(one.text.length <= 20);

  const none = speakable("This single sentence is far longer than the cap allows anywhere.", { maxChars: 10 });
  assert.equal(none.text, TOO_LONG_LINE);
  assert.ok(none.text.endsWith("."), "the fallback is itself a whole sentence");

  const fits = speakable("Short brief.", { maxChars: 100 });
  assert.equal(fits.summarized, false);
  assert.equal(fits.text, "Short brief.");
});

test("R11-245 money, send and delete are refused by voice at any phrasing", () => {
  assert.deepEqual(catalogueIds(), ["money", "send", "delete"]);
  const pay = classifyUtterance("please pay the invoice");
  assert.equal(pay.refused, true);
  assert.equal(pay.id, "money");
  assert.match(pay.says, /do not move money/);
  assert.equal(classifyUtterance("send the report to the crew").id, "send");
  assert.equal(classifyUtterance("delete the old images").id, "delete");
  assert.equal(classifyUtterance("what is the gate status").refused, false);
});

test("R11-246 latency comes from the record, and a backwards clock is 0 ms plus a jump flag", () => {
  const ok = latencyOf({ filedAt: "2026-11-02T10:00:00.000Z", finishedAt: "2026-11-02T10:00:01.250Z" });
  assert.equal(ok.ms, 1250);
  assert.equal(ok.clockJump, false);
  const back = latencyOf({ filedAt: "2026-11-02T10:00:05.000Z", finishedAt: "2026-11-02T10:00:00.000Z" });
  assert.equal(back.ms, 0);
  assert.equal(back.clockJump, true);
  assert.equal(latencyOf({ filedAt: "nope", finishedAt: "nope" }).reason, "unreadable-timestamp");

  const dir = tmp();
  fs.writeFileSync(path.join(dir, "a.job.json"), JSON.stringify({ id: "a", agent: "worker", filedAt: "2026-11-02T10:00:00.000Z" }));
  fs.writeFileSync(path.join(dir, "a.result.json"), JSON.stringify({ id: "a", finishedAt: "2026-11-02T10:00:00.400Z" }));
  assert.equal(measureBoard(dir)[0].ms, 400);
  const s = fileLatency(path.join(dir, "latency.jsonl"), measureBoard(dir));
  assert.equal(s.measured, 1);
  assert.equal(s.minMs, 400);
  assert.equal(JSON.parse(fs.readFileSync(path.join(dir, "latency.jsonl"), "utf8").trim()).measured, 1);
});

test("R11-247 a down service is named as down, in plain words", () => {
  const line = speakFailure({ service: "socket", state: "down" });
  assert.equal(line.ok, false);
  assert.match(line.text, /^socket is down\./);
  assert.match(line.text, /Orders for socket are not running\./);
  assert.equal(line.names.service, "socket");
  assert.match(speakFailure({ service: "time", state: "weird" }).text, /not answering/);
  assert.equal(speakSuccess({ count: 1 }).text, "One order ran.");
});

test("R11-248 a session record recomposes its own brief, and tampering is caught", () => {
  const dir = tmp();
  const results = [
    { id: "a", agent: "worker", code: 0 },
    { id: "b", agent: "runner", code: 3 },
  ];
  const session = buildSession({ id: "s1", results, orders: [{ agent: "worker", orders: "one" }] });
  const r = replay(session);
  assert.equal(r.matches, true);
  assert.equal(r.brief, session.brief);

  const file = path.join(dir, "session.json");
  writeSession(file, session);
  assert.equal(readSession(file).id, "s1");

  const tampered = { ...session, brief: "3 orders ran.\n" };
  const bad = replay(tampered);
  assert.equal(bad.ok, false);
  assert.equal(bad.reason, "brief-does-not-recompose");
  assert.equal(replay({ id: "x" }).reason, "no-results-in-record");
});
