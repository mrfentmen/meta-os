// Hands-Free — the host-path drill (R11-246).
//
// This is not a unit test with two fake files. It runs the whole path on this host:
//   intake writes job files -> the real watchman spawns the real hosted commands -> the results
//   land -> brief reads them and measures filedAt..finishedAt.
//
// The registry it uses is a copy of the real hosted entries with their commands resolved to
// absolute paths, because the watchman root here is the Hands-Free workspace, not the repo root.
// Nothing about the commands is simulated; the copy only fixes their working directory.
//
//   node handsfree/drill.mjs
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawnSync } from "node:child_process";
import { createWatchman } from "../agents/watchman.mjs";
import { resolveCommand } from "../agents/runtime.mjs";
import { fileLatency, measureBoard } from "./latency.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.dirname(HERE);
const work = path.join(root, "os-build", "handsfree");
const jobsDir = path.join(work, "jobs");

fs.mkdirSync(work, { recursive: true });
for (const f of fs.readdirSync(work)) {
  if (f === "jobs" || f === "brief.txt" || f === "latency.jsonl" || f === "drill-receipt.json" || f === "intake-receipt.json") {
    const p = path.join(work, f);
    if (fs.statSync(p).isDirectory()) fs.rmSync(p, { recursive: true, force: true });
    else fs.unlinkSync(p);
  }
}

// 1. intake: real command, real inbox.
fs.writeFileSync(path.join(work, "inbox.txt"), "aegis: run the local passes\nnervus: file one stub record\n");
const intake = spawnSync(process.execPath, [path.join(HERE, "hosted.mjs"), "intake"], { cwd: root, encoding: "utf8" });
if (intake.status !== 0) { console.error("drill: intake failed\n" + intake.stdout + intake.stderr); process.exit(1); }

// 2. the relay: real watchman, real registry entries, commands resolved once.
const real = JSON.parse(fs.readFileSync(path.join(root, "agents", "registry.json"), "utf8")).agents;
const entries = real.filter((a) => a.name === "aegis" || a.name === "nervus").map((a) => ({
  ...a, command: resolveCommand(a.command, root), hosted: true,
}));
const registryFile = path.join(work, "drill-registry.json");
fs.writeFileSync(registryFile, JSON.stringify({ agents: entries }, null, 2));

const w = createWatchman({ registryFile, root: work, jobsDir });
const spawned = await w.pollOnce();
await Promise.all(spawned.map((s) => s.handle.done));

// 3. brief: real command, and it measures the board on its way through.
const brief = spawnSync(process.execPath, [path.join(HERE, "hosted.mjs"), "brief"], { cwd: root, encoding: "utf8" });
if (brief.status !== 0) { console.error("drill: brief failed\n" + brief.stdout + brief.stderr); process.exit(1); }

const rows = measureBoard(jobsDir);
const summary = fileLatency(path.join(work, "latency.jsonl"), rows);
const receipt = {
  at: new Date().toISOString(),
  jobs: spawned.length,
  exits: await Promise.all(spawned.map((s) => s.handle.done.then((e) => ({ run: s.handle.runId, ...e })))),
  latency: summary,
  brief: fs.readFileSync(path.join(work, "brief.txt"), "utf8"),
  note: "measured on this host; one run, wall time includes agent start-up",
};
fs.writeFileSync(path.join(work, "drill-receipt.json"), JSON.stringify(receipt, null, 2));
console.log("handsfree drill: " + receipt.jobs + " jobs, " + summary.measured + " measured, median " + summary.medianMs + " ms");
console.log(receipt.brief);
