#!/usr/bin/env node
// evals/agentic/run.mjs — does the Meta OS agent actually finish work?
//
// Two parts, both real:
//   PART 1  the loop: each task's fixture is copied into a fresh workspace, the
//           agent gets the orders, and a shell grader decides pass/fail from the
//           files on disk. No model judges, no self-report scoring.
//   PART 2  the relay: the same agent is started through agents/runtime.mjs
//           (registry entry, brief.json, ledger) the way the OS starts it, and
//           the file it was told to make is checked.
//
//   node evals/agentic/run.mjs [--only 03] [--max-usd 0.20] [--keep]
//
// Writes evals/agentic/report-<stamp>.md and .json. Never prints the key.
// Exits 1 when any task fails, so it can gate a build.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { spawn, spawnSync } from "node:child_process";
import { runLoop } from "../../agents/agent_loop.mjs";
import { modelConfig } from "../../agents/model_client.mjs";
import { loadRegistry, spawnAgent } from "../../agents/runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "../..");
const TASKS_DIR = path.join(HERE, "tasks");

function arg(flag, fallback = null) {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

function stamp() {
  return new Date().toISOString().replace(/[:.]/g, "-").replace(/Z$/, "Z");
}

function runShell(cwd, file) {
  return spawnSync("bash", [file], { cwd, encoding: "utf8", timeout: 30000 });
}

function sh(cwd, command) {
  return spawnSync("bash", ["-lc", command], { cwd, encoding: "utf8", timeout: 60000 });
}

async function partLoop(tasks, { maxUsd, keep }) {
  const rows = [];
  for (const task of tasks) {
    const dir = path.join(TASKS_DIR, task);
    const orders = fs.readFileSync(path.join(dir, "task.md"), "utf8");
    // One directory per task, with the workspace inside it: transcripts from
    // different tasks must never land on the same path.
    const runDir = fs.mkdtempSync(path.join(os.tmpdir(), "meta-eval-" + task + "-"));
    const workspace = path.join(runDir, "workspace");
    fs.mkdirSync(workspace);
    const seed = runShell(workspace, path.join(dir, "setup.sh"));
    if (seed.status !== 0) {
      rows.push({ id: task, pass: false, why: "fixture setup failed: " + (seed.stderr || "").slice(0, 200) });
      continue;
    }
    let result;
    let error = null;
    try {
      result = await runLoop({
        task: orders,
        workspace,
        maxActions: 14,
        maxUsd,
        transcriptPath: path.join(runDir, "transcript.jsonl"),
      });
    } catch (e) {
      error = e.message;
    }
    const grade = error ? null : runShell(workspace, path.join(dir, "grade.sh"));
    const pass = !error && grade.status === 0;
    rows.push({
      id: task,
      pass,
      why: error ? "error: " + error : pass ? "grader exit 0" : "grader exit " + grade.status + ": " +
        (grade.stderr || grade.stdout || "").trim().split("\n").slice(0, 3).join(" | ").slice(0, 300),
      finished: Boolean(result?.ok),
      stopped: result?.stopped ?? null,
      steps: result?.steps?.length ?? 0,
      calls: result?.usage?.calls ?? 0,
      usd: result?.usage?.usd ?? 0,
      tools: (result?.steps || []).map((s) => s.tool).join(","),
      workspace: keep ? runDir : null,
    });
    if (!keep) fs.rmSync(runDir, { recursive: true, force: true });
    process.stdout.write((pass ? "PASS " : "FAIL ") + task + " — " + rows[rows.length - 1].why + "\n");
  }
  return rows;
}

async function partRelay() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "meta-eval-relay-"));
  let agents;
  try {
    agents = loadRegistry(path.join(REPO, "agents/registry.json"));
  } catch (error) {
    return { pass: false, why: "registry did not load: " + error.message };
  }
  const agent = agents.find((a) => a.name === "meta-coder");
  if (!agent) return { pass: false, why: "no meta-coder entry in the registry" };
  const orders =
    "Create relay.txt in the workspace containing exactly RELAY_OK followed by a newline, " +
    "then verify it with cat and finish.";
  const handle = spawnAgent(agent, { root, job: { orders }, repoRoot: REPO });
  const code = await handle.done;
  const file = path.join(handle.runDir, "workspace", "relay.txt");
  const body = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null;
  const brief = JSON.parse(fs.readFileSync(path.join(handle.runDir, "brief.json"), "utf8"));
  const pass = body === "RELAY_OK\n";
  return {
    pass,
    why: pass ? "relay run " + handle.runId + " wrote relay.txt" : "relay run " + handle.runId +
      " exit " + code.code + "; relay.txt " + (body === null ? "missing" : JSON.stringify(body)),
    run: handle.runId,
    exit: code.code,
    briefOrders: brief.orders.slice(0, 120),
    root,
  };
}

function report({ rows, relay, maxUsd, startedAt }) {
  const passed = rows.filter((r) => r.pass).length;
  const calls = rows.reduce((n, r) => n + (r.calls || 0), 0);
  const usd = rows.reduce((n, r) => n + (r.usd || 0), 0);
  const lines = [
    "# Meta OS agentic eval — " + startedAt,
    "",
    "Model: `muse-spark-1.3` via api.meta.ai. Scoring: a shell grader per task, run on the",
    "files the agent actually wrote. The agent's own \"done\" is recorded but never scored.",
    "",
    "## Score",
    "",
    "| | |",
    "|---|---|",
    "| tasks passed | **" + passed + " / " + rows.length + "** |",
    "| model calls | " + calls + " |",
    "| est. spend | $" + usd.toFixed(4) + " (cap $" + maxUsd + " per task) |",
    "| relay path | " + (relay.pass ? "PASS" : "FAIL") + " — " + relay.why + " |",
    "",
    "## Per task",
    "",
    "| task | pass | agent finished | steps | calls | est. $ | grader |",
    "|---|---|---|---|---|---|---|",
    ...rows.map((r) =>
      "| " + r.id + " | " + (r.pass ? "✅" : "❌") + " | " + (r.finished ? "yes" : "no") +
      " | " + (r.steps ?? "-") + " | " + (r.calls ?? "-") + " | " + (r.usd ? r.usd.toFixed(4) : "-") +
      " | " + String(r.why || "").replace(/\|/g, "\\|") + " |"),
    "",
    "## What this does not prove",
    "",
    "- It does not prove the GUI: these runs happen on the host and in the relay, not on X.",
    "- `muse-spark-1.3` is a reasoning model; a task can fail on the action cap rather than",
    "  on understanding, and the table shows `finished: no` when that happens.",
    "- The price column is a local estimate (env `METAOS_PRICE_*`), not an invoice.",
  ];
  return lines.join("\n") + "\n";
}

const startedAt = new Date().toISOString();
const maxUsd = Number(arg("--max-usd", "0.06"));
const keep = process.argv.includes("--keep");
const cfg = modelConfig();
if (!cfg.keyPresent) {
  console.error("eval: SPARK_API_KEY is not set — refusing to write an empty report");
  process.exit(4);
}

const only = arg("--only");
const all = fs.readdirSync(TASKS_DIR).filter((d) => fs.statSync(path.join(TASKS_DIR, d)).isDirectory()).sort();
const tasks = only ? all.filter((t) => t.startsWith(only)) : all;
console.log("eval: " + tasks.length + " tasks, model " + cfg.model + ", cap $" + maxUsd + "/task");

const rows = await partLoop(tasks, { maxUsd, keep });
const relay = await partRelay();
console.log((relay.pass ? "PASS " : "FAIL ") + "relay — " + relay.why);

const md = report({ rows, relay, maxUsd, startedAt });
const outBase = path.join(HERE, "report-" + stamp());
fs.writeFileSync(outBase + ".md", md);
fs.writeFileSync(
  outBase + ".json",
  JSON.stringify({ startedAt, model: cfg.model, maxUsd, rows, relay: { ...relay, root: undefined } }, null, 2) + "\n",
);
console.log("eval: report " + outBase + ".md");
const failed = rows.filter((r) => !r.pass).length + (relay.pass ? 0 : 1);
console.log("eval: " + (tasks.length - rows.filter((r) => !r.pass).length) + "/" + rows.length + " tasks + relay " +
  (relay.pass ? "pass" : "FAIL"));
process.exit(failed === 0 ? 0 : 1);
