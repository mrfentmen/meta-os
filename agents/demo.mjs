// Meta OS agent layer — receipt demo (R2-T3 patrol lane, tasks 76-78).
//
// Submits 3 jobs, waits for their receipts, prints every artifact path and a
// verify verdict. Safe to run twice: job ids are fixed, so a repeat run
// reuses the board instead of filing duplicates (submit-duplicate is caught,
// finished jobs are skipped by the watchman, receipts are re-verified).
//
// State lives OUTSIDE the git tree: $R2T3_DATA_DIR or
// ~/.local/state/oc2-agent-r2t3-d/demo.
//
//   node agents/demo.mjs [--data-dir DIR] [--prefix demo-r2t3] [--json]
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { createWatchman } from "./watchman.mjs";
import { board } from "./jobs.mjs";
import { submitJob, SubmitError } from "./submit.mjs";
import { loadRegistry } from "./runtime.mjs";
import { defaultDataDir } from "./heartbeat.mjs";

export const DEMO_AGENT = "demo-echo";
export const DEMO_JOBS = 3;

export function demoRegistry(root) {
  return { agents: [{ name: DEMO_AGENT, lane: "R2-T3 receipt demo", command: [process.execPath, "-e", "process.exit(0)"], budget: {} }] };
}

export async function runDemo({ dataDir = defaultDataDir() + "/demo", prefix = "demo-r2t3", jobCount = DEMO_JOBS } = {}) {
  const root = path.resolve(dataDir);
  const jobsDir = path.join(root, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  const registryFile = path.join(root, "demo-registry.json");
  fs.writeFileSync(registryFile, JSON.stringify(demoRegistry(root), null, 2));
  const registry = loadRegistry(registryFile);

  const ids = Array.from({ length: jobCount }, (_, i) => `${prefix}-${i + 1}`);
  const submitted = [];
  let reused = 0;
  for (const id of ids) {
    try {
      const out = submitJob({ root, registry, agent: DEMO_AGENT, orders: "demo receipt probe " + id, id });
      submitted.push({ id, path: out.path, fresh: true });
    } catch (err) {
      if (err instanceof SubmitError && err.code === "submit-duplicate") {
        reused += 1;
        submitted.push({ id, path: path.join(jobsDir, id + ".job.json"), fresh: false });
      } else throw err;
    }
  }

  const w = createWatchman({ registryFile, root, jobsDir, repoRoot: root });
  const spawned = await w.pollOnce();
  await Promise.allSettled(spawned.map((s) => s.handle.done));
  await new Promise((r) => setTimeout(r, 50));

  const artifacts = [];
  let allDone = true;
  for (const s of submitted) {
    const resultFile = path.join(jobsDir, s.id + ".result.json");
    let result = null;
    try {
      result = JSON.parse(fs.readFileSync(resultFile, "utf8"));
    } catch { /* missing/unreadable receipt */ }
    const done = Boolean(result) && result.code === 0 && (result.signal === null || result.signal === undefined);
    if (!done) allDone = false;
    artifacts.push({
      id: s.id, fresh: s.fresh,
      job: path.join(jobsDir, s.id + ".job.json"),
      result: resultFile,
      runLedger: result && result.ledger ? result.ledger : null,
      code: result ? result.code : null,
      done,
    });
  }
  const view = board({ root });
  const verify = allDone && artifacts.length === jobCount
    ? "OK: 3 jobs, 3 code-0 receipts"
    : `FAIL: ${artifacts.filter((a) => a.done).length}/${artifacts.length} receipts done`;
  return { root, reused, artifacts, counts: view.counts, verify, ok: allDone && artifacts.length === jobCount };
}

function isMainModule(moduleUrl) {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(process.argv[1]) === fs.realpathSync(url.fileURLToPath(moduleUrl));
  } catch {
    return false;
  }
}

if (isMainModule(import.meta.url)) {
  if (process.argv.includes("--help") || process.argv.includes("-h")) {
    console.log("usage: node agents/demo.mjs [--data-dir DIR] [--prefix P] [--json]");
    console.log("  submits 3 stub jobs, waits for receipts, prints artifacts + verify.");
    console.log("  safe to re-run: fixed ids are reused, receipts re-verified.");
    process.exit(0);
  }
  const arg = (name, fallback = null) => {
    const i = process.argv.indexOf(name);
    return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
  };
  const out = await runDemo({
    dataDir: arg("--data-dir", defaultDataDir() + "/demo"),
    prefix: arg("--prefix", "demo-r2t3"),
  });
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify(out, null, 2));
  } else {
    for (const a of out.artifacts) {
      console.log(`${a.done ? "receipt" : "MISSING"} ${a.id} code=${a.code} fresh=${a.fresh}`);
      console.log(`  job    ${a.job}`);
      console.log(`  result ${a.result}`);
      console.log(`  ledger ${a.runLedger || "(none)"}`);
    }
    console.log(`board: ${JSON.stringify(out.counts)} (reused ${out.reused})`);
    console.log("verify: " + out.verify);
  }
  process.exit(out.ok ? 0 : 1);
}
