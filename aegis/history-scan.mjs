// Meta Aegis — R12-015, git-history secret scan.
//
// Counts only. This program never prints or stores a matched value, a matched line, or a file
// path from inside a match: the output is category + year + count, plus the exact commit range
// that was covered. Matching is line-based over `git log -p`, so a secret split across lines is
// outside what this scan can see, and the report says that.
//
//   node aegis/history-scan.mjs [rev]
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { Ledger } from "../agents/runtime.mjs";

const root = process.cwd();
const rev = process.argv[2] || "HEAD";
const outDir = path.join(root, "os-build", "aegis");

const CATEGORIES = [
  ["private-key", /-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----/],
  ["aws-access-key", /\bAKIA[0-9A-Z]{16}\b/],
  ["github-token", /\bgh[pousr]_[A-Za-z0-9]{36,}\b/],
  ["slack-token", /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/],
  ["openai-style-key", /\bsk-[A-Za-z0-9_-]{20,}\b/],
  ["stripe-key", /\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b/],
  ["jwt", /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/],
  ["url-credentials", /https?:\/\/[^/\s:@]+:[^/\s@]+@/],
  // Deliberately broad: a line-level assignment of a long quoted value to a secret-shaped key.
  // False positives are expected here and are reported as counts, not as findings.
  ["secret-assignment", /(?:api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["'][^"'\s]{12,}["']/i],
];

const counts = {};
for (const [name] of CATEGORIES) counts[name] = {};
let commits = 0, first = null, last = null, lines = 0, currentYear = null;

function bump(cat, year, seenLines) {
  const y = year || "unknown";
  counts[cat][y] = (counts[cat][y] || 0) + 1;
  seenLines.add(cat + ":" + y);
}

const child = spawn("git", ["log", rev, "-p", "--no-color", "--pretty=format:@@COMMIT %H %ad", "--date=short"], {
  cwd: root, stdio: ["ignore", "pipe", "pipe"],
});
let buf = "";
let stderr = "";
child.stderr.on("data", (d) => { stderr = (stderr + d.toString()).slice(-2000); });
child.stdout.on("data", (chunk) => {
  buf += chunk.toString("utf8");
  const parts = buf.split("\n");
  buf = parts.pop();
  for (const line of parts) {
    lines += 1;
    if (line.startsWith("@@COMMIT ")) {
      const [, hash, date] = line.split(" ");
      commits += 1;
      currentYear = (date || "").slice(0, 4) || null;
      if (!first) first = { hash, date };
      last = { hash, date };
      continue;
    }
    if (!line || line[0] === " ") continue;   // context line: not added or removed by a commit
    const seen = new Set();
    for (const [cat, re] of CATEGORIES) {
      if (re.test(line)) bump(cat, currentYear, seen);
    }
  }
});
const code = await new Promise((resolve) => child.on("close", resolve));
if (code !== 0) {
  console.error("history-scan: git log exited " + code + ": " + stderr.slice(-300));
  process.exit(3);
}

const total = Object.values(counts).reduce((a, perYear) => a + Object.values(perYear).reduce((x, y) => x + y, 0), 0);
const years = [...new Set(Object.values(counts).flatMap((perYear) => Object.keys(perYear)))].sort();
const runId = "history-" + new Date().toISOString().replace(/[:.]/g, "-");
const result = {
  run: runId,
  at: new Date().toISOString(),
  rev,
  commits,
  range: { first, last },
  linesScanned: lines,
  categories: counts,
  totalCategoryHits: total,
  limits: "line-based diff scan; a secret split across lines is not seen; counts include documentation and test fixtures",
};
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "HISTORY_SCAN.json"), JSON.stringify(result, null, 2) + "\n");

const md = [];
md.push("# Aegis git-history secret scan — counts only");
md.push("");
md.push("Run `" + runId + "`, " + result.at + ". Range: `" + rev + "`, **" + commits + " commits**, " +
  (first ? first.hash.slice(0, 8) + " (" + first.date + ")" : "?") + " to " +
  (last ? last.hash.slice(0, 8) + " (" + last.date + ")" : "?") + ".");
md.push("");
md.push("**No value, matched line, or matched path is written here.** The scan counts category hits");
md.push("per commit year. A hit in a test fixture, a regex, or a doc example is counted too — this is a");
md.push("count of pattern-shaped lines, not a confirmed-secret count.");
md.push("");
md.push("| category | " + (years.length ? years.join(" | ") : "no hits") + " | total |");
md.push("|---|" + years.map(() => "---").join("|") + "|---|");
for (const [name] of CATEGORIES) {
  const perYear = counts[name];
  const t = Object.values(perYear).reduce((a, b) => a + b, 0);
  md.push("| " + name + " | " + (years.length ? years.map((y) => (perYear[y] || 0)).join(" | ") : "0") + " | " + t + " |");
}
md.push("");
md.push("Total category hits: **" + total + "** across **" + lines + "** diff lines.");
md.push("");
md.push("## Limits, stated");
md.push("");
md.push("- Line-based: a secret split across lines is not detected.");
md.push("- No pattern here distinguishes a live credential from an example. Any nonzero count needs a");
md.push("  human review of the location before it is called a leak; this record deliberately cannot");
md.push("  name the location without also naming the value's neighbourhood.");
md.push("- The scan covers `git log " + rev + "` only. Other refs, stashes, and reflogs are not included.");
fs.writeFileSync(path.join(outDir, "HISTORY_SCAN.md"), md.join("\n") + "\n");

new Ledger(path.join(outDir, "runs.jsonl")).add(runId, "history-scan", {
  commits, from: first && first.hash, to: last && last.hash, categoryHits: total,
});
console.log("history scan " + runId);
console.log("  commits " + commits + " (" + (first && first.date) + " .. " + (last && last.date) + ")");
console.log("  hits    " + total);
for (const [name] of CATEGORIES) {
  const t = Object.values(counts[name]).reduce((a, b) => a + b, 0);
  if (t) console.log("  " + name.padEnd(20) + t);
}
