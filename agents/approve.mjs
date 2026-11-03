// Meta OS agent layer — human-in-the-loop approval airlock.
//
// High-risk commands halt here instead of running blind. A JSON policy
// routes each command to allow, deny, or ask; ask entries are recorded
// and refuse to run without an explicit human approval. Every check is
// appended to an audit log (JSONL), so the ledger shows what was gated.
//
// Policy file shape:
//   { "rules": [{ "match": "<js-regexp>", "decision": "allow|deny|ask",
//                 "reason": "human text" }],
//     "default": "ask" }
// First matching rule wins. Decisions: allow runs, deny never runs, ask
// runs only with an approval record (see approve()).
//
//   node agents/approve.mjs check "rm -rf /tmp/x" --policy <p> [--audit <log>]
//   node agents/approve.mjs run --policy <p> --audit <log> -- <cmd...>
//   node agents/approve.mjs approve <token> --approvals <dir>  (records a human yes)
//
// Approvals are files: requestApproval() writes a pending request and
// returns a token; a human answers by writing the token file with "yes"
// (any other content, or no file, means NOT approved). No network, no
// daemon — the filesystem is the airlock.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

function fail(code, message, detail = {}) {
  const err = new Error(message);
  err.name = "ApprovalError";
  err.code = code;
  Object.assign(err, detail);
  throw err;
}

const DECISIONS = new Set(["allow", "deny", "ask"]);

export function loadPolicy(policyPath) {
  let raw;
  try {
    raw = fs.readFileSync(policyPath, "utf8");
  } catch {
    fail("NO_POLICY", `policy file not found: ${policyPath}`);
  }
  let p;
  try {
    p = JSON.parse(raw);
  } catch {
    fail("BAD_POLICY", `policy file is not JSON: ${policyPath}`);
  }
  if (!Array.isArray(p.rules)) fail("BAD_POLICY", "policy needs a rules array");
  if (p.default !== undefined && !DECISIONS.has(p.default)) {
    fail("BAD_POLICY", `bad default decision: ${p.default}`);
  }
  p.rules.forEach((r, i) => {
    if (!DECISIONS.has(r.decision)) fail("BAD_POLICY", `rule ${i} bad decision: ${r.decision}`);
    try {
      new RegExp(r.match || "");
    } catch {
      fail("BAD_POLICY", `rule ${i} bad regexp: ${r.match}`);
    }
  });
  return { rules: p.rules, def: p.default || "ask" };
}

export function checkCommand(policy, cmd) {
  const text = Array.isArray(cmd) ? cmd.join(" ") : String(cmd);
  for (const r of policy.rules) {
    if (new RegExp(r.match).test(text)) {
      return { decision: r.decision, rule: r.reason || r.match, command: text };
    }
  }
  return { decision: policy.def, rule: "(default)", command: text };
}

export function auditCheck(auditPath, entry) {
  const line = JSON.stringify({ at: new Date().toISOString(), ...entry }) + "\n";
  fs.mkdirSync(path.dirname(auditPath), { recursive: true });
  fs.appendFileSync(auditPath, line);
  return entry;
}

export function requestApproval(approvalsDir, command, meta = {}) {
  fs.mkdirSync(approvalsDir, { recursive: true });
  const token = crypto.randomBytes(8).toString("hex");
  const req = { token, command, ...meta, at: new Date().toISOString(), status: "pending" };
  fs.writeFileSync(path.join(approvalsDir, `${token}.json`), JSON.stringify(req, null, 2));
  return req;
}

export function readApproval(approvalsDir, token) {
  const f = path.join(approvalsDir, `${token}.json`);
  let req;
  try {
    req = JSON.parse(fs.readFileSync(f, "utf8"));
  } catch {
    return { approved: false, reason: "no-such-request" };
  }
  if (req.status === "yes") return { approved: true };
  return { approved: false, reason: "not-approved" };
}

export function recordApproval(approvalsDir, token, answer) {
  const f = path.join(approvalsDir, `${token}.json`);
  let req;
  try {
    req = JSON.parse(fs.readFileSync(f, "utf8"));
  } catch {
    fail("NO_REQUEST", `no approval request ${token}`);
  }
  req.status = answer === "yes" ? "yes" : "no";
  req.answeredAt = new Date().toISOString();
  fs.writeFileSync(f, JSON.stringify(req, null, 2));
  return req;
}

export function gateCommand(policy, cmd, options = {}) {
  const verdict = checkCommand(policy, cmd);
  if (options.audit) auditCheck(options.audit, verdict);
  if (verdict.decision === "allow") {
    const r = spawnSync(cmd[0], cmd.slice(1), { encoding: "utf8" });
    return { ...verdict, ran: true, exit: r.status, stdout: r.stdout, stderr: r.stderr };
  }
  if (verdict.decision === "deny") return { ...verdict, ran: false };
  // ask: only run with a recorded human yes for this exact command.
  const approvalsDir = options.approvals;
  if (approvalsDir && options.token) {
    const a = readApproval(approvalsDir, options.token);
    if (a.approved) {
      const r = spawnSync(cmd[0], cmd.slice(1), { encoding: "utf8" });
      return { ...verdict, ran: true, exit: r.status, stdout: r.stdout, stderr: r.stderr };
    }
  }
  return { ...verdict, ran: false, needsHuman: true };
}

function parseArgs(argv) {
  const out = { cmd: argv[2] || "", pos: [], flags: {} };
  for (let i = 3; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--policy") out.flags.policy = argv[++i];
    else if (a === "--audit") out.flags.audit = argv[++i];
    else if (a === "--approvals") out.flags.approvals = argv[++i];
    else if (a === "--token") out.flags.token = argv[++i];
    else if (a === "--") out.pos.push(...argv.slice(i + 1)), (i = argv.length);
    else if (!a.startsWith("--")) out.pos.push(a);
  }
  return out;
}

if (process.argv[1] && path.resolve(process.argv[1]) === new URL(import.meta.url).pathname) {
  const { cmd, pos, flags } = parseArgs(process.argv);
  try {
    if (cmd === "check") {
      if (!flags.policy || !pos.length) throw new Error("check needs --policy and a command string");
      const v = checkCommand(loadPolicy(flags.policy), pos.join(" "));
      if (flags.audit) auditCheck(flags.audit, v);
      console.log(`${v.decision.toUpperCase()} [${v.rule}] :: ${v.command}`);
      process.exit(v.decision === "deny" ? 3 : 0);
    } else if (cmd === "run") {
      if (!flags.policy || !pos.length) throw new Error("run needs --policy, --audit and -- <cmd>");
      const r = gateCommand(loadPolicy(flags.policy), pos, { audit: flags.audit, approvals: flags.approvals, token: flags.token });
      if (!r.ran) {
        console.error(`${r.decision.toUpperCase()}: not running :: ${r.command}`);
        process.exit(r.decision === "deny" ? 3 : 4);
      }
      if (r.stdout) process.stdout.write(r.stdout);
      if (r.stderr) process.stderr.write(r.stderr);
      process.exit(r.exit ?? 0);
    } else if (cmd === "approve") {
      if (!flags.approvals || !pos[0]) throw new Error("approve needs --approvals and <token>");
      const r = recordApproval(flags.approvals, pos[0], pos[1] || "yes");
      console.log(`request ${r.token}: ${r.status}`);
    } else {
      console.error("usage: approve.mjs <check|run|approve> ...");
      process.exit(2);
    }
  } catch (e) {
    console.error(`${e.name || "Error"}[${e.code || "?"}]: ${e.message}`);
    process.exit(1);
  }
}
