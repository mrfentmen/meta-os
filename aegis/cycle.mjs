// Meta Aegis — R12-019, one unattended cycle: sweep -> KEV cross-check -> ledger.
//
// The three stages are the existing programs, run as separate processes so a stage that fails
// cannot be reported as success by the stage after it. The receipt carries each stage's exit,
// duration, and real output count; it does not carry a claim for a stage that did not run.
//
// Route: if AEGIS_OSV_MCP is set, the sweep uses the boss's server. Otherwise the direct OSV
// API is used under Pax's written exception, and the receipt says so.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawn } from "node:child_process";
import { Ledger } from "../agents/runtime.mjs";

// The hosted runtime starts an agent with cwd set to its run directory. Root must come from
// this file's location, or the cycle looks for manifests in runs/<id>/ and reports a failed
// sweep that is really a path bug.
const root = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));
const outDir = path.join(root, "os-build", "aegis");
const receiptFile = path.join(root, "os-build", "layer1", "r12", "AEGIS_CYCLE.json");
const runId = "aegis-cycle-" + new Date().toISOString().replace(/[:.]/g, "-");

function runNode(script, { env = {}, timeout = 150000 } = {}) {
  return new Promise((resolve) => {
    const started = Date.now();
    const child = spawn(process.execPath, [script], {
      cwd: root, env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "", err = "";
    child.stdout.on("data", (d) => { out += d; });
    child.stderr.on("data", (d) => { err += d; });
    const timer = setTimeout(() => child.kill("SIGKILL"), timeout);
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, out, err: err.slice(-2000), ms: Date.now() - started });
    });
  });
}

const stages = {};
const direct = !process.env.AEGIS_OSV_MCP;

const sweep = await runNode("aegis/run-sweep.mjs", { env: direct ? { AEGIS_OSV_DIRECT: "1" } : {} });
const num = (re) => { const m = re.exec(sweep.out); return m ? Number(m[1]) : null; };
stages.sweep = {
  state: sweep.code === 0 ? "ran" : "failed",
  exit: sweep.code,
  ms: sweep.ms,
  route: direct ? "api.osv.dev directly (Pax written exception)" : "AEGIS_OSV_MCP",
  manifests: num(/manifests\s+(\d+)/),
  queried: num(/queried\s+(\d+)/),
  findings: num(/findings\s+(\d+)/),
  stderr: sweep.err.slice(-300),
};

let kev = { code: null, out: "", err: "", ms: 0 };
if (stages.sweep.state === "ran") {
  kev = await runNode("aegis/run-kev.mjs");
  let doc = null;
  try { doc = JSON.parse(fs.readFileSync(path.join(outDir, "KEV.json"), "utf8")); } catch { /* failed stage */ }
  stages.kev = {
    state: kev.code === 0 && doc ? "ran" : "failed",
    exit: kev.code,
    ms: kev.ms,
    checked: doc ? doc.checked : null,
    flagged: doc ? doc.flagged : null,
    unchecked: doc ? doc.unchecked : null,
    excluded: doc ? doc.excludedNonSweep : null,
    stderr: kev.err.slice(-300),
  };
} else {
  stages.kev = { state: "not-run", reason: "sweep did not run" };
}

let ledgerStage = { code: null, out: "", err: "", ms: 0 };
if (stages.kev.state === "ran") {
  ledgerStage = await runNode("aegis/findings-receipts.mjs");
  let batch = null;
  try {
    const lines = fs.readFileSync(path.join(outDir, "findings-ledger.jsonl"), "utf8").trim().split("\n");
    for (const line of lines.reverse()) {
      const rec = JSON.parse(line);
      if (rec.kind === "batch" && rec.run && rec.run.startsWith("findings-")) { batch = rec; break; }
    }
  } catch { /* failed stage */ }
  stages.ledger = {
    state: ledgerStage.code === 0 && batch ? "ran" : "failed",
    exit: ledgerStage.code,
    ms: ledgerStage.ms,
    receiptsWritten: batch ? batch.receiptsWritten : null,
    sweepFindings: batch ? batch.sweepFindings : null,
    ledgerLines: (() => {
      try { return fs.readFileSync(path.join(outDir, "findings-ledger.jsonl"), "utf8").split("\n").filter(Boolean).length; }
      catch { return null; }
    })(),
    stderr: ledgerStage.err.slice(-300),
  };
} else {
  stages.ledger = { state: "not-run", reason: "KEV did not run" };
}

const ok = Object.values(stages).every((s) => s.state === "ran");
const receipt = {
  task: "R12-019",
  run: runId,
  at: new Date().toISOString(),
  ok,
  route: direct ? "direct OSV API under Pax's written exception" : "AEGIS_OSV_MCP",
  stages,
  claims: {
    proven: ok
      ? "the sweep queried the manifests, the KEV cross-check read its findings, and the ledger recorded a batch receipt"
      : "nothing beyond the stages that state ran",
    not_proven: "no model, no report beyond the stage counts; the registry entry is claimed only when the run ledger shows the spawn",
  },
};
fs.mkdirSync(path.dirname(receiptFile), { recursive: true });
fs.writeFileSync(receiptFile, JSON.stringify(receipt, null, 2) + "\n");

new Ledger(path.join(outDir, "runs.jsonl")).add(runId, "aegis-cycle", {
  ok, sweep: stages.sweep, kev: stages.kev, ledger: stages.ledger,
});
console.log("aegis cycle " + runId + (ok ? " PASS" : " FAIL"));
for (const [name, s] of Object.entries(stages)) {
  console.log("  " + name.padEnd(7) + " " + s.state + (s.findings != null ? " findings=" + s.findings : "") +
    (s.checked != null ? " checked=" + s.checked : "") + (s.receiptsWritten != null ? " receipts=" + s.receiptsWritten : ""));
}
process.exit(ok ? 0 : 1);
