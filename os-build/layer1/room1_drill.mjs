// Round 9 D1/D2 — the room-1 drill. Real watchman, real child process, real ledger.
//
//   node os-build/layer1/room1_drill.mjs
//
// D1: an order posted to the room is claimed once, written into the watchman's job board,
//     spawned with a brief that carries the order, and its result posted back to the room.
// D2: with no relay running a job lands, nothing runs, and after the relay starts the job runs
//     exactly once -- a second poll does not run it again.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { createWatchman } from "../../agents/watchman.mjs";
import { postJob, drainOnce, listJobs, postResult } from "../../agents/room1.mjs";
import { Ledger } from "../../agents/runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..", "..");
const NODE = process.execPath;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const root = fs.mkdtempSync(path.join(os.tmpdir(), "room1-drill-"));
const roomDir = path.join(root, "room-1");
const jobsDir = path.join(root, "jobs");
const registryFile = path.join(root, "registry.json");

// A real agent: a node process that reads its brief, writes proof it was briefed, and exits 0.
const agentScript = `
const fs = require("fs");
const brief = JSON.parse(fs.readFileSync("brief.json", "utf8"));
fs.writeFileSync("done.txt", "orders=" + brief.orders);
`;
fs.writeFileSync(registryFile, JSON.stringify({ agents: [
  { name: "drill-agent", command: [NODE, "-e", agentScript], budget: { maxWallMs: 10000 } },
]}));

const results = [];
const check = (name, ok, detail = "") => { results.push({ name, ok, detail }); };

function watchman() {
  return createWatchman({ registryFile, root, jobsDir });
}

async function waitForResult(id, ms = 8000) {
  const at = path.join(jobsDir, id + ".result.json");
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (fs.existsSync(at)) return JSON.parse(fs.readFileSync(at, "utf8"));
    await sleep(25);
  }
  return null;
}

// ---------- D1 ----------
{
  const b = watchman();
  const { id } = postJob(roomDir, { id: "d1", agent: "drill-agent", orders: "D1: post, claim, spawn briefed, answer" });
  const drained = await drainOnce(roomDir, {
    owner: "d1",
    handle: async (job) => {
      fs.writeFileSync(path.join(jobsDir, job.id + ".job.json"), JSON.stringify(job));
      await b.pollOnce();
      const r = await waitForResult(job.id);
      if (!r) throw new Error("no result after spawn");
      return r;
    },
  });
  const jobs = listJobs(roomDir);
  const resultFile = path.join(roomDir, "d1.result.json");
  check("D1 claimed once", drained.length === 1 && drained[0].claimed === true && jobs.claimed.length === 1, JSON.stringify(jobs));
  check("D1 nothing unclaimed left", jobs.unclaimed.length === 0);
  check("D1 result posted back to the room", fs.existsSync(resultFile));
  const posted = fs.existsSync(resultFile) ? JSON.parse(fs.readFileSync(resultFile, "utf8")) : {};
  check("D1 result says it ran", posted.ok === true && posted.result && posted.result.code === 0, JSON.stringify(posted).slice(0, 160));

  const briefs = [];
  for (const d of fs.readdirSync(path.join(root, "runs"))) {
    const bf = path.join(root, "runs", d, "brief.json");
    if (fs.existsSync(bf)) briefs.push(JSON.parse(fs.readFileSync(bf, "utf8")));
  }
  const brief = briefs[0] || {};
  check("D1 the agent opened with the order in its brief", String(brief.orders || "").startsWith("D1:"), JSON.stringify(brief).slice(0, 120));
  const donePath = brief.run ? path.join(root, "runs", brief.run, "done.txt") : null;
  check("D1 the agent read the brief and acted", donePath && fs.existsSync(donePath) && fs.readFileSync(donePath, "utf8").startsWith("orders=D1:"), donePath || "(no run)");

  const events = b.ledger.read().map((l) => l.event);
  check("D1 watchman ledger has the bell", events.includes("bell"), events.join(","));
  check("D1 watchman ledger has the completion", events.includes("job-done"), events.join(","));
}

// ---------- D2 ----------
{
  // No watchman is running in this block until the restart. The job lands while the relay is
  // down: the room holds it, and nothing spawns.
  const before = fs.existsSync(path.join(root, "runs")) ? fs.readdirSync(path.join(root, "runs")).length : 0;
  postJob(roomDir, { id: "d2", agent: "drill-agent", orders: "D2: landed while the relay was down" });
  await sleep(150);
  const stalled = listJobs(roomDir);
  const runsWhileDown = fs.readdirSync(path.join(root, "runs")).length - before;
  check("D2 while down: job unclaimed", stalled.unclaimed.includes("d2"));
  check("D2 while down: nothing ran", runsWhileDown === 0, "runs added: " + runsWhileDown);

  // Restart: a fresh watchman over the same root, then drain the room.
  const b = watchman();
  const out = await drainOnce(roomDir, {
    owner: "d2",
    handle: async (job) => {
      fs.writeFileSync(path.join(jobsDir, job.id + ".job.json"), JSON.stringify(job));
      await b.pollOnce();
      const r = await waitForResult(job.id);
      if (!r) throw new Error("no result after restart");
      return r;
    },
  });
  const runsAfter = fs.readdirSync(path.join(root, "runs")).length - before;
  check("D2 after restart: job ran", out.length === 1 && out[0].ok === true);
  check("D2 after restart: exactly one run", runsAfter === 1, "runs added: " + runsAfter);

  // Poll again: the job board entry is claimed, so a second poll must not spawn again.
  await b.pollOnce();
  await sleep(200);
  const runsSecond = fs.readdirSync(path.join(root, "runs")).length - before;
  check("D2 second poll: still exactly one run", runsSecond === 1, "runs added: " + runsSecond);
  check("D2 result posted once", fs.existsSync(path.join(roomDir, "d2.result.json")));
}

const failed = results.filter((r) => !r.ok);
console.log("room-1 drill " + path.basename(root));
for (const r of results) console.log("  " + (r.ok ? "ok   " : "FAIL ") + r.name.padEnd(44) + (r.ok ? "" : r.detail || ""));
console.log("  " + results.length + " checks, " + failed.length + " failed");
fs.writeFileSync(path.join(REPO, "os-build", "layer1", "ROOM1_DRILL.json"), JSON.stringify({
  note: "D1 and D2 drill output. The result files under the room are real; the model-free agent is a two-line node process.",
  ts: new Date().toISOString(), root: path.basename(root), results,
}, null, 2) + "\n");
process.exit(failed.length ? 1 : 0);
