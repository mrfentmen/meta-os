// Hands-Free C2 — results and ledgers become ONE speakable brief.
//
// Rules the text follows: numbers first, short sentences, no jargon, and a plain word for what
// happened. "exit code 3" is a fact for a machine; "failed (code 3)" is the same fact said once.
// The brief never says "success" for a run that was stopped: stopped is its own outcome.
import fs from "node:fs";
import path from "node:path";

export function composeBrief(results) {
  const list = [...results].sort((a, b) => String(a.id).localeCompare(String(b.id)));
  if (list.length === 0) return "No orders ran.\n";

  const stoppedOf = (r) => r.code !== 0 && (r.stopped || r.signal);
  const finished = list.filter((r) => r.code === 0 && !r.stopped).length;
  const stopped = list.filter(stoppedOf).length;
  const failed = list.length - finished - stopped;

  const lines = [];
  lines.push(list.length + (list.length === 1 ? " order ran." : " orders ran."));
  lines.push(finished + " finished, " + stopped + " stopped, " + failed + " failed.");
  for (const r of list) {
    if (r.code === 0 && !r.stopped) lines.push(r.agent + " finished.");
    else if (stoppedOf(r)) lines.push(r.agent + " was stopped.");
    else lines.push(r.agent + " failed (code " + r.code + ").");
  }
  return lines.join("\n") + "\n";
}

export function readResults(jobsDir) {
  if (!fs.existsSync(jobsDir)) return [];
  const out = [];
  for (const f of fs.readdirSync(jobsDir).filter((x) => x.endsWith(".result.json")).sort()) {
    try { out.push(JSON.parse(fs.readFileSync(path.join(jobsDir, f), "utf8"))); } catch { /* torn result: not a fact yet */ }
  }
  return out;
}

export function briefFromJobs(jobsDir) {
  return composeBrief(readResults(jobsDir));
}

/* ---- CLI: node handsfree/brief.mjs <jobsDir> ---- */
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const [, , jobsDir] = process.argv;
  if (!jobsDir) { console.error("usage: brief.mjs <jobsDir>"); process.exit(2); }
  process.stdout.write(briefFromJobs(jobsDir));
}
