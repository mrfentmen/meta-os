import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { repoTipTargets, buildWatchTargets, WatchTargetError } from "../aegis/watch-targets.mjs";
import { pollWatch } from "../agents/runtime.mjs";

function fakeRepo({ head = "ref: refs/heads/main\n", ref = "abc123\n", branch = "refs/heads/main" } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-repo-"));
  const git = path.join(root, ".git");
  fs.mkdirSync(path.dirname(path.join(git, branch)), { recursive: true });
  fs.writeFileSync(path.join(git, "HEAD"), head);
  if (ref != null) fs.writeFileSync(path.join(git, branch), ref);
  return root;
}

test("a repo tip is HEAD plus the checked-out ref", () => {
  const repo = fakeRepo();
  const targets = repoTipTargets(repo);
  assert.deepEqual(targets.map((t) => t.path), [
    path.join(repo, ".git", "HEAD"),
    path.join(repo, ".git", "refs", "heads", "main"),
  ]);
  assert.ok(targets.every((t) => t.type === "file"));
});

test("a detached HEAD is one target, not a guess at a branch", () => {
  const repo = fakeRepo({ head: "deadbeef\n" });
  assert.deepEqual(repoTipTargets(repo).map((t) => t.path), [path.join(repo, ".git", "HEAD")]);
});

test("an unborn branch is still targeted, and reported missing", () => {
  const repo = fakeRepo({ ref: null });
  const r = buildWatchTargets({ repos: [repo] });
  assert.equal(r.targets.length, 2);
  assert.deepEqual(r.missing, [path.join(repo, ".git", "refs", "heads", "main")]);
});

test("non-repos and worktree-style .git files are refused", () => {
  assert.throws(() => repoTipTargets(fs.mkdtempSync(path.join(os.tmpdir(), "aegis-norepo-"))), WatchTargetError);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-worktree-"));
  fs.writeFileSync(path.join(root, ".git"), "gitdir: /elsewhere\n");
  assert.throws(() => repoTipTargets(root), WatchTargetError);
});

test("a ref that climbs out of .git is refused", () => {
  const repo = fakeRepo({ head: "ref: ../../etc/passwd\n" });
  assert.throws(() => repoTipTargets(repo), WatchTargetError);
});

test("targets are deduped and missing pages are named", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-pages-"));
  const page = path.join(dir, "listing.html");
  fs.writeFileSync(page, "<html></html>");
  const gone = path.join(dir, "not-yet.html");
  const r = buildWatchTargets({ pages: [page, page], files: [page, gone] });
  assert.equal(r.targets.length, 2);
  assert.deepEqual(r.missing, [gone]);
});

test("the real runtime poller reads the pack, quiet when nothing moved, loud when it did", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-poll-"));
  const page = path.join(dir, "listing.html");
  fs.writeFileSync(page, "<html>v1</html>");
  const { targets } = buildWatchTargets({ pages: [page] });

  const baseline = pollWatch(targets, {});
  assert.equal(Object.keys(baseline.state).length, targets.length);
  assert.deepEqual(pollWatch(targets, baseline.state).changes, []);

  fs.writeFileSync(page, "<html>v2</html>");
  fs.utimesSync(page, new Date(), new Date(Date.now() + 5000));
  const moved = pollWatch(targets, baseline.state);
  assert.equal(moved.changes.length, 1);
  assert.equal(moved.changes[0].key, "file:" + page);
});
