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
import { writeBeat } from "./watchdog.mjs";

export function createWatchman({ registryFile, root, jobsDir, heartbeatFile = path.join(root, "watchman.heartbeat.json") }) {
  const agents = loadRegistry(registryFile);
  fs.mkdirSync(jobsDir, { recursive: true });
  const ledger = new Ledger(path.join(root, "watchman.jsonl"));
  const stateFile = path.join(root, "watchman-state.json");
  let claimed = new Set();
  // id -> the run it should CONTINUE, when a previous run for the same job died mid-flight.
  // Persisted, so a second restart still resumes instead of starting over.
  let resume = {};
  try {
    const st = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    claimed = new Set(st.claimed || []);
    resume = st.resume || {};
  } catch {}
  const save = () => fs.writeFileSync(stateFile, JSON.stringify({ claimed: [...claimed], resume }, null, 2));
  const runs = new Map();

  function runStatus(runDir) {
    const f = path.join(runDir, "ledger.jsonl");
    if (!fs.existsSync(f)) return { exists: false, exited: false };
    const events = new Ledger(f).read().map((l) => l.event);
    return { exists: true, exited: events.includes("exit") };
  }

  function lastBell(id) {
    let found = null;
    for (const l of ledger.read()) if (l.event === "bell" && l.id === id) found = l;
    return found;
  }

  // Reconcile the claims on disk against what the runs on disk say. Two states are reachable
  // only after a crash, and both used to be permanent:
  //
  //   claimed, no bell      the daemon died between claiming the job and spawning it. Nothing
  //                         ran, so the claim is released and the job is picked up next poll.
  //   bell, run has no exit the daemon (or the runtime) died mid-run. The run is MARKED with
  //                         `run-orphaned` -- so the record says the run did not finish by
  //                         itself -- and the job is re-queued to CONTINUE from that run, which
  //                         is what the baton is for. Starting over would throw away the work.
  function reconcile() {
    const recovered = [];
    for (const id of [...claimed]) {
      if (fs.existsSync(path.join(jobsDir, id + ".result.json"))) continue;   // finished
      const bell = lastBell(id);
      if (!bell) {
        claimed.delete(id);
        recovered.push({ id, action: "unclaimed", reason: "claimed but never spawned" });
        continue;
      }
      const runDir = path.join(root, "runs", bell.run);
      const st = runStatus(runDir);
      if (st.exited) continue;   // finished; a missing result file is not a reason to re-run
      new Ledger(path.join(runDir, "ledger.jsonl")).add(bell.run, "run-orphaned", { seenBy: "watchman-restart" });
      resume[id] = bell.run;
      claimed.delete(id);
      recovered.push({ id, action: "resume", from: bell.run });
    }
    if (recovered.length) save();
    return recovered;
  }

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
      // A job whose previous run died resumes from that run, not from scratch: reconcile()
      // recorded the run id, and the baton pass below turns it into continuation orders.
      if (resume[id]) {
        job = { ...job, continuesFrom: resume[id] };
        delete resume[id];
        save();
        ledger.add("watchman", "resume-from-orphan", { id, from: job.continuesFrom });
      }
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
    // The beat is written after the poll, not before: a beat that lands while the poll is
    // stuck would claim the relay is alive when the thing it exists to do is not happening.
    try { writeBeat(heartbeatFile); } catch { /* a heartbeat failure must not stop the relay */ }
    return spawnedNow;
  }
  const recovered = reconcile();
  // One beat at start-up so a checker run immediately after `node watchman.mjs` sees a live
  // relay rather than a missing file it would have to treat as an alarm.
  try { writeBeat(heartbeatFile); } catch {}
  return { pollOnce, ledger, runs, reconcile, recovered };
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
