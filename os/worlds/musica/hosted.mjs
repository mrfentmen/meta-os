// Meta Musica — the hosted entry point for `musica-studio`.
//
// The Python runtime does the work (compose -> keepers -> variation ->
// catalogue -> rights -> board). This file only decides where a session
// writes, runs it, and refuses to report success unless the report the
// runtime promised is actually on disk.
//
//   node os/worlds/musica/hosted.mjs [--takes N] [--brief chipsynth] [--check]
//
// State lives under $METAOS_STATE (default ~/.local/state/metaos), never in
// the checkout: an install runs this from a read-only payload.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { spawnSync } from "node:child_process";
import { Ledger } from "../../../agents/runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..", "..", "..");
const RUNTIME = path.join(HERE, "runtime", "overnight.py");

const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(name);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

const stateRoot = path.resolve(
  process.env.METAOS_STATE || path.join(os.homedir(), ".local", "state", "metaos"),
);
const outRoot = path.join(stateRoot, "musica");
fs.mkdirSync(outRoot, { recursive: true });

const takes = Number(arg("--takes", process.env.MUSICA_TAKES || 8));
if (!Number.isInteger(takes) || takes < 1 || takes > 500) {
  console.error("musica: --takes must be an integer 1..500");
  process.exit(2);
}
const briefId = arg("--brief", "chipsynth");
const briefFile = path.join(HERE, "briefs", briefId + ".md");
if (!fs.existsSync(briefFile)) {
  console.error("musica: no brief at " + briefFile);
  process.exit(2);
}
if (!fs.existsSync(RUNTIME)) {
  console.error("musica: no runtime at " + RUNTIME);
  process.exit(2);
}

// --check proves the pipeline is wired without spending a session: the
// brief parses, the runtime answers --help, the state dir is writable.
if (process.argv.includes("--check")) {
  const help = spawnSync(process.env.PYTHON || "python3", [RUNTIME, "--help"], { encoding: "utf8" });
  if (help.status !== 0) {
    console.error("musica: runtime --help failed: " + (help.stderr || "").slice(0, 200));
    process.exit(1);
  }
  const probe = path.join(outRoot, ".write-probe");
  try {
    fs.writeFileSync(probe, String(Date.now()));
    fs.unlinkSync(probe);
  } catch (error) {
    console.error("musica: state dir is not writable: " + error.message);
    process.exit(1);
  }
  console.log("musica: check ok — brief " + briefId + ", runtime " + path.relative(REPO, RUNTIME));
  process.exit(0);
}

const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const sessionDir = path.join(outRoot, "session-" + stamp);
fs.mkdirSync(sessionDir, { recursive: true });

const ledger = new Ledger(path.join(outRoot, "hosted.jsonl"));
const runId = "musica-" + stamp;
ledger.add(runId, "hosted-start", { brief: briefId, takes, sessionDir });

const run = spawnSync(
  process.env.PYTHON || "python3",
  [RUNTIME, "--session-dir", sessionDir, "--brief-file", briefFile,
   "--brief-id", briefId, "--takes", String(takes),
   "--seed-base", String(10000 + Math.floor(Date.now() / 1000) % 100000)],
  { encoding: "utf8", timeout: 30 * 60 * 1000 },
);

const reportFile = path.join(sessionDir, "overnight-report.json");
let report = null;
try { report = JSON.parse(fs.readFileSync(reportFile, "utf8")); } catch { /* named below */ }

// The exit code alone is not the proof: a runtime that exits 0 and writes no
// report would leave a session nobody can read.
if (run.status !== 0 || !report) {
  ledger.add(runId, "hosted-failed", {
    code: run.status, report: Boolean(report),
    stderr: String(run.stderr || "").slice(-400),
  });
  console.error("musica: session failed (exit " + run.status + ", report " + Boolean(report) + ")");
  if (run.stderr) console.error(String(run.stderr).slice(-800));
  process.exit(1);
}

ledger.add(runId, "hosted-done", {
  sessionDir, takes: report.takes, keepers: report.keepers,
  rejectRate: report.reject_rate, catalogueDelta: report.catalogue_delta,
});
console.log("musica: session " + path.relative(stateRoot, sessionDir)
  + " takes=" + report.takes + " keepers=" + report.keepers
  + " rejects=" + (report.reject_rate ?? "?"));
