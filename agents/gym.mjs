// Meta OS Gym — agents train before real work (BUILD_WAVE W5, first slice).
// A drill is one agent, three tasks, run against the real agent runtime
// (agents/runtime.mjs, no mocks): the entry loads, the agent spawns to a
// clean exit, and the run ledger reads back complete. Each task scores 0/1.
// Scores land in two places the wave names: the gym ledger
// (agents/gym-ledger.jsonl, append-only, one event per task plus a total)
// and the agent's registry entry, which carries its gym record.
//   node agents/gym.mjs drill <name> [--record]
//     --record also writes the gym record onto the agent's registry entry
//     and appends the scores to agents/gym-ledger.jsonl.
//   node agents/gym.mjs tasks
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { loadRegistry, spawnAgent, Ledger } from "./runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
export const REGISTRY_FILE = path.join(HERE, "registry.json");
export const GYM_LEDGER_FILE = path.join(HERE, "gym-ledger.jsonl");

export const TASKS = [
  { id: "registry-entry", what: "registry entry loads with a name, a command, and a budget" },
  { id: "spawn-clean-exit", what: "real spawn through the runtime exits 0 and writes its brief" },
  { id: "ledger-complete", what: "run ledger reads back spawn then exit, in order, no torn lines" },
];

// Run one drill. runRoot defaults to a temp dir so drill runs never litter
// the repo; the scores themselves persist via the gym ledger + registry.
export async function runGymDrill({ registryFile = REGISTRY_FILE, agentName, runRoot = null } = {}) {
  const agents = loadRegistry(registryFile);
  const agent = agents.find((a) => a.name === agentName);
  if (!agent) throw new Error("gym: no such agent: " + agentName);
  const root = runRoot || fs.mkdtempSync(path.join(os.tmpdir(), "gym-drill-"));
  const results = [];

  // Task 1: the entry itself.
  results.push({
    id: "registry-entry",
    score: agent.name && Array.isArray(agent.command) && agent.command.length > 0 && agent.budget ? 1 : 0,
    max: 1,
  });

  // Tasks 2+3: one real spawn, judged two ways.
  const handle = spawnAgent(agent, { root, job: { orders: "gym drill" } });
  const { code } = await handle.done;
  let briefOk = false;
  try {
    const brief = JSON.parse(fs.readFileSync(path.join(handle.runDir, "brief.json"), "utf8"));
    briefOk = brief.agent === agent.name;
  } catch { briefOk = false; }
  results.push({ id: "spawn-clean-exit", score: code === 0 && briefOk ? 1 : 0, max: 1 });

  const events = handle.ledger.read().map((l) => l.event);
  results.push({
    id: "ledger-complete",
    score: events[0] === "spawn" && events[events.length - 1] === "exit" && events.length >= 2 ? 1 : 0,
    max: 1,
  });

  return {
    drill: "gym-drill-1",
    agent: agent.name,
    at: new Date().toISOString(),
    tasks: results,
    total: results.reduce((s, t) => s + t.score, 0),
    max: results.reduce((s, t) => s + t.max, 0),
    runDir: handle.runDir,
  };
}

// Write the drill record onto the agent's registry entry (other entries and
// fields untouched) and append the scores to the gym ledger.
export function recordGymResult({ registryFile = REGISTRY_FILE, gymLedgerFile = GYM_LEDGER_FILE, result }) {
  const raw = JSON.parse(fs.readFileSync(registryFile, "utf8"));
  const entry = raw.agents.find((a) => a.name === result.agent);
  if (!entry) throw new Error("gym: no such agent in registry: " + result.agent);
  entry.gym = {
    drill: result.drill,
    at: result.at,
    tasks: result.tasks,
    total: result.total,
    max: result.max,
  };
  // registry.json is 1-space indent, no trailing newline, non-ASCII escaped
  // (e.g. \u2014); keep all three so a record update touches one entry,
  // not the whole file.
  const text = JSON.stringify(raw, null, 1)
    .replace(/[^\x00-\x7F]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
  fs.writeFileSync(registryFile, text);
  const ledger = new Ledger(gymLedgerFile);
  for (const t of result.tasks) ledger.add(result.agent, "gym-task-score", { drill: result.drill, task: t.id, score: t.score, max: t.max });
  // CB-010: a failed task leaves its own record, with the step named, so a
  // drill cannot report a total without saying what failed.
  for (const t of result.tasks) {
    if (t.score < t.max) ledger.add(result.agent, "gym-fail", { drill: result.drill, task: t.id, score: t.score, max: t.max });
  }
  ledger.add(result.agent, "gym-total", { drill: result.drill, total: result.total, max: result.max });
  return entry.gym;
}

/* ---- CLI ---- */
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const [, , cmd, name, flag] = process.argv;
  if (cmd === "tasks") {
    for (const t of TASKS) console.log(t.id, "—", t.what);
  } else if (cmd === "drill" && name) {
    const result = await runGymDrill({ agentName: name });
    for (const t of result.tasks) console.log(t.id, t.score + "/" + t.max);
    console.log("total", result.total + "/" + result.max);
    if (flag === "--record") {
      recordGymResult({ result });
      console.log("recorded on registry entry", name, "+ gym ledger");
    }
  } else {
    console.error("usage: gym.mjs tasks | drill <name> [--record]");
    process.exit(1);
  }
}
