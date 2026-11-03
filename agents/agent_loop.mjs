#!/usr/bin/env node
// agent_loop.mjs — the Meta OS agent that can think and act.
//
// The relay (runtime.mjs) has always spawned *programs*. This is the missing
// piece: one bounded loop where a Meta model decides the next action, the OS
// performs it inside a workspace, and every step is written to disk. Nothing
// is simulated: each tool call really touches a real directory, and `run`
// really spawns a shell.
//
// Contract with the relay: it starts this file with cwd = the run directory
// and a brief.json already there (see runtime.mjs §S4). Orders come from that
// brief, so `meta-ask "..." --agent meta-coder` works with no extra plumbing.
//
//   node agents/agent_loop.mjs                 # read ./brief.json
//   node agents/agent_loop.mjs --task "..."    # direct run
//   node agents/agent_loop.mjs --self-test     # tools only, no model, no key
//
// Exit: 0 finished, 2 action cap, 3 model error, 4 no key, 5 unusable task.
//
// Secrets: the key is never logged, never given to a tool subprocess, and the
// transcript is redacted before it is written.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { spawn } from "node:child_process";
import {
  chat,
  usageCosts,
  modelConfig,
  ModelUnavailable,
  ModelError,
} from "./model_client.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));

const LIMITS = {
  maxActions: Number(process.env.METAOS_MAX_ACTIONS || 0) || 12,
  maxUsd: Number(process.env.METAOS_MAX_USD || 0) || 0.25,
  maxOutputChars: 4000,
  maxReadChars: 20000,
  maxWriteChars: 200000,
  commandTimeoutMs: Number(process.env.METAOS_CMD_TIMEOUT_MS || 0) || 25000,
};

const SYSTEM = `You are a Meta OS agent, working on a real Linux userland from a
native Meta desktop. You act by calling tools, one per turn, and you verify your
own work before finishing.

Reply with ONE JSON object and nothing else:
  {"tool": "<name>", "args": {...}}

Tools:
  {"tool":"list","args":{"path":"."}}
      -> entries of a directory, relative to the workspace
  {"tool":"read","args":{"path":"file.txt"}}
      -> file contents (text only, truncated at ${LIMITS.maxReadChars} chars)
  {"tool":"write","args":{"path":"file.txt","content":"..."}}
      -> create or replace a file inside the workspace (parents are created)
  {"tool":"run","args":{"command":"sh -c '...'"}}
      -> run a shell command in the workspace; stdout+stderr come back
  {"tool":"finish","args":{"summary":"what you did and how you checked it"}}

Rules:
- Work only inside the workspace. Paths are relative to it; escaping it fails.
- Prefer doing the task over describing it. A claim without a tool result is
  not evidence.
- Verify: after writing, run the check the task names (a test, a parser, a
  grep) and read the real output.
- Stop as soon as the evidence is in: if your last tool result already proves
  the task is done, your next reply is finish. Do not verify the same thing
  twice.
- Do not print or search for credentials. Never write a key into a file.
- When the task is complete and verified, call finish with the evidence.
- If the task is impossible with these tools, finish with the blocker named.`;

function redact(text) {
  return String(text)
    .replace(/\b(sk-[A-Za-z0-9_-]{8,}|LLM_[A-Za-z0-9]{8,})\b/g, "[REDACTED]")
    .replace(/(Bearer\s+)[A-Za-z0-9._-]{8,}/g, "$1[REDACTED]");
}

function childEnv() {
  const env = {};
  for (const [k, v] of Object.entries(process.env)) {
    if (/(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|SESSION|COOKIE)/i.test(k)) continue;
    env[k] = v;
  }
  return env;
}

const DENY = [
  { re: /(^|[\s;&|])rm\s+-[a-z]*r[a-z]*f?\s+\/(\s|$)/i, why: "rm -rf /" },
  { re: /\bmkfs(\.[a-z0-9]+)?\b/i, why: "mkfs" },
  { re: /\bdd\b[^\n]*\bof=\/dev\//i, why: "dd to a device" },
  { re: /:\s*\(\s*\)\s*\{/, why: "fork bomb" },
  { re: /\b(shutdown|reboot|poweroff|halt)\b/i, why: "host power control" },
  { re: /\bsudo\b/, why: "privilege escalation" },
  { re: /\b(curl|wget)\b[^\n]*(KEY|TOKEN|SECRET)/i, why: "credential egress" },
];

function within(root, rel) {
  const abs = path.resolve(root, rel || ".");
  const withSep = root.endsWith(path.sep) ? root : root + path.sep;
  if (abs !== root && !abs.startsWith(withSep)) {
    throw new Error("path escapes the workspace: " + rel);
  }
  return abs;
}

function trimOut(text) {
  const s = String(text || "");
  if (s.length <= LIMITS.maxOutputChars) return s;
  return s.slice(0, LIMITS.maxOutputChars) + "\n... [truncated " + (s.length - LIMITS.maxOutputChars) + " chars]";
}

function runShell(root, command) {
  return new Promise((resolve) => {
    const started = Date.now();
    const child = spawn("bash", ["-lc", command], {
      cwd: root,
      env: childEnv(),
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    let err = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      try { child.kill("SIGKILL"); } catch { /* already gone */ }
    }, LIMITS.commandTimeoutMs);
    child.stdout.on("data", (c) => { out += c.toString("utf8"); });
    child.stderr.on("data", (c) => { err += c.toString("utf8"); });
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve({ code: null, error: e.message, stdout: "", stderr: "", ms: Date.now() - started });
    });
    child.on("exit", (code, signal) => {
      clearTimeout(timer);
      resolve({
        code,
        signal: signal || null,
        timedOut,
        stdout: trimOut(out),
        stderr: trimOut(err),
        ms: Date.now() - started,
      });
    });
  });
}

export async function execTool(root, tool, args = {}) {
  const absRoot = path.resolve(root);
  try {
    return await runTool(absRoot, tool, args || {});
  } catch (error) {
    // A tool that throws is a tool result, not a dead agent: the loop must be
    // able to read the refusal and try something else.
    return { ok: false, error: error.message };
  }
}

async function runTool(root, tool, args) {
  switch (tool) {
    case "list": {
      const abs = within(root, args.path || ".");
      const entries = fs.readdirSync(abs, { withFileTypes: true })
        .sort((a, b) => a.name.localeCompare(b.name))
        .slice(0, 200)
        .map((d) => (d.isDirectory() ? d.name + "/" : d.name));
      return { ok: true, path: args.path || ".", entries };
    }
    case "read": {
      const abs = within(root, args.path);
      const text = fs.readFileSync(abs, "utf8");
      const clipped = text.length > LIMITS.maxReadChars
        ? text.slice(0, LIMITS.maxReadChars) + "\n... [truncated]"
        : text;
      return { ok: true, path: args.path, bytes: Buffer.byteLength(text), content: clipped };
    }
    case "write": {
      const abs = within(root, args.path);
      const content = String(args.content ?? "");
      if (content.length > LIMITS.maxWriteChars) {
        return { ok: false, error: "content larger than " + LIMITS.maxWriteChars + " chars" };
      }
      fs.mkdirSync(path.dirname(abs), { recursive: true });
      fs.writeFileSync(abs, content);
      return { ok: true, path: args.path, bytes: Buffer.byteLength(content) };
    }
    case "run": {
      const command = String(args.command || "");
      if (!command.trim()) return { ok: false, error: "empty command" };
      const denied = DENY.find((d) => d.re.test(command));
      if (denied) return { ok: false, refused: denied.why };
      const r = await runShell(root, command);
      return { ok: r.code === 0, ...r };
    }
    default:
      return { ok: false, error: "unknown tool: " + String(tool) };
  }
}

function parseAction(text) {
  const t = String(text || "").trim().replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  const start = t.indexOf("{");
  const end = t.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("no JSON object in the reply");
  const obj = JSON.parse(t.slice(start, end + 1));
  if (!obj || typeof obj !== "object" || typeof obj.tool !== "string") {
    throw new Error("reply is JSON but has no string tool field");
  }
  return obj;
}

function readBrief(cwd) {
  const file = path.join(cwd, "brief.json");
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function argValue(argv, flag) {
  const i = argv.indexOf(flag);
  return i !== -1 && argv[i + 1] ? argv[i + 1] : null;
}

export async function runLoop({
  task,
  workspace,
  maxActions = LIMITS.maxActions,
  maxUsd = LIMITS.maxUsd,
  transcriptPath = null,
  env = process.env,
} = {}) {
  const cfg = modelConfig(env);
  if (!cfg.keyPresent) {
    throw new ModelUnavailable(
      "SPARK_API_KEY is not set; the agent cannot think. meta-agent-login imports it from /etc/metaos/agent.env",
    );
  }
  fs.mkdirSync(workspace, { recursive: true });

  const messages = [
    { role: "system", content: SYSTEM },
    {
      role: "user",
      content:
        "Your orders from the Meta OS board:\n\n" + task +
        "\n\nThe workspace is empty unless your brief says otherwise. Start by " +
        "looking, then act.",
    },
  ];
  const transcript = transcriptPath ? fs.createWriteStream(transcriptPath, { flags: "a" }) : null;
  const say = (event) => {
    if (!transcript) return;
    transcript.write(redact(JSON.stringify({ at: new Date().toISOString(), ...event })) + "\n");
  };

  const usage = { promptTokens: 0, completionTokens: 0, usd: 0, calls: 0 };
  const steps = [];
  let stopped = "actions";
  let summary = null;

  for (let i = 1; i <= maxActions; i += 1) {
    if (usage.usd > maxUsd) { stopped = "budget"; break; }
    let reply;
    try {
      reply = await chat(messages, { maxTokens: 1400, env });
    } catch (error) {
      // A reasoning model can spend the entire allowance on reasoning and
      // return content: null. That is a size problem, not a dead end: retry
      // once with a larger allowance before calling the run failed.
      if (error instanceof ModelError && /no content/.test(error.message)) {
        say({ step: i, notice: "empty content; retrying with a larger token budget" });
        try {
          reply = await chat(messages, { maxTokens: 3200, env });
        } catch (retryError) {
          error = retryError;
        }
      }
      if (!reply) {
        say({ step: i, error: error.message, code: error.code });
        stopped = error.code === "model-unavailable" ? "no-key" : "model-error";
        if (transcript) transcript.end();
        if (error instanceof ModelUnavailable) throw error;
        return { ok: false, stopped, steps, usage, summary: null, error: error.message };
      }
    }
    usage.calls += 1;
    const cost = usageCosts(reply.usage);
    usage.promptTokens += cost.promptTokens;
    usage.completionTokens += cost.completionTokens;
    usage.usd = Math.round((usage.usd + cost.usd) * 1e6) / 1e6;

    messages.push({ role: "assistant", content: reply.content });

    let action;
    try {
      action = parseAction(reply.content);
    } catch (error) {
      say({ step: i, parseError: error.message, reply: reply.content.slice(0, 400) });
      steps.push({ step: i, tool: "(unparsed)", ok: false, error: error.message });
      messages.push({
        role: "user",
        content:
          "TOOL RESULT {\"ok\":false,\"error\":\"your reply was not one JSON " +
          "object: " + error.message + "\"}\nReply again with exactly one JSON object.",
      });
      continue;
    }

    if (action.tool === "finish") {
      summary = String(action.args?.summary || "").slice(0, 2000);
      steps.push({ step: i, tool: "finish", ok: true });
      say({ step: i, tool: "finish", summary });
      stopped = "finished";
      break;
    }

    const result = await execTool(workspace, action.tool, action.args || {});
    const record = {
      step: i,
      tool: action.tool,
      args: action.tool === "write"
        ? { path: action.args?.path, bytes: String(action.args?.content || "").length }
        : action.args,
      ok: Boolean(result.ok),
      ms: result.ms ?? null,
    };
    steps.push(record);
    say({ ...record, result: trimOut(JSON.stringify(result)) });

    messages.push({
      role: "user",
      content: "TOOL RESULT " + JSON.stringify(result),
    });
    // A reasoning model will happily verify forever. When one action is left,
    // say so instead of letting the run end on a silent cap.
    if (i === maxActions - 1) {
      messages.push({
        role: "user",
        content:
          "You have one action left. If the tool results above already show the " +
          "task done, call finish now with the evidence. Otherwise finish and name " +
          "the blocker.",
      });
    }
  }

  if (transcript) transcript.end();
  return {
    ok: stopped === "finished",
    stopped,
    steps,
    usage,
    summary,
    workspace,
    model: cfg.model,
  };
}

async function selfTest() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "meta-agent-selftest-"));
  const rows = [];
  const check = (name, ok, detail = "") => rows.push({ name, ok, detail });

  const w = await execTool(root, "write", { path: "notes/a.txt", content: "hello meta\n" });
  check("write creates parents", w.ok && fs.readFileSync(path.join(root, "notes/a.txt"), "utf8") === "hello meta\n");
  const r = await execTool(root, "read", { path: "notes/a.txt" });
  check("read returns content", r.ok && r.content.includes("hello meta"));
  const l = await execTool(root, "list", { path: "notes" });
  check("list sees the file", l.ok && l.entries.includes("a.txt"));
  const run = await execTool(root, "run", { command: "printf meta | tr a-z A-Z" });
  check("run executes and captures stdout", run.ok && run.stdout.trim() === "META");
  const fail = await execTool(root, "run", { command: "exit 7" });
  check("run reports a nonzero exit", fail.ok === false && fail.code === 7);
  const escape = await execTool(root, "read", { path: "../../etc/passwd" });
  check("path escape is refused", escape.ok === false && /escapes/.test(escape.error));
  const deny = await execTool(root, "run", { command: "sudo rm -rf /" });
  check("dangerous command is refused", deny.ok === false && deny.refused);
  // Prove the strip with a fake key actually present in this process.
  const keep = process.env.SPARK_API_KEY;
  process.env.SPARK_API_KEY = "selftest-not-a-real-key";
  const noKey = await execTool(root, "run", { command: "printf %s \"$SPARK_API_KEY\"" });
  if (keep === undefined) delete process.env.SPARK_API_KEY; else process.env.SPARK_API_KEY = keep;
  check("tool subprocess never sees the key", noKey.stdout === "" && noKey.ok);

  for (const row of rows) console.log((row.ok ? "PASS " : "FAIL ") + row.name + (row.detail ? " — " + row.detail : ""));
  fs.rmSync(root, { recursive: true, force: true });
  const failed = rows.filter((x) => !x.ok).length;
  console.log("agent_loop self-test: " + (rows.length - failed) + "/" + rows.length + " pass");
  process.exit(failed === 0 ? 0 : 1);
}

if (import.meta.url === url.pathToFileURL(process.argv[1]).href) {
  const argv = process.argv.slice(2);
  if (argv.includes("--self-test")) {
    await selfTest();
  } else {
    const cwd = process.cwd();
    const brief = readBrief(cwd);
    const task = argValue(argv, "--task") || brief?.orders || "";
    if (!String(task).trim()) {
      console.error("agent_loop: no orders. Pass --task or run from a relay run dir with brief.json");
      process.exit(5);
    }
    const workspace = path.resolve(argValue(argv, "--workspace") || path.join(cwd, "workspace"));
    const maxActions = Number(argValue(argv, "--max-actions") || brief?.budget?.maxActions || LIMITS.maxActions);
    const maxUsd = Number(argValue(argv, "--max-usd") || brief?.budget?.maxCostUsd || LIMITS.maxUsd);
    const transcriptPath = argValue(argv, "--transcript") || path.join(path.dirname(workspace), "transcript.jsonl");
    const startedAt = new Date().toISOString();
    let result;
    try {
      result = await runLoop({ task, workspace, maxActions, maxUsd, transcriptPath });
    } catch (error) {
      const end = new Date().toISOString();
      const out = {
        ok: false, stopped: error.code === "model-unavailable" ? "no-key" : "error",
        error: redact(error.message), startedAt, endAt: end, workspace,
      };
      fs.writeFileSync(path.join(path.dirname(workspace), "agent-result.json"), JSON.stringify(out, null, 2) + "\n");
      console.error("agent_loop: " + out.error);
      process.exit(error.code === "model-unavailable" ? 4 : 3);
    }
    const out = { ...result, startedAt, endAt: new Date().toISOString() };
    fs.writeFileSync(path.join(path.dirname(workspace), "agent-result.json"), JSON.stringify(out, null, 2) + "\n");
    console.log(
      "agent_loop: " + (result.ok ? "finished" : "stopped:" + result.stopped) +
      " after " + result.steps.length + " steps, " + result.usage.calls + " model calls, " +
      "$" + result.usage.usd.toFixed(4) + " est",
    );
    if (result.summary) console.log("agent_loop: " + result.summary.replace(/\s+/g, " ").slice(0, 400));
    process.exit(result.ok ? 0 : 2);
  }
}
