// Tests for the Meta OS workspace snapshots (agents/snapshots.mjs).
//
// Run from the worktree root:  node --test agents/snapshots.test.mjs
//
// Each test builds a real temp workspace and a real temp store. Nothing
// leaves /tmp, nothing is mocked, and rollback tests always run against
// the temp workspace — never the repo.

import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, test } from "node:test";

import {
  createSnapshot,
  listSnapshots,
  rollbackDiff,
  rollbackSnapshot,
  verifySnapshot,
} from "./snapshots.mjs";

function scratch() {
  const work = mkdtempSync(path.join(tmpdir(), "snap-work-"));
  const store = mkdtempSync(path.join(tmpdir(), "snap-store-"));
  return { work, store };
}

function seed(work) {
  writeFileSync(path.join(work, "a.txt"), "alpha");
  mkdirSync(path.join(work, "sub"), { recursive: true });
  writeFileSync(path.join(work, "sub", "b.txt"), "beta");
  mkdirSync(path.join(work, "node_modules", "dep"), { recursive: true });
  writeFileSync(path.join(work, "node_modules", "dep", "x.js"), "skip me");
}

describe("snapshots", () => {
  test("snapshot captures files, skips node_modules", () => {
    const { work, store } = scratch();
    try {
      seed(work);
      const r = createSnapshot(work, store, { label: "before-refactor" });
      assert.match(r.id, /^\d{4}-\d{2}-\d{2}T/);
      assert.equal(r.files, 2);
      const listed = listSnapshots(store);
      assert.equal(listed.length, 1);
      assert.equal(listed[0].label, "before-refactor");
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(store, { recursive: true, force: true });
    }
  });

  test("verify passes on an intact snapshot", () => {
    const { work, store } = scratch();
    try {
      seed(work);
      const { id } = createSnapshot(work, store);
      const v = verifySnapshot(store, id);
      assert.equal(v.bad.length, 0);
      assert.equal(v.files, 2);
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(store, { recursive: true, force: true });
    }
  });

  test("dry-run rollback diffs, applies nothing", () => {
    const { work, store } = scratch();
    try {
      seed(work);
      const { id } = createSnapshot(work, store);
      writeFileSync(path.join(work, "a.txt"), "CORRUPTED");
      writeFileSync(path.join(work, "new.txt"), "junk");
      const dry = rollbackSnapshot(store, id, {});
      assert.equal(dry.applied, false);
      assert.deepEqual(
        dry.actions.map((a) => `${a.op}:${a.path}`).sort(),
        ["delete:new.txt", "restore:a.txt"],
      );
      assert.equal(readFileSync(path.join(work, "a.txt"), "utf8"), "CORRUPTED");
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(store, { recursive: true, force: true });
    }
  });

  test("--apply restores corrupted, deleted, and added files", () => {
    const { work, store } = scratch();
    try {
      seed(work);
      const { id } = createSnapshot(work, store);
      writeFileSync(path.join(work, "a.txt"), "CORRUPTED");
      rmSync(path.join(work, "sub", "b.txt"));
      writeFileSync(path.join(work, "new.txt"), "junk");
      const done = rollbackSnapshot(store, id, { apply: true });
      assert.equal(done.applied, true);
      assert.equal(readFileSync(path.join(work, "a.txt"), "utf8"), "alpha");
      assert.equal(readFileSync(path.join(work, "sub", "b.txt"), "utf8"), "beta");
      assert.equal(
        (() => {
          try {
            readFileSync(path.join(work, "new.txt"));
            return true;
          } catch {
            return false;
          }
        })(),
        false,
      );
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(store, { recursive: true, force: true });
    }
  });

  test("rollback to the wrong target is refused", () => {
    const { work, store } = scratch();
    const elsewhere = mkdtempSync(path.join(tmpdir(), "snap-else-"));
    try {
      seed(work);
      const { id } = createSnapshot(work, store);
      try {
        rollbackDiff(store, id, elsewhere);
        assert.fail("should have refused the wrong target");
      } catch (e) {
        assert.equal(e.code, "TARGET_MISMATCH");
      }
    } finally {
      rmSync(work, { recursive: true, force: true });
      rmSync(store, { recursive: true, force: true });
      rmSync(elsewhere, { recursive: true, force: true });
    }
  });

  test("unknown snapshot id fails loudly", () => {
    const { store } = scratch();
    try {
      try {
        verifySnapshot(store, "nope");
        assert.fail("should have failed on unknown id");
      } catch (e) {
        assert.equal(e.code, "NO_SNAPSHOT");
      }
    } finally {
      rmSync(store, { recursive: true, force: true });
    }
  });
});
