// Meta Aegis — OPSEC v1 (AEGIS_SPEC.md, wing 7: "how the operation leaks, checked as practice").
//
// This is not a scan of a system; it is a review of text that is about to be published. One
// question, asked per line: does this tell a stranger something we did not decide to tell?
//
// Five things answer yes, and every one of them is a fact about the *author's* machine or
// identity rather than about the product:
//
//   home-path    /Users/<name>/, /home/<name>/  -- the account name and the directory layout
//   private-ip   10/8, 172.16/12, 192.168/16    -- the shape of a private network
//   email        any address                    -- a contact that was not meant to be the contact
//   internal-host *.internal, *.local, *.lan    -- a name that only resolves inside
//   machine-name a hostname literal             -- which box did the work
//
// Like the secret scanner, this reports where and what kind, never the matched text: the
// report is committed to a public repository.
export const CHECKS = [
  { id: "home-path", re: /(?:\/Users\/|\/home\/|C:\\Users\\)([A-Za-z0-9._-]+)/, severity: "low",
    why: "a home path names the account and the machine's layout" },
  { id: "private-ip", re: /\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b/, severity: "low",
    why: "a private address describes a network a reader cannot see" },
  { id: "email", re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/, severity: "low",
    why: "an address published in passing becomes the address people write to" },
  { id: "internal-host", re: /\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:internal|local|lan|corp)\b/i, severity: "low",
    why: "an internal name is a hint about infrastructure that is not public" },
  { id: "machine-name", re: /\b(?:MacBook|iMac|Mac-mini|Mac-Pro)[-A-Za-z0-9._]*\b/, severity: "info",
    why: "the machine that built the artifact is not part of the artifact" },
];

// A line that is deliberately about the reader's own machine is not a leak. These markers let
// a file opt a line out, and the opt-out is COUNTED so a reader can see how much was excused.
export const ALLOW_MARKERS = ["<your-", "<path>", "example.com", "you@", "/Users/you/", "/home/you/"];

export function scanText(text, { path: relPath = "(text)", allow = null } = {}) {
  const hits = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (ALLOW_MARKERS.some((m) => line.includes(m))) continue;
    if (allow && allow(line)) continue;
    for (const c of CHECKS) {
      if (c.re.test(line)) hits.push({ id: c.id, severity: c.severity, path: relPath, line: i + 1 });
    }
  }
  return hits;
}

import fs from "node:fs";

export function scanFiles(files, { root = process.cwd(), allow = null } = {}) {
  const hits = [];
  const read = [];
  const missing = [];
  for (const f of files) {
    const abs = f.startsWith("/") ? f : `${root}/${f}`;
    if (!fs.existsSync(abs)) { missing.push(f); continue; }
    read.push(f);
    hits.push(...scanText(fs.readFileSync(abs, "utf8"), { path: f, allow }));
  }
  const counts = {};
  for (const c of CHECKS) counts[c.id] = 0;
  for (const h of hits) counts[h.id] += 1;
  return { files: read, missing, hits, counts };
}

// One finding per check that fired, not one per hit: a README with nine home paths is one
// practice problem with nine locations, and nine records would make the list unreadable.
export function findingsFrom(scan, { runId }) {
  const out = [];
  for (const c of CHECKS) {
    const mine = scan.hits.filter((h) => h.id === c.id);
    if (!mine.length) continue;
    const where = [...new Set(mine.map((h) => h.path + ":" + h.line))];
    out.push({
      severity: c.severity,
      title: c.id + " appears in " + where.length + " place(s) in the submission materials",
      evidence: c.why + ". Locations: " + where.slice(0, 12).join(", ") + (where.length > 12 ? " (+" + (where.length - 12) + " more)" : ""),
      source: "aegis/opsec.mjs pre-publish review",
      run: runId,
      target: "submission-materials",
    });
  }
  return out;
}

export function renderReport(scan, findings, { runId, materials }) {
  const lines = [];
  lines.push("# Aegis OPSEC v1 — pre-publish review");
  lines.push("");
  lines.push("Run `" + runId + "`. Materials: " + materials.map((m) => "`" + m + "`").join(", ") + ".");
  if (scan.missing.length) lines.push("");
  if (scan.missing.length) lines.push("Not found (not reviewed): " + scan.missing.map((m) => "`" + m + "`").join(", ") + ".");
  lines.push("");
  lines.push("The question is the one in the spec: **does this tell a stranger something we did not decide to tell?** Locations and kinds are recorded; the matched text never is.");
  lines.push("");
  lines.push("## Counts");
  lines.push("");
  lines.push("| check | what it means | count |");
  lines.push("|---|---|---|");
  for (const c of CHECKS) lines.push("| `" + c.id + "` | " + c.why + " | " + scan.counts[c.id] + " |");
  lines.push("");
  lines.push("## Locations");
  lines.push("");
  if (!scan.hits.length) {
    lines.push("None: " + scan.files.length + " file(s) read, no check fired.");
  } else {
    lines.push("| file | line | check |");
    lines.push("|---|---|---|");
    for (const h of scan.hits.slice(0, 100)) lines.push("| `" + h.path + "` | " + h.line + " | `" + h.id + "` |");
    if (scan.hits.length > 100) lines.push("| | | (" + (scan.hits.length - 100) + " more) |");
  }
  lines.push("");
  lines.push("## Findings filed");
  lines.push("");
  if (!findings.length) lines.push("None. The materials as they stand pass every automated check above.");
  else for (const f of findings) lines.push("- **" + f.severity + "** — " + f.title);
  lines.push("");
  lines.push("## What this cannot check");
  lines.push("");
  lines.push("- Whether a claim in the copy is true. That is a reading job, and the checklist's");
  lines.push("  review items are for the person publishing, not for a regex.");
  lines.push("- Git history, commit metadata, or the repository's public metadata. Those are the");
  lines.push("  other half of OPSEC and a separate pass.");
  lines.push("- Text in images, PDFs, or a rendered page. Only these files were read.");
  lines.push("");
  return lines.join("\n");
}
