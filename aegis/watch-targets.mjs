// Meta Aegis — D3, the watch-target pack (AEGIS_SPEC.md, "Watch").
//
// Turns "these repos and these pages" into the exact target shape the agent layer's poller
// already reads -- {type: "file", path} -- so Aegis is a registry agent with watch targets,
// not a watch program (the boss's 2026-11-02 ruling). This module never watches, spawns, or
// wakes anything: it writes the list, and agents/runtime.mjs does the polling.
import fs from "node:fs";
import path from "node:path";

export class WatchTargetError extends Error {}

function assertStrings(name, v) {
  if (!Array.isArray(v)) throw new WatchTargetError("targets: " + name + " must be an array");
  for (const x of v) {
    if (typeof x !== "string" || x.trim() === "") {
      throw new WatchTargetError("targets: " + name + " entries must be non-empty strings");
    }
  }
}

// A repo tip is two files. A commit moves the checked-out ref; a checkout moves HEAD. Watching
// only one of them makes the watch lie in the other case -- a commit would be missed, and a
// branch switch would look like no change at all.
export function repoTipTargets(repoDir) {
  const repo = path.resolve(repoDir);
  const git = path.join(repo, ".git");
  let st;
  try { st = fs.statSync(git); } catch { throw new WatchTargetError("repo: no .git in " + repo); }
  if (!st.isDirectory()) {
    throw new WatchTargetError(
      "repo: .git is a file (worktree or submodule); this pack watches plain checkouts only: " + repo);
  }
  const head = path.join(git, "HEAD");
  let text;
  try { text = fs.readFileSync(head, "utf8"); } catch { throw new WatchTargetError("repo: .git has no HEAD: " + repo); }

  const targets = [{ type: "file", path: head }];
  const m = /^ref:\s*(.+?)\s*$/.exec(text);
  if (m) {
    const full = path.resolve(git, m[1]);
    // HEAD is a file inside the repo; a ref that climbs out of .git would point the watch at
    // something that is not the repo.
    if (full !== git && !full.startsWith(git + path.sep)) {
      throw new WatchTargetError("repo: HEAD points outside .git: " + m[1]);
    }
    targets.push({ type: "file", path: full });
  }
  return targets;   // detached HEAD: HEAD alone is the tip
}

export function buildWatchTargets({ repos = [], pages = [], files = [], root = "." } = {}) {
  assertStrings("repos", repos);
  assertStrings("pages", pages);
  assertStrings("files", files);
  const base = path.resolve(root);
  const seen = new Set();
  const targets = [];
  const missing = [];
  const add = (p) => {
    const abs = path.normalize(path.isAbsolute(p) ? p : path.resolve(base, p));
    const key = "file:" + abs;
    // pollWatch keys targets by type+path: a duplicate would be polled twice and reported
    // twice, which reads as two changes when one file moved.
    if (seen.has(key)) return;
    seen.add(key);
    targets.push({ type: "file", path: abs });
    if (!fs.existsSync(abs)) missing.push(abs);
  };
  for (const r of repos) for (const t of repoTipTargets(r)) add(t.path);
  for (const p of pages) add(p);
  for (const f of files) add(f);
  return { targets, missing };
}
