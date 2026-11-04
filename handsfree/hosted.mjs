// Hands-Free — the hosted entry points (R11-244).
//
// Three registry entries, one command with a role argument, because the three passes share one
// workspace: os-build/handsfree/. Each role exercises the real module (not a copy of it), writes
// its output under that workspace, and exits non-zero if the pass refused something it should
// have accepted.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { dropOrders } from "./intake.mjs";
import { briefFromJobs } from "./brief.mjs";
import { requestApproval, dropApproval, readApproval } from "./approval.mjs";
import { fileLatency, measureBoard } from "./latency.mjs";
import { stateRoot } from "../agents/state-root.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.dirname(HERE);
const shipped = path.join(root, "os-build", "handsfree");
// The image's payload is read-only, so the working board lives in the user's
// state dir there; a checkout keeps writing beside the code.
const work = path.join(stateRoot(root, "handsfree"), "os-build", "handsfree");
const [, , role = "brief"] = process.argv;

if (role === "intake") {
  const inbox = path.join(work, "inbox.txt");
  const jobsDir = path.join(work, "jobs");
  fs.mkdirSync(work, { recursive: true });
  // The shipped inbox is the lane's standing orders. On a read-only payload it
  // cannot be written in place, so the first run copies it into the board.
  if (!fs.existsSync(inbox) && fs.existsSync(path.join(shipped, "inbox.txt"))) {
    fs.copyFileSync(path.join(shipped, "inbox.txt"), inbox);
  }
  if (!fs.existsSync(inbox)) {
    // The shipped inbox is the lane's standing orders, not invented work: two orders the crew
    // can actually pick up.
    fs.writeFileSync(inbox, "aegis: run the local passes\nnervus: file one stub record\n");
  }
  const r = dropOrders(inbox, jobsDir);
  fs.writeFileSync(path.join(work, "intake-receipt.json"), JSON.stringify({
    at: new Date().toISOString(), filed: r.jobs, refused: r.skipped,
  }, null, 2));
  console.log("handsfree intake: filed " + r.jobs.length + ", refused " + r.skipped.length);
  process.exit(r.skipped.length ? 1 : 0);
} else if (role === "brief") {
  const jobsDir = path.join(work, "jobs");
  const text = briefFromJobs(jobsDir);
  fs.mkdirSync(work, { recursive: true });
  fs.writeFileSync(path.join(work, "brief.txt"), text);
  const rows = measureBoard(jobsDir);
  if (rows.length) fileLatency(path.join(work, "latency.jsonl"), rows);
  process.stdout.write(text);
} else if (role === "approval") {
  const runDir = path.join(work, "approval-drill");
  fs.mkdirSync(runDir, { recursive: true });
  // The drill is re-runnable: it clears its OWN state, never a real run's. Without this the
  // second hosted invocation saw an answered request and exited 1, which would have read as the
  // loop being broken.
  for (const f of ["ledger.jsonl", "approval.request.json", "approval.json", "approval-duplicates.jsonl"]) {
    try { fs.unlinkSync(path.join(runDir, f)); } catch { /* first run */ }
  }
  fs.writeFileSync(path.join(runDir, "ledger.jsonl"), "");
  requestApproval(runDir, { run: "handsfree-approval", what: "drill: answer once" });
  const first = dropApproval(runDir, "yes", { by: "hosted-drill" });
  const second = dropApproval(runDir, "yes", { by: "hosted-drill" });
  const state = readApproval(runDir).state;
  console.log("handsfree approval: first=" + (first.ok ? first.decision : first.reason) +
    " second=" + (second.ok ? "counted" : second.reason) + " state=" + state);
  process.exit(first.ok && !second.ok && second.duplicate === true && state === "allowed" ? 0 : 1);
} else {
  console.error("usage: hosted.mjs intake|brief|approval");
  process.exit(2);
}
