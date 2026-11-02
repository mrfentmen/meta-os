// Meta OS agent layer — crew room 1 as a job source (Round 9, D1/D2).
//
// The watchman already drains a jobs directory. What it did not have is a *room*: a place where
// an order is posted as a message, claimed exactly once, and answered where it was asked. This
// module is that boundary, and it is file-backed on purpose — the bus is a message log, and a
// log on disk is the smallest honest stand-in for one during a drill.
//
// Claim-once is the whole correctness argument: `claimJob` renames the job file, and rename is
// atomic on one filesystem. Two relays racing the same job produce one winner and one ENOENT,
// never two runs. A "check then act" would produce two runs the first time two relays started
// together, which is exactly the failure the boss's "claimed once" rule exists to prevent.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export function postJob(roomDir, job) {
  fs.mkdirSync(roomDir, { recursive: true });
  const id = job.id || "job-" + crypto.randomBytes(4).toString("hex");
  const final = path.join(roomDir, id + ".job.json");
  const tmp = final + ".tmp-" + process.pid + "-" + crypto.randomBytes(2).toString("hex");
  fs.writeFileSync(tmp, JSON.stringify({ ...job, id, posted: job.posted || new Date().toISOString() }, null, 2));
  fs.renameSync(tmp, final);   // a reader never sees a half-written post
  return { id, path: final };
}

// Returns the job when this caller won the claim, null when someone else did or it is gone.
export function claimJob(roomDir, id, owner = "relay") {
  const from = path.join(roomDir, id + ".job.json");
  const to = path.join(roomDir, id + "." + owner + ".claim.json");
  try { fs.renameSync(from, to); }
  catch (err) { if (err.code === "ENOENT") return null; throw err; }
  return JSON.parse(fs.readFileSync(to, "utf8"));
}

export function postResult(roomDir, id, result) {
  const final = path.join(roomDir, id + ".result.json");
  const tmp = final + ".tmp-" + process.pid;
  fs.writeFileSync(tmp, JSON.stringify({ id, posted: new Date().toISOString(), ...result }, null, 2));
  fs.renameSync(tmp, final);
  return final;
}

export function listJobs(roomDir) {
  if (!fs.existsSync(roomDir)) return { unclaimed: [], claimed: [], results: [] };
  const files = fs.readdirSync(roomDir).sort();
  const idOf = (f, suffix) => f.slice(0, -suffix.length);
  return {
    unclaimed: files.filter((f) => f.endsWith(".job.json")).map((f) => idOf(f, ".job.json")),
    claimed: files.filter((f) => f.endsWith(".claim.json")).map((f) => f.split(".")[0]),
    results: files.filter((f) => f.endsWith(".result.json")).map((f) => idOf(f, ".result.json")),
  };
}

// Drain everything unclaimed exactly once. `handle(job)` returns the result to post back; a
// throw is posted as a failure result rather than swallowing the job.
export async function drainOnce(roomDir, { owner = "relay", handle } = {}) {
  if (typeof handle !== "function") throw new Error("drainOnce: handle is required");
  const out = [];
  for (const id of listJobs(roomDir).unclaimed) {
    const job = claimJob(roomDir, id, owner);
    if (!job) { out.push({ id, claimed: false }); continue; }   // another relay won
    try {
      const result = await handle(job);
      postResult(roomDir, id, { ok: true, result });
      out.push({ id, claimed: true, ok: true });
    } catch (err) {
      postResult(roomDir, id, { ok: false, error: String(err && err.message || err) });
      out.push({ id, claimed: true, ok: false });
    }
  }
  return out;
}
