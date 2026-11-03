// Meta Hands-Free eval adapter (first slice).
//
// Hands-Free was already hosted on main (agents/registry.json holds
// handsfree-intake, handsfree-brief and handsfree-approval, each running
// handsfree/hosted.mjs) but eval/ had no handsfree harness, so there was
// no Hands-Free baseline for "whatever raises eval scores" to be measured
// against. This is that first harness.
//
// What it scores is the text path's own rules, not voice performance:
// there is no microphone, wake word or synthesis anywhere in this path,
// and nothing here is evidence about spoken audio. The checks run the
// real modules (intake, brief, approval, speak, refusals, latency, voice,
// session) against inputs taken from committed material only:
//   - the shipped inbox in handsfree/hosted.mjs (aegis: run the local
//     passes / nervus: file one stub record),
//   - the refusal catalogue and the R11 expectations in
//     tests/handsfree-r11.test.mjs,
//   - the intake invariants in handsfree/intake_cases.test.mjs.
//
// The harness NEVER runs handsfree/hosted.mjs or handsfree/drill.mjs:
// the hosted entry writes under os-build/handsfree/ (inbox, jobs,
// brief.txt, latency.jsonl, approval drill state) and the drill clears
// and rewrites that workspace, so a harness that ran either would move
// the very workspace it scores and could approve nothing real. Every
// file-writing check here runs in its own fresh tmp dir, which it
// deletes afterwards. The tmp-only guard is asserted in adapter.test.mjs
// (os-build/handsfree/ byte-identical before and after a run).
//
// No order is dispatched, no money is moved, nothing is sent or deleted:
// the refusal catalogue is exercised as data, and the approval check
// answers a drill request in a tmp dir, never a real run.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parseInbox, dropOrders } from "../../handsfree/intake.mjs";
import { composeBrief } from "../../handsfree/brief.mjs";
import { requestApproval, dropApproval, readApproval, mayAct } from "../../handsfree/approval.mjs";
import { speakable, TOO_LONG_LINE } from "../../handsfree/speak.mjs";
import { classifyUtterance, catalogueIds } from "../../handsfree/refusals.mjs";
import { latencyOf } from "../../handsfree/latency.mjs";
import { speakFailure, speakSuccess } from "../../handsfree/voice.mjs";
import { buildSession, replay } from "../../handsfree/session.mjs";

const STANDING_INBOX = "aegis: run the local passes\nnervus: file one stub record\n";
// Fixed stamp, same as the committed intake cases use, so job ids are
// deterministic: aegis-20260101000000-0, nervus-20260101000000-1.
const FIXED_NOW = 1767225600000;

function withTmp(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "handsfree-eval-"));
  try {
    return fn(dir);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function readJob(dir, id) {
  return JSON.parse(fs.readFileSync(path.join(dir, id + ".job.json"), "utf8"));
}

function check(cond, evidence) {
  return { pass: Boolean(cond), evidence };
}

function assessIntake01() {
  return withTmp((dir) => {
    const inbox = path.join(dir, "inbox.txt");
    fs.writeFileSync(inbox, STANDING_INBOX);
    const jobsDir = path.join(dir, "jobs");
    const r = dropOrders(inbox, jobsDir, { now: FIXED_NOW, source: "handsfree-eval" });
    const filed = r.jobs.map((j) => readJob(jobsDir, j.id));
    const ok = r.jobs.length === 2 && r.skipped.length === 0 &&
      filed[0].agent === "aegis" && filed[0].orders === "run the local passes" &&
      filed[1].agent === "nervus" && filed[1].orders === "file one stub record" &&
      fs.readFileSync(inbox, "utf8") === "";
    return check(ok, "standing inbox: filed " + r.jobs.length + ", skipped " + r.skipped.length +
      ", agents " + filed.map((f) => f.agent).join(",") + ", inbox emptied");
  });
}

function assessIntake02() {
  return withTmp((dir) => {
    const inbox = path.join(dir, "inbox.txt");
    fs.writeFileSync(inbox, "# note\n\nno colon here\n: no agent\npax:\naegis: run the local passes\n");
    const jobsDir = path.join(dir, "jobs");
    const r = dropOrders(inbox, jobsDir, { now: FIXED_NOW, source: "handsfree-eval" });
    // 4 non-comment lines, all accounted for: 1 filed + 3 skipped.
    const accounted = r.jobs.length + r.skipped.length === 4;
    const refusedStay = fs.readFileSync(inbox, "utf8") === "no colon here\n: no agent\npax:\n";
    return check(accounted && r.jobs.length === 1 && r.skipped.length === 3 && refusedStay,
      "mixed inbox: filed " + r.jobs.length + ", skipped " + r.skipped.length +
      ", refused lines stay in inbox: " + refusedStay);
  });
}

function assessIntakeEmpty() {
  const r = parseInbox("");
  return check(r.jobs.length === 0 && r.skipped.length === 0,
    "empty inbox: filed 0, skipped 0");
}

function assessRefusal() {
  const ids = catalogueIds();
  const pay = classifyUtterance("please pay the invoice");
  const send = classifyUtterance("send the report to the crew");
  const del = classifyUtterance("delete the old images");
  const ok = classifyUtterance("what is the gate status");
  const good = JSON.stringify(ids) === JSON.stringify(["money", "send", "delete"]) &&
    pay.refused && pay.id === "money" && send.id === "send" && del.id === "delete" && !ok.refused;
  return check(good, "catalogue " + ids.join(",") + "; pay->money, send->send, delete->delete, gate question allowed");
}

function assessBrief01() {
  const text = composeBrief([
    { id: "b", agent: "nervus", code: 3 },
    { id: "a", agent: "aegis", code: 0 },
  ]);
  const want = "2 orders ran.\n1 finished, 0 stopped, 1 failed.\naegis finished.\nnervus failed (code 3).\n";
  return check(text === want, "brief: " + JSON.stringify(text));
}

function assessBriefStopped() {
  const text = composeBrief([{ id: "a", agent: "aegis", code: 1, stopped: true }]);
  const want = "1 order ran.\n0 finished, 1 stopped, 0 failed.\naegis was stopped.\n";
  return check(text === want && !text.includes("success"), "brief: " + JSON.stringify(text));
}

function assessBriefEmpty() {
  const text = composeBrief([]);
  return check(text === "No orders ran.\n", "brief: " + JSON.stringify(text));
}

function assessSpeak() {
  const over = speakable("One order ran. One finished, zero stopped, zero failed. Worker finished.", { maxChars: 20 });
  const none = speakable("This single sentence is far longer than the cap allows anywhere.", { maxChars: 10 });
  const fits = speakable("Short brief.", { maxChars: 100 });
  const good = over.summarized && over.text === "One order ran." && over.text.endsWith(".") &&
    none.text === TOO_LONG_LINE && none.text.endsWith(".") &&
    !fits.summarized && fits.text === "Short brief.";
  return check(good, "speak: cap20 kept " + JSON.stringify(over.text) +
    ", single-sentence fallback used: " + (none.text === TOO_LONG_LINE) +
    ", fitting brief unchanged: " + (!fits.summarized));
}

function assessApproval() {
  return withTmp((dir) => {
    const run = path.join(dir, "run");
    fs.mkdirSync(run);
    const req = requestApproval(run, { run: "handsfree-approval", what: "drill: answer once" });
    const first = dropApproval(run, "yes", { by: "hosted-drill" });
    const second = dropApproval(run, "yes", { by: "hosted-drill" });
    const state = readApproval(run).state;
    const ledger = fs.readFileSync(path.join(run, "ledger.jsonl"), "utf8")
      .split("\n").filter(Boolean).map((l) => JSON.parse(l).event);
    const good = req.ok && first.ok && first.decision === "yes" &&
      !second.ok && second.duplicate === true && second.prior === "yes" &&
      state === "allowed" && mayAct(run) &&
      ledger.includes("approval") && ledger.includes("approval-duplicate");
    return check(good, "approval: first=" + (first.ok ? first.decision : first.reason) +
      ", second=" + (second.ok ? "counted" : second.reason) + ", state=" + state +
      ", ledger events " + ledger.join(","));
  });
}

function assessLatency() {
  const ok = latencyOf({ filedAt: "2026-11-02T10:00:00.000Z", finishedAt: "2026-11-02T10:00:01.250Z" });
  const back = latencyOf({ filedAt: "2026-11-02T10:00:05.000Z", finishedAt: "2026-11-02T10:00:00.000Z" });
  const good = ok.ok && ok.ms === 1250 && ok.clockJump === false &&
    back.ok && back.ms === 0 && back.clockJump === true;
  return check(good, "latency: forward " + ok.ms + " ms, backwards " + back.ms +
    " ms clockJump=" + back.clockJump);
}

function assessVoice() {
  const down = speakFailure({ service: "socket", state: "down" });
  const unknown = speakFailure({ service: "time", state: "weird" });
  const one = speakSuccess({ count: 1 });
  const good = down.ok === false && down.text === "socket is down. Orders for socket are not running." &&
    unknown.text.includes("is not answering") && unknown.ok === false &&
    one.ok === true && one.text === "One order ran.";
  return check(good, "voice: " + JSON.stringify(down.text) + " / " + JSON.stringify(unknown.text));
}

function assessSession() {
  const results = [
    { id: "a", agent: "worker", code: 0 },
    { id: "b", agent: "runner", code: 3 },
  ];
  const session = buildSession({ id: "s1", results, orders: [{ agent: "worker", orders: "one" }] });
  const goodReplay = replay(session);
  const tampered = replay({ ...session, brief: "3 orders ran.\n" });
  const noResults = replay({ id: "x" });
  const good = goodReplay.matches && goodReplay.ok &&
    !tampered.ok && tampered.reason === "brief-does-not-recompose" &&
    !noResults.ok && noResults.reason === "no-results-in-record";
  return check(good, "session: replay matches=" + goodReplay.matches +
    ", tampered reason=" + tampered.reason + ", no-results reason=" + noResults.reason);
}

function assessRegistry(root) {
  const registry = JSON.parse(fs.readFileSync(path.join(root, "agents", "registry.json"), "utf8"));
  const entries = registry.agents || [];
  const want = [
    ["handsfree-intake", "intake", "order intake"],
    ["handsfree-brief", "brief", "speakable brief"],
    ["handsfree-approval", "approval", "approval inbox"],
  ];
  const found = want.map(([name, role, lanePart]) => {
    const e = entries.find((a) => a.name === name);
    return e && e.hosted === true &&
      JSON.stringify(e.command) === JSON.stringify(["repo:node", "handsfree/hosted.mjs", role]) &&
      String(e.lane || "").includes(lanePart);
  });
  return check(found.every(Boolean),
    "registry: " + want.map(([n], i) => n + "=" + (found[i] ? "hosted" : "MISSING")).join(", "));
}

const CHECKS = {
  "HF-INTAKE-01": () => assessIntake01(),
  "HF-INTAKE-02": () => assessIntake02(),
  "HF-INTAKE-EMPTY-01": () => assessIntakeEmpty(),
  "HF-REFUSAL-01": () => assessRefusal(),
  "HF-BRIEF-01": () => assessBrief01(),
  "HF-BRIEF-STOPPED-01": () => assessBriefStopped(),
  "HF-BRIEF-EMPTY-01": () => assessBriefEmpty(),
  "HF-SPEAK-01": () => assessSpeak(),
  "HF-APPROVAL-01": () => assessApproval(),
  "HF-LATENCY-01": () => assessLatency(),
  "HF-VOICE-01": () => assessVoice(),
  "HF-SESSION-01": () => assessSession(),
  "HF-REGISTRY-01": (root) => assessRegistry(root),
};

export function assessHandsfree(scenario, root) {
  const fn = CHECKS[scenario.id];
  if (!fn) return { pass: false, evidence: "no checker for scenario " + scenario.id };
  try {
    return fn(root);
  } catch (err) {
    return { pass: false, evidence: "error: " + err.message };
  }
}

export function runHandsfreeEval(scenarios, assess, root) {
  return scenarios.map((s) => {
    let result;
    try {
      result = assess(s, root);
    } catch (err) {
      result = { pass: false, evidence: "error: " + err.message };
    }
    return { id: s.id, title: s.title, pass: result.pass === true, evidence: result.evidence || "" };
  });
}
