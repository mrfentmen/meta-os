// Meta Aegis — secret hygiene (AEGIS_SPEC.md, "Secret hygiene": pattern counts, never values).
//
// The rule is the whole design: **a match is recorded as where and what kind, never as what.**
// Nothing in this module returns the matched text. `locations` carries a path, a line number
// and a category; a caller that wants the value has to go to the file, which is the point --
// the report lands in a public repo (`main`), so a scanner that echoed its finding would be
// the leak it was hired to find.
//
// Not in this file: no network, no git history (that is the OPSEC pass), no "fix".
import fs from "node:fs";
import path from "node:path";
import { SKIP_DIRS, DEFAULT_MAX_DEPTH } from "./manifests.mjs";

// Ordered by how little doubt there is. `assigned-secret` is the only one that can be a false
// positive, which is why it is counted separately and labelled for review rather than mixed
// into the confirmed counts.
export const PATTERNS = [
  { id: "private-key-block", re: /-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----/, confidence: "confirmed" },
  { id: "aws-access-key-id", re: /\bAKIA[0-9A-Z]{16}\b/, confidence: "confirmed" },
  { id: "github-token", re: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/, confidence: "confirmed" },
  { id: "slack-token", re: /\bxox[baprs]-[A-Za-z0-9-]{12,}\b/, confidence: "confirmed" },
  { id: "stripe-live-key", re: /\bsk_live_[A-Za-z0-9]{16,}\b/, confidence: "confirmed" },
  { id: "jwt", re: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/, confidence: "confirmed" },
  { id: "assigned-secret", re: /\b(?:api[_-]?key|secret|passwd|password|access[_-]?token|auth[_-]?token)\s*[:=]\s*["'][^"'\s]{16,}["']/i, confidence: "review" },
];

export const TEXT_EXT = new Set([
  ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".jsonl", ".md", ".txt", ".yml", ".yaml",
  ".toml", ".rs", ".go", ".py", ".sh", ".bash", ".zsh", ".css", ".html", ".htm", ".svg", ".sql",
  ".goose", ".lobster", ".env", ".ini", ".cfg", ".conf", ".xml", ".lock", ".c", ".h",
]);

// An extensionless file is worth reading if its name says what it is; everything else is
// counted as skipped, so "no findings" cannot quietly mean "no files opened".
const NAME_ALLOW = new Set(["Makefile", "Dockerfile", ".gitignore", ".env", "Cargo.lock", "LICENSE", "README", "Procfile"]);

export function isTextCandidate(file) {
  const base = path.basename(file);
  const ext = path.extname(base).toLowerCase();
  if (TEXT_EXT.has(ext)) return true;
  if (base.startsWith(".env")) return true;
  return NAME_ALLOW.has(base);
}

export function looksBinary(buf) {
  const n = Math.min(buf.length, 8192);
  for (let i = 0; i < n; i++) if (buf[i] === 0) return true;
  return false;
}

// scanText takes a string so the test can hand it a fixture. `allow` is the line-based
// allowlist hook: a line that names a fixture or an example is skipped, but the skip is
// counted (see `allowlisted`) so a reader can tell how much was waved through.
export function scanText(text, { path: relPath = "(text)", allow = () => false } = {}) {
  const hits = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (const p of PATTERNS) {
      if (!p.re.test(line)) continue;
      if (allow(line, p.id)) { hits.push({ id: p.id, confidence: p.confidence, path: relPath, line: i + 1, allowlisted: true }); continue; }
      hits.push({ id: p.id, confidence: p.confidence, path: relPath, line: i + 1 });
    }
  }
  return hits;
}

export function scanTree(root, { maxDepth = DEFAULT_MAX_DEPTH, skipDirs = SKIP_DIRS, maxBytes = 2 * 1024 * 1024, allow = () => false } = {}) {
  const base = path.resolve(root);
  const locations = [];
  const skipped = { binary: 0, large: 0, notText: 0, symlink: 0, dirs: 0 };
  let scanned = 0;

  const walk = (abs, depth) => {
    if (depth > maxDepth) return;
    for (const e of fs.readdirSync(abs, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
      const child = path.join(abs, e.name);
      if (e.isSymbolicLink()) { skipped.symlink += 1; continue; }
      if (e.isDirectory()) {
        if (skipDirs.has(e.name)) { skipped.dirs += 1; continue; }
        walk(child, depth + 1);
        continue;
      }
      if (!e.isFile()) continue;
      if (!isTextCandidate(child)) { skipped.notText += 1; continue; }
      const st = fs.statSync(child);
      if (st.size > maxBytes) { skipped.large += 1; continue; }
      const buf = fs.readFileSync(child);
      if (looksBinary(buf)) { skipped.binary += 1; continue; }
      scanned += 1;
      const rel = path.relative(base, child).split(path.sep).join("/");
      locations.push(...scanText(buf.toString("utf8"), { path: rel, allow }));
    }
  };
  walk(base, 0);

  const counts = {};
  for (const p of PATTERNS) counts[p.id] = 0;
  const byConfidence = { confirmed: 0, review: 0 };
  const allowlisted = [];
  for (const l of locations) {
    counts[l.id] = (counts[l.id] || 0) + 1;
    if (l.allowlisted) { allowlisted.push(l); continue; }
    byConfidence[l.confidence] += 1;
  }
  return { root: base, scanned, skipped, counts, byConfidence, locations: locations.filter((l) => !l.allowlisted), allowlisted };
}

export function renderReport(result, { runId = null } = {}) {
  const total = result.byConfidence.confirmed + result.byConfidence.review;
  const lines = [];
  lines.push("# Aegis secret hygiene — counts only");
  lines.push("");
  lines.push((runId ? "Run `" + runId + "`. " : "") + "Generated by `aegis/secrets.mjs`. **No value is recorded anywhere in this file or its JSON**, by design: this lands on `main`.");
  lines.push("");
  lines.push("## Counts");
  lines.push("");
  lines.push("| pattern | confirmed / review | count |");
  lines.push("|---|---|---|");
  for (const p of PATTERNS) lines.push("| `" + p.id + "` | " + p.confidence + " | " + (result.counts[p.id] || 0) + " |");
  lines.push("| **total** | | **" + total + "** |");
  lines.push("");
  lines.push("Files read: " + result.scanned + ". Skipped: " + result.skipped.notText + " not-text, " +
    result.skipped.binary + " binary, " + result.skipped.large + " oversized, " +
    result.skipped.symlink + " symlink, " + result.skipped.dirs + " cache/VCS dirs.");
  lines.push("");
  if (result.allowlisted.length) {
    lines.push(result.allowlisted.length + " match(es) sit on lines that name a fixture or an example; they are counted here and excluded from the locations below.");
    lines.push("");
  }
  lines.push("## Locations");
  lines.push("");
  if (!result.locations.length) {
    lines.push("None. Zero is the result, not an empty section: " + result.scanned + " files were read.");
  } else {
    lines.push("| file | line | pattern | confidence |");
    lines.push("|---|---|---|---|");
    for (const l of result.locations.slice(0, 200)) {
      lines.push("| `" + l.path + "` | " + l.line + " | `" + l.id + "` | " + l.confidence + " |");
    }
    if (result.locations.length > 200) lines.push("");
    if (result.locations.length > 200) lines.push("(" + (result.locations.length - 200) + " more not listed; the JSON has all of them.)");
  }
  lines.push("");
  lines.push("## What this cannot tell you");
  lines.push("");
  lines.push("- A pattern is not a live credential. `assigned-secret` matches can be placeholders, and every");
  lines.push("  one of them needs a human look at the line. `confirmed` means the shape is unambiguous, not");
  lines.push("  that the secret is real or still valid.");
  lines.push("- It does not look at git history. A secret removed from the working tree is still in the");
  lines.push("  history, and that check is a separate pass (OPSEC).");
  lines.push("- It does not validate anything against a provider, because that would mean sending the value");
  lines.push("  somewhere, which is the one thing this module will not do.");
  lines.push("");
  return lines.join("\n");
}
