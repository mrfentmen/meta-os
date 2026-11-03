// Hands-Free C1 — a text inbox becomes watchman job files.
//
// The inbox is lines a person can type: one line, one order, the agent's name before a colon.
// Blank lines and #comments are ignored. A line with no colon is NOT guessed at -- it stays in
// the inbox and is reported, because an order nobody can parse is an order nobody should run.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { classifyUtterance } from "./refusals.mjs";

// A typed order is a line, not a payload. 4096 characters is far beyond any order a person
// types and far below anything that would turn the inbox into a transfer buffer; a longer line
// is refused with its length recorded, and the line stays in the inbox for a human to split.
export const MAX_ORDER_CHARS = 4096;

export const ORDER_REFUSALS = {
  "malformed-no-colon": "the line has no 'agent:' prefix, so the order has no owner",
  "empty-agent": "the line names no agent before the colon",
  "empty-order": "the line names an agent but asks for nothing",
  "not-a-string": "an order must be text",
  "oversized-order": "the line is longer than one typed order may be",
  "empty-inbox": "the inbox held no order at all",
};

export function validateOrder(line) {
  if (typeof line !== "string") return { ok: false, reason: "not-a-string" };
  const text = line.trim();
  if (!text) return { ok: false, reason: "empty-order" };
  const at = text.indexOf(":");
  if (at < 0) return { ok: false, reason: "malformed-no-colon" };
  if (at === 0) return { ok: false, reason: "empty-agent" };
  if (!text.slice(at + 1).trim()) return { ok: false, reason: "empty-order" };
  return { ok: true, agent: text.slice(0, at).trim(), orders: text.slice(at + 1).trim() };
}

export function parseInbox(text) {  const jobs = [];
  const skipped = [];
  text.split(/\r?\n/).forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    if (line.length > MAX_ORDER_CHARS) {
      // Kept whole so dropOrders can leave it in the inbox; the refusal record carries only a
      // length and a hash, never the text (R12-039).
      skipped.push({ line: i + 1, text: line, reason: "oversized-order", length: line.length });
      return;
    }
    const at = line.indexOf(":");
    if (at <= 0) {
      skipped.push({ line: i + 1, text: line, reason: "no agent before a colon" });
      return;
    }
    const agent = line.slice(0, at).trim();
    const orders = line.slice(at + 1).trim();
    if (!agent || !orders) {
      skipped.push({ line: i + 1, text: line, reason: "empty agent or empty order" });
      return;
    }
    // R13-394: the catalogue decided what may not be ordered, but intake never asked it, so a
    // refused order was still filed as a job. Ask before filing; the line stays in the inbox.
    const refusal = classifyUtterance(orders);
    if (refusal.refused) {
      skipped.push({ line: i + 1, text: line, reason: "refusal:" + refusal.id, says: refusal.says });
      return;
    }
    jobs.push({ agent, orders });
  });
  return { jobs, skipped };
}

// Write each order as <id>.job.json, atomically, and mark the lines that were taken. Lines the
// parser refused stay in the inbox: silently deleting them would turn a typo into a lost order.
export function dropOrders(inboxFile, jobsDir, { now = Date.now(), source = "handsfree", refugeFile = null } = {}) {
  const text = fs.readFileSync(inboxFile, "utf8");
  const { jobs, skipped } = parseInbox(text);
  fs.mkdirSync(jobsDir, { recursive: true });
  const stamp = new Date(now).toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const written = [];
  // Every refusal is written down, because a line that silently disappears is worse than a
  // line that was never accepted (R12-039). The record names the line and the reason; the text
  // is represented by a short hash, not copied, so an order that mentions something private
  // does not become a second copy in a log.
  const refusalFile = refugeFile || inboxFile + ".refusals.jsonl";
  const at = new Date(now).toISOString();
  const refusals = [];
  if (!text.trim()) {
    refusals.push({ at, event: "refused", reason: "empty-inbox", source });
  }
  for (const s of skipped) {
    const full = typeof s.text === "string" ? s.text : "";
    refusals.push({
      at,
      event: "refused",
      line: s.line,
      reason: s.reason,
      says: s.says || null,
      length: full.length,
      text_hash: createHash("sha256").update(full).digest("hex").slice(0, 16),
      source,
    });
  }
  if (refusals.length) {
    fs.appendFileSync(refusalFile, refusals.map((r) => JSON.stringify(r)).join("\n") + "\n");
  }

  jobs.forEach((j, i) => {
    let id = j.agent + "-" + stamp + "-" + i;
    let bump = 0;
    while (fs.existsSync(path.join(jobsDir, id + ".job.json"))) {
      bump += 1;
      id = j.agent + "-" + stamp + "-" + i + "-" + bump;
    }
    const rec = { id, agent: j.agent, orders: j.orders, filedAt: new Date(now).toISOString(), source };
    const tmp = path.join(jobsDir, id + ".job.json.tmp");
    fs.writeFileSync(tmp, JSON.stringify(rec, null, 2));
    fs.renameSync(tmp, path.join(jobsDir, id + ".job.json"));
    written.push({ id, agent: j.agent });
  });

  if (written.length) {
    fs.appendFileSync(inboxFile + ".done", written.map((w) => JSON.stringify({ ...w, at: new Date(now).toISOString() })).join("\n") + "\n");
  }
  fs.writeFileSync(inboxFile, skipped.length ? skipped.map((s) => s.text).join("\n") + "\n" : "");
  return { jobs: written, skipped, refusals };
}

/* ---- CLI: node handsfree/intake.mjs <inbox> <jobsDir> ---- */
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const [, , inbox, jobsDir] = process.argv;
  if (!inbox || !jobsDir) { console.error("usage: intake.mjs <inbox> <jobsDir>"); process.exit(2); }
  const r = dropOrders(inbox, jobsDir);
  console.log("handsfree intake: filed " + r.jobs.length + ", refused " + r.skipped.length);
  for (const s of r.skipped) console.log("  refused line " + s.line + ": " + s.reason);
  process.exit(r.skipped.length ? 1 : 0);
}
