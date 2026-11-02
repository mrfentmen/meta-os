// Hands-Free C3 — a yes/no drop lands in the run's ledger, timestamped.
//
// The standing rule is announce-before-send: where it applies, nothing acts until the boss's
// word is in the run's own record. So the approval is not a flag in a side file -- the answer is
// appended to the same JSONL the run already writes, with who said it and when.
//
// One request, one answer. A second answer is refused rather than overwriting the first: the
// record is append-only, and an approval that can be changed is not an approval.
import fs from "node:fs";
import path from "node:path";
import { Ledger } from "../agents/runtime.mjs";

const reqFile = (dir) => path.join(dir, "approval.request.json");
const ansFile = (dir) => path.join(dir, "approval.json");

function writeJson(file, obj) {
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2));
  fs.renameSync(tmp, file);
}

export function requestApproval(runDir, { run, what, why = "", now = Date.now() } = {}) {
  if (!run || !what) return { ok: false, reason: "missing-run-or-what" };
  const cur = readApproval(runDir);
  if (cur.state === "pending") return { ok: false, reason: "already-pending" };
  if (cur.state === "allowed" || cur.state === "denied") return { ok: false, reason: "already-answered" };
  writeJson(reqFile(runDir), { run, what, why, requestedAt: new Date(now).toISOString(), state: "pending" });
  return { ok: true };
}

export function readApproval(runDir) {
  let request = null;
  try { request = JSON.parse(fs.readFileSync(reqFile(runDir), "utf8")); } catch {}
  if (!request) return { state: "none", request: null, answer: null };
  let answer = null;
  try { answer = JSON.parse(fs.readFileSync(ansFile(runDir), "utf8")); } catch {}
  if (!answer) return { state: "pending", request, answer: null };
  return { state: answer.decision === "yes" ? "allowed" : "denied", request, answer };
}

const YES = /^(y|yes|approve|approved)$/i;
const NO = /^(n|no|deny|denied)$/i;

export function dropApproval(runDir, answer, { by = "boss", now = Date.now() } = {}) {
  const word = String(answer == null ? "" : answer).trim();
  const decision = YES.test(word) ? "yes" : NO.test(word) ? "no" : null;
  if (!decision) return { ok: false, reason: "bad-answer" };
  const cur = readApproval(runDir);
  if (cur.state === "none") return { ok: false, reason: "no-request" };
  if (cur.state === "allowed" || cur.state === "denied") return { ok: false, reason: "already-answered" };

  const at = new Date(now).toISOString();
  writeJson(ansFile(runDir), { decision, by, at });
  // The ledger line is the record; the side file is a convenience for the next reader.
  new Ledger(path.join(runDir, "ledger.jsonl")).add(cur.request.run, "approval", { decision, by, at, what: cur.request.what });
  return { ok: true, decision, at };
}

export function mayAct(runDir) {
  return readApproval(runDir).state === "allowed";
}
