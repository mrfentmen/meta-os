// Meta OS agent layer — submit one job to the board.
//
// Until now the only way to put work in front of the watchman was to write a
// .job.json by hand, which meant a typo in an agent name became a job that was
// claimed, refused and forgotten. This validates before the file exists:
//
//   node agents/submit.mjs --root DIR --agent NAME --orders "..." [--id ID]
//
// It refuses an unknown agent, a draft agent (no program), empty orders, an
// unsafe id, and an id that already has a job on the board. The write is a
// rename, so a reader never sees half a job.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

export class SubmitError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "SubmitError";
    this.code = code;
  }
}

export const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export function validateJob({ registry, agent, orders, id }) {
  if (!Array.isArray(registry)) {
    throw new SubmitError("submit-registry", "submit: registry must be an array of agents");
  }
  if (typeof agent !== "string" || agent.trim() === "") {
    throw new SubmitError("submit-agent", "submit: --agent is required");
  }
  const entry = registry.find((candidate) => candidate.name === agent);
  if (!entry) {
    throw new SubmitError("submit-agent", "submit: no such agent: " + agent);
  }
  if (entry.draft === true || !Array.isArray(entry.command) || entry.command.length === 0) {
    throw new SubmitError(
      "submit-draft",
      "submit: " + agent + " has no program yet (draft); nothing would run"
    );
  }
  if (typeof orders !== "string" || orders.trim() === "") {
    throw new SubmitError("submit-orders", "submit: --orders is required");
  }
  if (typeof id !== "string" || !ID_PATTERN.test(id)) {
    throw new SubmitError("submit-id", "submit: bad job id: " + JSON.stringify(id));
  }
  return entry;
}

export function submitJob({ root, registry, agent, orders, id, maxContinues }) {
  const entry = validateJob({ registry, agent, orders, id });
  const jobsDir = path.join(root, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  const target = path.join(jobsDir, id + ".job.json");
  if (fs.existsSync(target)) {
    throw new SubmitError("submit-duplicate", "submit: job already on the board: " + id);
  }
  const job = {
    id,
    agent,
    orders,
    lane: entry.lane || null,
    submittedAt: new Date().toISOString(),
  };
  if (Number.isInteger(maxContinues) && maxContinues >= 0) {
    job.maxContinues = maxContinues;
  }
  const tmp = target + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(job, null, 2) + "\n");
  fs.renameSync(tmp, target);
  return { path: target, job };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));

// A comparison of resolved paths is not enough: /tmp and /var are symlinks on
// macOS, so `node /tmp/x/submit.mjs` and the module's own /private/tmp/x URL
// disagree, the guard falls through, and the process exits 0 having done
// nothing. Compare the real paths instead -- a CLI that silently no-ops is
// worse than one that refuses.
function isMainModule(moduleUrl) {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(process.argv[1]) === fs.realpathSync(url.fileURLToPath(moduleUrl));
  } catch {
    return false;
  }
}

if (isMainModule(import.meta.url)) {
  const arg = (name, fallback = null) => {
    const i = process.argv.indexOf(name);
    return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
  };
  const root = path.resolve(arg("--root", process.cwd()));
  const registryFile = path.resolve(arg("--registry", path.join(HERE, "registry.json")));
  const agent = arg("--agent");
  const orders = arg("--orders");
  const id = arg("--id", "job-" + Date.now().toString(36));
  const continues = arg("--max-continues");

  if (!agent || !orders) {
    console.error("usage: submit.mjs --root DIR --agent NAME --orders TEXT [--id ID] [--max-continues N]");
    process.exit(2);
  }
  try {
    const registry = JSON.parse(fs.readFileSync(registryFile, "utf8")).agents;
    const result = submitJob({
      root, registry, agent, orders, id,
      maxContinues: continues == null ? null : Number(continues),
    });
    console.log(JSON.stringify({ id: result.job.id, agent, path: result.path }, null, 2));
  } catch (error) {
    console.error((error && error.message) || String(error));
    process.exit(1);
  }
}
