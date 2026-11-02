// Meta OS agent layer — relay-watchman v1 (AGENT_LAYER_SPEC.md S4).
// The boss's 2026-10-23 design: a tiny always-on NON-agent program.
// It watches the job board; when work lands with an agent's name on
// it, the agent wakes already briefed. The watchman never does the
// work itself — it only rings the bell.
//   node agents/watchman.mjs        (daemon: polls the jobs dir)
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { loadRegistry, spawnAgent, Ledger } from "./runtime.mjs";
import { readBaton, continuationOrders } from "./baton.mjs";

export function createWatchman({ registryFile, root, jobsDir }) {
  const agents = loadRegistry(registryFile);
  fs.mkdirSync(jobsDir, { recursive: true });
  const ledger = new Ledger(path.join(root, "watchman.jsonl"));
  const stateFile = path.join(root, "watchman-state.json");
  let claimed = new Set();
  try { claimed = new Set(JSON.parse(fs.readFileSync(stateFile, "utf8")).claimed || []); } catch {}
  const save = () => fs.writeFileSync(stateFile, JSON.stringify({ claimed: [...claimed] }, null, 2));
  const runs = new Map();

  async function pollOnce() {
    const spawnedNow = [];
    for (const f of fs.readdirSync(jobsDir).filter((x) => x.endsWith(".job.json")).sort()) {
      const jobPath = path.join(jobsDir, f);
      let job;
      try { job = JSON.parse(fs.readFileSync(jobPath, "utf8")); } catch { continue; }
      const id = job.id || f.replace(/\.job\.json$/, "");
      if (claimed.has(id)) continue;
      const agent = agents.find((a) => a.name === job.agent);
      claimed.add(id); save();
      if (!agent) { ledger.add("watchman", "job-unmatched", { id, agent: job.agent }); continue; }
      if (job.continuesFrom) {
        const baton = readBaton(path.join(root, "runs", job.continuesFrom));
        if (baton) {
          job = { ...job, orders: continuationOrders(job.continuesFrom, baton, job.orders || ""), baton };
          ledger.add("watchman", "baton-pass", { id, from: job.continuesFrom });
        } else {
          ledger.add("watchman", "baton-missing", { id, from: job.continuesFrom });
        }
      }
      const h = spawnAgent(agent, { root, job });
      runs.set(id, h);
      ledger.add("watchman", "bell", { id, agent: job.agent, run: h.runId });
      spawnedNow.push({ id, handle: h });
      h.done.then(({ code, signal }) => {
        ledger.add("watchman", "job-done", { id, run: h.runId, code, signal });
        fs.writeFileSync(path.join(jobsDir, id + ".result.json"),
          JSON.stringify({ id, agent: job.agent, run: h.runId, code, signal, ledger: path.join(h.runDir, "ledger.jsonl") }, null, 2));
      });
    }
    return spawnedNow;
  }
  return { pollOnce, ledger, runs };
}

/* ---- daemon ---- */
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const HERE = path.dirname(url.fileURLToPath(import.meta.url));
  const w = createWatchman({ registryFile: path.join(HERE, "registry.json"), root: HERE, jobsDir: path.join(HERE, "jobs") });
  console.log("relay-watchman: watching", path.join(HERE, "jobs"));
  const tick = async () => { await w.pollOnce(); };
  await tick();
  setInterval(tick, 2000);
}
