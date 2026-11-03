// Meta OS agent layer — read the board.
//
// A board with no view is a rumour. This reads the jobs directory, the relay
// ledger and the result files, and says where each job actually stands:
//
//   queued     a job file is there, nothing has claimed it
//   running    the ledger has a bell and no result yet
//   done       a result exists and the run exited cleanly
//   failed     a result exists with a nonzero code or a signal
//   refused    the layer refused the spawn (draft, budget, memory)
//   unreadable the job file does not parse; it is shown, not skipped
//
// It writes nothing.
//
//   node agents/jobs.mjs [--root DIR] [--json]
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

export function readLedger(file) {
  if (!fs.existsSync(file)) return [];
  const events = [];
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line) continue;
    try {
      events.push(JSON.parse(line));
    } catch {
      // A torn line is a crash, not a reason to hide the rest of the history.
    }
  }
  return events;
}

export function board({ root }) {
  const jobsDir = path.join(root, "jobs");
  const ledgerFile = path.join(root, "watchman.jsonl");
  const events = readLedger(ledgerFile);

  const bell = new Map();
  const done = new Map();
  const refused = new Map();
  for (const event of events) {
    if (!event || typeof event.id !== "string") continue;
    if (event.event === "bell") bell.set(event.id, event);
    if (event.event === "job-done") done.set(event.id, event);
    if (event.event === "job-refused") refused.set(event.id, event);
  }

  const rows = [];
  let files = [];
  try {
    files = fs.readdirSync(jobsDir).filter((name) => name.endsWith(".job.json")).sort();
  } catch {
    return { root, rows, counts: tally(rows) };
  }

  for (const file of files) {
    const id = file.replace(/\.job\.json$/, "");
    const row = { id, agent: null, state: "queued", code: null, reason: null, file };
    try {
      const job = JSON.parse(fs.readFileSync(path.join(jobsDir, file), "utf8"));
      row.agent = job.agent || null;
    } catch {
      row.state = "unreadable";
      rows.push(row);
      continue;
    }

    const resultFile = path.join(jobsDir, id + ".result.json");
    if (fs.existsSync(resultFile)) {
      try {
        const result = JSON.parse(fs.readFileSync(resultFile, "utf8"));
        row.code = result.code == null ? null : result.code;
        if (result.refused) {
          row.state = "refused";
          row.reason = result.refused;
        } else if (result.signal != null || (typeof result.code === "number" && result.code !== 0)) {
          row.state = "failed";
          row.reason = result.signal ? "signal " + result.signal : "exit " + result.code;
        } else {
          row.state = "done";
        }
        rows.push(row);
        continue;
      } catch {
        row.state = "unreadable";
        rows.push(row);
        continue;
      }
    }

    if (refused.has(id)) {
      row.state = "refused";
      row.reason = refused.get(id).reason || "refused";
    } else if (bell.has(id)) {
      row.state = done.has(id) ? "done" : "running";
    }
    rows.push(row);
  }

  return { root, rows, counts: tally(rows) };
}

function tally(rows) {
  const counts = { queued: 0, running: 0, done: 0, failed: 0, refused: 0, unreadable: 0 };
  for (const row of rows) counts[row.state] += 1;
  return counts;
}

// A failed run left a baton; a refused one never started. Only the first is
// retryable -- re-queuing a refusal would spin on the same missing entry.
// The new job carries `continuesFrom`, so the watchman resumes from the run
// that died instead of starting the work over.
export function retryJob({ root, id, mark = {} }) {
  const jobsDir = path.join(root, "jobs");
  const jobFile = path.join(jobsDir, id + ".job.json");
  const resultFile = path.join(jobsDir, id + ".result.json");
  if (!fs.existsSync(jobFile)) return { ok: false, reason: "no job " + id };
  let job;
  try {
    job = JSON.parse(fs.readFileSync(jobFile, "utf8"));
  } catch {
    return { ok: false, reason: "job " + id + " does not parse; fix it by hand" };
  }
  if (!fs.existsSync(resultFile)) {
    return { ok: false, reason: "job " + id + " has no result yet; it has not failed" };
  }
  let result;
  try {
    result = JSON.parse(fs.readFileSync(resultFile, "utf8"));
  } catch {
    return { ok: false, reason: "result for " + id + " does not parse" };
  }
  if (result.refused) {
    return { ok: false, reason: "job " + id + " was refused (" + result.refused + "); fix the entry, do not re-queue" };
  }
  if (result.signal == null && result.code === 0) {
    return { ok: false, reason: "job " + id + " finished cleanly; nothing to retry" };
  }
  if (!result.run) {
    return { ok: false, reason: "result for " + id + " names no run; no baton to continue from" };
  }

  const base = id.replace(/-r\d+$/, "");
  const attempt = Number((id.match(/-r(\d+)$/) || [])[1] || 1);
  const nextId = base + "-r" + (attempt + 1);
  const nextFile = path.join(jobsDir, nextId + ".job.json");
  // Idempotent: asking twice returns the same retry instead of stacking them.
  if (fs.existsSync(nextFile)) {
    return { ok: true, id: nextId, continuesFrom: result.run, existing: true };
  }

  const next = {
    ...job,
    id: nextId,
    retryOf: id,
    continuesFrom: result.run,
    createdAt: new Date().toISOString(),
    // `mark` lets the watchman stamp a retry as automatic, so the retry
    // itself cannot spawn another one and loop forever.
    ...mark,
  };
  const tmp = nextFile + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(next, null, 2));
  fs.renameSync(tmp, nextFile);
  return { ok: true, id: nextId, continuesFrom: result.run, existing: false };
}

// A run that finishes its work can say what it would do next. That is the
// difference between a queue and a relay: the layer does not need a person to
// decide the next job, because the worker that just learned the ground hands
// the next order back to itself.
//
//   baton.next = "sweep the second shelf"   ->   job <id>-n1, same agent
//
// Bounded on purpose. One proposal per finished job unless the job says
// otherwise, never a proposal that repeats the order it answered, and never
// from a job that already asked to continue (that path has its own ceiling).
// A layer that can task itself forever is a layer that never stops spending.
export const PROPOSAL_LIMIT = 1;
const PROPOSAL_SUFFIX = /-n(\d+)$/;

export function proposeJob({ root, id, runId, next, mark = {} }) {
  const jobsDir = path.join(root, "jobs");
  const jobFile = path.join(jobsDir, id + ".job.json");
  let job;
  try {
    job = JSON.parse(fs.readFileSync(jobFile, "utf8"));
  } catch {
    return { ok: false, reason: "job " + id + " does not parse; cannot propose from it" };
  }
  if (typeof next !== "string" || next.trim() === "") {
    return { ok: false, reason: "no next order on the baton" };
  }
  const order = next.trim();
  // Echoing the orders just done is a loop wearing a new name. Refuse it by
  // name so the ledger shows why the chain stops.
  if (typeof job.orders === "string" && job.orders.trim() === order) {
    return { ok: false, reason: "proposal-echo" };
  }
  const made = Number(job.proposals) || 0;
  const limit = job.maxProposals == null ? PROPOSAL_LIMIT : Number(job.maxProposals);
  if (!(made < limit)) {
    return { ok: false, reason: "proposal-limit" };
  }
  const base = id.replace(PROPOSAL_SUFFIX, "").replace(/-r\d+$/, "");
  const chain = Number((id.match(PROPOSAL_SUFFIX) || [])[1] || 0);
  const nextId = base + "-n" + (chain + 1);
  const nextFile = path.join(jobsDir, nextId + ".job.json");
  // Idempotent: asking twice returns the same job instead of stacking two.
  if (fs.existsSync(nextFile)) return { ok: true, id: nextId, existing: true };

  const proposal = {
    id: nextId,
    agent: job.agent,
    orders: order,
    lane: job.lane == null ? null : job.lane,
    proposedBy: runId || null,
    fromJob: id,
    proposals: made + 1,
    maxProposals: limit,
    ...mark,
    createdAt: new Date().toISOString(),
  };
  fs.mkdirSync(jobsDir, { recursive: true });
  const tmp = nextFile + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(proposal, null, 2));
  fs.renameSync(tmp, nextFile);

  // Record the count on the job that proposed, so the next poll can tell the
  // limit was spent without reading the whole board.
  try {
    fs.writeFileSync(jobFile, JSON.stringify({ ...job, proposals: made + 1 }, null, 2));
  } catch {
    // The new job is already on disk; a lost counter only means one more
    // proposal could be asked for, never that work is lost.
  }
  return { ok: true, id: nextId, existing: false, order };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const arg = (name, fallback = null) => {
    const i = process.argv.indexOf(name);
    return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
  };
  const root = path.resolve(arg("--root", process.cwd()));
  if (!fs.existsSync(path.join(root, "jobs"))) {
    console.error("jobs: no board at " + path.join(root, "jobs"));
    process.exit(2);
  }
  const proposeId = arg("--propose");
  if (proposeId) {
    const next = arg("--next");
    const out = proposeJob({ root, id: proposeId, runId: arg("--run"), next });
    if (!out.ok) {
      console.error("jobs: " + out.reason);
      process.exit(1);
    }
    console.log("jobs: " + (out.existing ? "already on the board " : "proposed ") + out.id);
    process.exit(0);
  }
  const retryId = arg("--retry");
  if (retryId) {
    const out = retryJob({ root, id: retryId });
    if (!out.ok) {
      console.error("jobs: " + out.reason);
      process.exit(1);
    }
    console.log("jobs: " + (out.existing ? "already re-queued " : "re-queued ")
      + out.id + " from run " + out.continuesFrom);
    process.exit(0);
  }
  const result = board({ root });
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }
  // console.log's format has no width flags: "%-9s" would print literally.
  const width = Math.max(2, ...result.rows.map((row) => String(row.id).length));
  for (const row of result.rows) {
    const detail = row.reason || (row.code == null ? "" : "exit " + row.code);
    console.log(
      String(row.id).padEnd(width) + "  " +
      row.state.padEnd(9) + " " +
      (row.agent || "-").padEnd(18) + " " +
      detail
    );
  }
  const c = result.counts;
  console.log(
    "%d job(s): %d queued, %d running, %d done, %d failed, %d refused, %d unreadable",
    result.rows.length, c.queued, c.running, c.done, c.failed, c.refused, c.unreadable
  );
}
