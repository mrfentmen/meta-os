// Meta OS agent layer — relay-watchman v1 (docs/AGENT_LAYER_SPEC.md).
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
import { retryJob, proposeJob } from "./jobs.mjs";
import { isStopped } from "./hosted.mjs";
import { createNotifier } from "./notify.mjs";
import {
  claimContinue,
  continueDecision,
  continueJob,
  readContinue,
  writeContinueJob,
} from "./continue.mjs";

export function createWatchman({ registryFile, root, jobsDir, resultDir = jobsDir, heartbeatFile = path.join(root, "watchman.heartbeat.json") }) {
  // The job board and the result board are separate directories on a relay: work arrives on
  // one, receipts go back on the other (R11-256). They default to the same dir so a local
  // board keeps its old shape.
  fs.mkdirSync(resultDir, { recursive: true });
  const agents = loadRegistry(registryFile);
  fs.mkdirSync(jobsDir, { recursive: true });
  const ledger = new Ledger(path.join(root, "watchman.jsonl"));
  // One notifier for the whole relay: alarms dedupe by key, notes always land.
  const notify = createNotifier(root);
  const stateFile = path.join(root, "watchman-state.json");
  let claimed = new Set();
  // A claim that survived a restart but never spawned. It stays in `claimed`
  // (the persisted set is the same set on reload) and is retried once.
  let pending = new Set();
  // id -> the run it should CONTINUE, when a previous run for the same job died mid-flight.
  // Persisted, so a second restart still resumes instead of starting over.
  let resume = {};
  // id -> agent held by a halt file. A halt PAUSES work: the job stays on the
  // board, unclaimed, and runs when the halt is cleared. A refusal here would
  // throw the work away for as long as the stop happens to be in place.
  let halted = new Set();
  try {
    const st = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    claimed = new Set(st.claimed || []);
    pending = new Set(st.pending || []);
    resume = st.resume || {};
    halted = new Set(st.halted || []);
  } catch {}
  const save = () => fs.writeFileSync(stateFile, JSON.stringify({ claimed: [...claimed], pending: [...pending], resume, halted: [...halted] }, null, 2));
  const runs = new Map();

  function runStatus(runDir) {
    const f = path.join(runDir, "ledger.jsonl");
    if (!fs.existsSync(f)) return { exists: false, exited: false };
    const events = new Ledger(f).read().map((l) => l.event);
    return { exists: true, exited: events.includes("exit") };
  }

  // A result file is not proof the job finished: the watchman writes one when its child exits
  // for ANY reason, including a signal. A signaled result is a killed run, and treating it as
  // complete made a restart skip the baton (R12-022). Clean exits finish a job, even nonzero.
  function resultFinished(id) {
    try {
      const r = JSON.parse(fs.readFileSync(path.join(resultDir, id + ".result.json"), "utf8"));
      return r && (r.signal === null || r.signal === undefined);
    } catch { return false; }
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
      if (resultFinished(id)) continue;   // clean exit: finished, even if the code is nonzero
      const bell = lastBell(id);
      if (!bell) {
        // CB-004: the claim survives the reload. Keep it in the persisted
        // set and retry it once, instead of pretending it never happened.
        pending.add(id);
        recovered.push({ id, action: "retry", reason: "claimed but never spawned" });
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
      try { job = JSON.parse(fs.readFileSync(jobPath, "utf8")); }
      catch (err) {
        // Refused and LOGGED. A torn job used to be skipped silently, which made a malformed
        // order indistinguishable from an empty board (R11-288).
        ledger.add("watchman", "job-unreadable", { file: f, reason: String((err && err.message) || err).slice(0, 200) });
        continue;
      }
      const id = job.id || f.replace(/\.job\.json$/, "");
      // A job held by a halt is picked up again only after the halt is gone.
      if (halted.has(id)) {
        if (isStopped(root, job.agent)) continue;
        halted.delete(id);
        // The hold was taken before the spawn, so the claim it made is stale;
        // release both or the job waits for a poll that never comes.
        claimed.delete(id);
        save();
        ledger.add("watchman", "job-resumed", { id, agent: job.agent });
      }
      if (claimed.has(id) && !pending.has(id)) continue;
      if (pending.has(id)) { pending.delete(id); save(); }
      const agent = agents.find((a) => a.name === job.agent);
      claimed.add(id); save();
      if (!agent) {
        ledger.add("watchman", "job-unmatched", { id, agent: job.agent });
        notify({ severity: "note", key: "job:" + id + ":unmatched", title: "Job names no agent",
                 body: "job " + id + " asked for " + job.agent });
        continue;
      }
      // A job whose previous run died resumes from that run, not from scratch: reconcile()
      // recorded the run id, and the baton pass below turns it into continuation orders.
      if (resume[id]) {
        job = { ...job, continuesFrom: resume[id] };
        delete resume[id];
        save();
        ledger.add("watchman", "resume-from-orphan", { id, from: job.continuesFrom });
      }
      if (job.continuesFrom) {
        // A continue job may carry the baton in the order itself. The run's baton.json is
        // preferred because it is the worker's own claim; the carried one is the fallback
        // that keeps a relayed continuation resumable even when that file was never written.
        const baton = readBaton(path.join(root, "runs", job.continuesFrom)) || job.baton || null;
        if (baton) {
          job = { ...job, orders: continuationOrders(job.continuesFrom, baton, job.orders || ""), baton };
          ledger.add("watchman", "baton-pass", { id, from: job.continuesFrom });
        } else {
          ledger.add("watchman", "baton-missing", { id, from: job.continuesFrom });
        }
      }
      // A draft has no program. Spawning it would start nothing and file a
      // finished job; refuse it here, by name.
      if (agent.draft === true || !Array.isArray(agent.command) || agent.command.length === 0) {
        ledger.add("watchman", "job-refused", { id, agent: job.agent, reason: "draft-agent" });
        notify({ severity: "note", key: "job:" + id + ":draft",
                 title: "No program for " + job.agent,
                 body: "the registry entry is a draft; nothing was started" });
        fs.writeFileSync(path.join(resultDir, id + ".result.json"),
          JSON.stringify({ id, agent: job.agent, refused: "draft-agent",
                           finishedAt: new Date().toISOString() }, null, 2));
        continue;
      }
      // A person can halt one agent by dropping stop/<name>.STOP. The runtime
      // honours a STOP inside a run, but a job written while the agent is
      // halted would otherwise start anyway -- a stop that only stops work
      // already begun is not a stop.
      if (isStopped(root, job.agent)) {
        // Hold it, do not judge it. The ledger says once why the job is waiting,
        // and no result file is written -- nothing ran and nothing was refused.
        halted.add(id);
        save();
        ledger.add("watchman", "job-halted", { id, agent: job.agent, reason: "stop-filed" });
        notify({ severity: "note", key: "job:" + id + ":halted",
                 title: "Agent is halted: " + job.agent,
                 body: "stop file present; job " + id + " waits on the board" });
        continue;
      }
      const runStartedAt = Date.now();
      const h = spawnAgent(agent, { root, job });
      runs.set(id, h);
      // A refused spawn (budget or memory) has no child and never will. Recording a bell and
      // a job-done for it made a job that never ran look finished. Name the refusal, write a
      // result that says so, and leave the job claimed so the poll does not spin on it.
      if (h.stopped) {
        ledger.add("watchman", "job-refused", { id, agent: job.agent, run: h.runId, reason: h.stopped });
        notify({ severity: "alarm", key: "job:" + id + ":refused",
                 title: "Agent job refused: " + job.agent,
                 body: (job.orders || "(no orders)") + " — " + h.stopped });
        fs.writeFileSync(path.join(resultDir, id + ".result.json"),
          JSON.stringify({ id, agent: job.agent, run: h.runId, refused: h.stopped,
                           finishedAt: new Date().toISOString() }, null, 2));
        continue;
      }
      ledger.add("watchman", "bell", { id, agent: job.agent, run: h.runId });
      spawnedNow.push({ id, handle: h });
      h.done.then(({ code, signal }) => {
        ledger.add("watchman", "job-done", { id, run: h.runId, code, signal });
        // A signal or a nonzero exit is an alarm; a clean exit is a quiet note.
        // Both are deduplicated by job id, so a retry storm cannot ring forever.
        const failed = signal !== null || (code !== 0 && code !== null);
        notify(failed
          ? { severity: "alarm", key: "job:" + id + ":failed",
              title: "Agent job failed: " + job.agent,
              body: "exit " + code + (signal ? " signal " + signal : "") }
          : { severity: "note", key: "job:" + id + ":done",
              title: "Agent job finished: " + job.agent, body: "exit " + code });
        // A run may ask to continue instead of finishing. The request is bounded before a
        // new job is written, and it is queued before the request file is archived -- so a
        // crash in between replays an idempotent write, never loses the continuation.
        let continuation = { requested: false, queued: false, reason: null };
        try {
          const request = readContinue(h.runDir);
          if (request) {
            continuation.requested = true;
            const cycles = Number(job.continueCycles) || 0;
            const verdict = continueDecision(h.runDir, {
              cycles,
              maxContinues: job.maxContinues == null ? 4 : Number(job.maxContinues),
              elapsedMs: Date.now() - runStartedAt,
              maxWallMs: agent.budget && agent.budget.maxWallMs,
              costUsd: job.estimatedCostUsd,
              maxCostUsd: agent.budget && agent.budget.maxCostUsd,
              exitCode: code,
            });
            if (verdict.continue) {
              const nextJob = continueJob({ job, runId: h.runId, request, cycles });
              writeContinueJob(jobsDir, nextJob);
              continuation.queued = true;
              ledger.add("watchman", "continue-queued", { id, run: h.runId, next: nextJob.id, cycle: cycles + 1 });
            } else {
              continuation.reason = verdict.reason;
              ledger.add("watchman", "continue-refused", { id, run: h.runId, reason: verdict.reason });
              notify({ severity: "note", key: "job:" + id + ":continue-refused",
                       title: "Continue refused", body: verdict.reason });
            }
            claimContinue(h.runDir);
          }
        } catch (err) {
          continuation.reason = "continue-error";
          ledger.add("watchman", "continue-error", { id, run: h.runId, reason: String((err && err.message) || err).slice(0, 200) });
        }
        fs.writeFileSync(path.join(resultDir, id + ".result.json"),
          JSON.stringify({ id, agent: job.agent, run: h.runId, code, signal, finishedAt: new Date().toISOString(), ledger: path.join(h.runDir, "ledger.jsonl"), continue: continuation }, null, 2));

        // One automatic retry, continued from the run that died. A layer that
        // only alarms on a crash is a layer a person has to nanny; the baton
        // already holds the work, so spending it costs one more run and no
        // thought. A job that already asked to continue is left alone, and a
        // retry is stamped so it cannot spawn another one.
        if (failed && !continuation.queued && job.autoRetried !== true) {
          try {
            const retry = retryJob({ root, id, mark: { autoRetried: true } });
            if (retry.ok) {
              ledger.add("watchman", "job-retry", { id, next: retry.id, from: h.runId, existing: retry.existing });
              notify({ severity: "note", key: "job:" + id + ":retry",
                       title: "Agent job retried: " + job.agent,
                       body: "exit " + code + (signal ? " signal " + signal : "")
                         + " — continuing from " + h.runId });
            } else {
              ledger.add("watchman", "retry-refused", { id, reason: retry.reason });
            }
          } catch (err) {
            ledger.add("watchman", "retry-error", { id, reason: String((err && err.message) || err).slice(0, 200) });
          }
        }

        // A run that finished its work may name the next piece on its baton
        // (`next`). Queue it for the same agent: this is what lets the relay
        // keep moving without a person deciding every step. A failed or
        // continuing run is not asked -- one has not learned enough to order
        // more work, the other already has its own ceiling.
        if (!failed && !continuation.queued) {
          try {
            const baton = readBaton(h.runDir);
            const proposal = proposeJob({ root, id, runId: h.runId, next: baton && baton.next });
            if (proposal.ok) {
              ledger.add("watchman", "proposal-queued", { id, run: h.runId, next: proposal.id });
              notify({ severity: "note", key: "job:" + id + ":proposed",
                       title: "Agent proposed its next job: " + job.agent, body: proposal.order });
            } else if (proposal.reason !== "no next order on the baton") {
              ledger.add("watchman", "proposal-refused", { id, reason: proposal.reason });
            }
          } catch (err) {
            ledger.add("watchman", "proposal-error", { id, reason: String((err && err.message) || err).slice(0, 200) });
          }
        }
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
  return { pollOnce, ledger, runs, reconcile, recovered,
    // CB-004: read-only view of persisted claims, for restart tests.
    state: () => ({ claimed: [...claimed], pending: [...pending], resume: { ...resume } }) };
}

/* ---- daemon ---- */
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const HERE = path.dirname(url.fileURLToPath(import.meta.url));
  // The image keeps the code read-only under /usr/share and writes state in the
  // user's own directory, so the CLI has to accept a root. Defaults stay HERE,
  // which is what every existing caller and test expects.
  const arg = (name) => {
    const i = process.argv.indexOf(name);
    return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : null;
  };
  const root = arg("--root") ? path.resolve(arg("--root")) : HERE;
  const jobsDir = arg("--jobs") ? path.resolve(arg("--jobs")) : path.join(root, "jobs");
  const registryFile = arg("--registry")
    ? path.resolve(arg("--registry"))
    : path.join(HERE, "registry.json");
  const w = createWatchman({ registryFile, root, jobsDir });
  console.log("relay-watchman: watching", jobsDir);
  const tick = async () => { await w.pollOnce(); };
  await tick();
  // --once makes the watchman a hosted loop command: one drain, exit 0. A daemon never returns,
  // so a registry entry pointing at it without this flag would sit until its budget killed it
  // (R12-009).
  if (process.argv.includes("--once")) process.exit(0);
  setInterval(tick, 2000);
}
