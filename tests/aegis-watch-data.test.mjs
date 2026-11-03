// CB2-497 — Aegis own-ground watch data.
//
// There is no watch-target data file in the tree: aegis/watch-targets.mjs is
// the module that turns a list of own repos and pages into the exact target
// shape the agent poller reads. So the own-ground rule is pinned where it
// lives: every target this module emits is a local file path, never a URL and
// never a remote fetch, and a page on Del's own ground resolves to a local
// path like every other entry.
//
// The four own domains are the published set (meta-os.pages.dev,
// muse-relay-live.pages.dev, clipraiders.com, watchpeoplefight.com). The test
// asserts the module cannot turn any of them — or a third-party host — into a
// network target.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { buildWatchTargets } from "../aegis/watch-targets.mjs";

const OWN_DOMAINS = [
  "meta-os.pages.dev",
  "muse-relay-live.pages.dev",
  "clipraiders.com",
  "watchpeoplefight.com",
];

const root = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-watch-"));
for (const d of OWN_DOMAINS) fs.writeFileSync(path.join(root, d), "page\n");

test("CB2-497 every own-ground page becomes a local file target, never a URL", () => {
  const { targets, missing } = buildWatchTargets({ pages: OWN_DOMAINS, root });
  assert.equal(targets.length, OWN_DOMAINS.length);
  assert.deepEqual(missing, [], "every own page is present on disk");
  for (const t of targets) {
    assert.deepEqual(Object.keys(t).sort(), ["path", "type"], "target is the poller shape");
    assert.equal(t.type, "file", "file target only");
    assert.ok(path.isAbsolute(t.path), "absolute path");
    assert.ok(t.path.startsWith(root + path.sep), "inside the watched root");
    assert.doesNotMatch(t.path, /^https?:/, "no network target");
  }
  const paths = targets.map((t) => path.basename(t.path)).sort();
  assert.deepEqual(paths, [...OWN_DOMAINS].sort());
});

test("CB2-497b a third-party host cannot become a network target either", () => {
  const { targets } = buildWatchTargets({ pages: ["https://example.com/x"], root });
  assert.equal(targets.length, 1);
  assert.equal(targets[0].type, "file");
  assert.doesNotMatch(targets[0].path, /^https?:/, "a pasted URL is treated as a path, not fetched");
});

test("CB2-497c the same page listed twice is watched once", () => {
  const { targets } = buildWatchTargets({ pages: ["clipraiders.com", "./clipraiders.com"], root });
  assert.equal(targets.length, 1, "duplicate collapses to one target");
});

test("CB2-497d an empty watch list produces no targets and no missing entries", () => {
  assert.deepEqual(buildWatchTargets({ root }), { targets: [], missing: [] });
});
