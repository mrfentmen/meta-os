// Meta Aegis — D1, the manifest collector (AEGIS_SPEC.md, "Sweep", v1).
//
// Walks one tree and reports every package manifest path it finds, with the ecosystem that
// would look after it. That is the whole job: the OSV sweep needs to know WHICH manifests
// exist before it can ask about them, and the inventory is worth having on its own because
// "what does this machine depend on" is a question nobody can answer from memory.
//
// Not in this file, on purpose: no network, no manifest parsing, no vulnerability claims.
// A manifest path is not a finding. D2 records findings, and only after a data source
// answered; anything else would be a claim without a source (AEGIS_SPEC, "What it never does").
//
// Host-side service, not kernel: it runs where the agent runs, needs no privileges, and is
// read-only. Wiring it into a Goose service would buy nothing until the kernel has spawn/kill.
import fs from "node:fs";
import path from "node:path";

export const MANIFESTS = {
  "package.json": "npm",
  "Cargo.toml": "cargo",
  "pyproject.toml": "pypi",
  "requirements.txt": "pypi",
  "go.mod": "go",
  "Gemfile": "gem",
  "composer.json": "packagist",
  "pom.xml": "maven",
};

// Skipped: VCS metadata and dependency caches. A cache holds manifests that were not written
// here (they arrive over the network), so counting them as the tree's own dependencies would
// overstate the ground. "vendor" is deliberately NOT skipped: vendored code ships, so it is
// part of the tree being watched.
export const SKIP_DIRS = new Set([
  ".git", ".hg", ".svn",
  "node_modules", "target", ".venv", "venv", "__pycache__",
  "dist", "build", ".next", ".cache",
]);

export const DEFAULT_MAX_DEPTH = 16;

export class CollectorError extends Error {}

function rel(base, abs) {
  return path.relative(base, abs).split(path.sep).join("/") || ".";
}

export function collectManifests(root, { maxDepth = DEFAULT_MAX_DEPTH, skipDirs = SKIP_DIRS } = {}) {
  const base = path.resolve(root);
  let st;
  try { st = fs.statSync(base); } catch { throw new CollectorError("collect: root does not exist: " + base); }
  if (!st.isDirectory()) throw new CollectorError("collect: root is not a directory: " + base);

  const manifests = [];
  const capped = [];
  const skipped = [];
  let scannedDirs = 0;
  let symlinksSkipped = 0;

  const walk = (abs, depth) => {
    // The cap is reported, not silent: a tree deeper than the cap is a tree this run did not
    // finish, and an inventory that hides that is worse than no inventory.
    if (depth > maxDepth) { capped.push(rel(base, abs)); return; }
    scannedDirs += 1;
    const entries = fs.readdirSync(abs, { withFileTypes: true })
      .sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    for (const e of entries) {
      const child = path.join(abs, e.name);
      // Never followed: a symlink can leave the tree or point back into it, and either one
      // turns a bounded walk into an unbounded one.
      if (e.isSymbolicLink()) { symlinksSkipped += 1; continue; }
      if (e.isDirectory()) {
        if (skipDirs.has(e.name)) { skipped.push({ path: rel(base, child), reason: "cache-or-vcs" }); continue; }
        walk(child, depth + 1);
        continue;
      }
      if (!e.isFile()) continue;
      const ecosystem = MANIFESTS[e.name];
      if (ecosystem) manifests.push({ path: rel(base, child), manifest: e.name, ecosystem });
    }
  };
  walk(base, 0);

  manifests.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  const byEcosystem = {};
  for (const m of manifests) byEcosystem[m.ecosystem] = (byEcosystem[m.ecosystem] || 0) + 1;

  return {
    root: base,
    manifests,
    counts: { total: manifests.length, byEcosystem },
    scannedDirs,
    symlinksSkipped,
    // Samples with exact counts, so a reader can tell "nothing was skipped" from "the first
    // fifty were". Truncation is stated, never silent.
    skipped: { count: skipped.length, sample: skipped.slice(0, 50) },
    capped: { count: capped.length, sample: capped.slice(0, 50) },
  };
}
