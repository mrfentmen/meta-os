// Meta Aegis — R12-017, watch-target liveness.
//
// The public check that exists for each target: HTTP status for a page, `git ls-remote` for a
// repo (public metadata over the git protocol, no API quota). UNVERIFIED is replaced by LIVE,
// DEAD or UNREACHABLE with a date. UNREACHABLE is not DEAD: a timeout is not evidence the thing
// is gone, and collapsing the two is how a watch list starts lying.
//
//   node aegis/check-liveness.mjs [targets.json]
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { Ledger } from "../agents/runtime.mjs";

const pexec = promisify(execFile);
const root = process.cwd();
const file = process.argv[2] || path.join(root, "aegis", "watch-targets.json");
const doc = JSON.parse(fs.readFileSync(file, "utf8"));
const CONCURRENCY = 12;
const date = new Date().toISOString();

async function checkPage(t) {
  const url = t.url || "https://" + t.ref;
  try {
    const res = await fetch(url, {
      redirect: "follow", signal: AbortSignal.timeout(12000),
      headers: { "user-agent": "meta-aegis-liveness/1" },
    });
    return { liveness: res.ok ? "LIVE" : "DEAD", detail: "HTTP " + res.status, method: "HTTP status", checkedAt: date };
  } catch (err) {
    return { liveness: "UNREACHABLE", detail: String(err && err.message || err).slice(0, 120), method: "HTTP status", checkedAt: date };
  }
}

async function checkRepo(t) {
  const ref = t.ref;
  try {
    const { stdout } = await pexec("git", ["ls-remote", "--heads", "https://github.com/" + ref + ".git"], {
      timeout: 20000, maxBuffer: 4 * 1024 * 1024,
      env: { ...process.env, GIT_TERMINAL_PROMPT: "0" },
    });
    return { liveness: "LIVE", detail: stdout.trim() ? "heads listed" : "empty repository", method: "git ls-remote --heads", checkedAt: date };
  } catch (err) {
    const text = String((err && (err.stderr || err.message)) || err);
    const dead = /not found|does not appear to be a git repository|could not read from remote repository/i.test(text);
    return {
      liveness: dead ? "DEAD" : "UNREACHABLE",
      detail: dead ? "remote refused: not found" : text.replace(/\s+/g, " ").slice(0, 120),
      method: "git ls-remote --heads", checkedAt: date,
    };
  }
}

const results = [];
let next = 0;
async function worker() {
  while (next < doc.targets.length) {
    const i = next++;
    const t = doc.targets[i];
    const found = t.type === "page" ? await checkPage(t)
      : t.type === "repo" ? await checkRepo(t)
      : { liveness: "UNREACHABLE", detail: "unknown target type " + t.type, method: "none", checkedAt: date };
    results[i] = { id: t.id, type: t.type, ref: t.ref, ...found };
  }
}
await Promise.all(Array.from({ length: CONCURRENCY }, () => worker()));

for (const r of results) {
  const t = doc.targets.find((x) => x.id === r.id);
  t.previousLiveness = t.liveness;
  t.liveness = r.liveness;
  t.livenessDetail = r.detail;
  t.livenessMethod = r.method;
  t.livenessCheckedAt = r.checkedAt;
}
doc.note = "Liveness checked " + date + " by aegis/check-liveness.mjs. Ownership remains the reviewer's question.";
fs.writeFileSync(file, JSON.stringify(doc, null, 2) + "\n");
fs.writeFileSync(path.join(root, "os-build", "aegis", "LIVENESS.json"),
  JSON.stringify({ at: date, file: path.relative(root, file), results }, null, 2) + "\n");

const count = (s) => results.filter((r) => r.liveness === s).length;
const byType = (type, s) => results.filter((r) => r.type === type && r.liveness === s).length;
const lines = [];
lines.push("# Aegis watch-target liveness — " + date.slice(0, 10));
lines.push("");
lines.push("Checked with the public check that exists per target: HTTP status for pages, `git ls-remote");
lines.push("--heads` for repos. UNREACHABLE is a failed check, not a dead target. Ownership is still");
lines.push("the reviewer's question and is not answered here.");
lines.push("");
lines.push("| item | count |");
lines.push("|---|---|");
lines.push("| targets | " + results.length + " |");
lines.push("| LIVE | " + count("LIVE") + " |");
lines.push("| DEAD | " + count("DEAD") + " |");
lines.push("| UNREACHABLE | " + count("UNREACHABLE") + " |");
lines.push("| pages LIVE | " + byType("page", "LIVE") + " / " + results.filter((r) => r.type === "page").length + " |");
lines.push("| repos LIVE | " + byType("repo", "LIVE") + " / " + results.filter((r) => r.type === "repo").length + " |");
lines.push("");
lines.push("| target | type | result | detail | checked |");
lines.push("|---|---|---|---|---|");
for (const r of results) {
  lines.push("| `" + r.id + "` | " + r.type + " | **" + r.liveness + "** | " + String(r.detail).replace(/\|/g, "\\|") + " | " + date.slice(0, 10) + " |");
}
lines.push("");
lines.push("Dead targets are not deleted by this check; removal is a review decision with a note.");
fs.writeFileSync(path.join(root, "os-build", "aegis", "LIVENESS.md"), lines.join("\n") + "\n");

new Ledger(path.join(root, "os-build", "aegis", "runs.jsonl")).add("liveness-" + date.replace(/[:.]/g, "-"), "liveness", {
  targets: results.length, live: count("LIVE"), dead: count("DEAD"), unreachable: count("UNREACHABLE"),
});
console.log("liveness: " + results.length + " targets; LIVE " + count("LIVE") + ", DEAD " + count("DEAD") + ", UNREACHABLE " + count("UNREACHABLE"));
