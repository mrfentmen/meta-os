// labs/delaney-xcheck bridge note: the runner is Python (RDKit).
// This node test file documents the edge-case contract; the real edge
// tests run under pytest-style asserts in tests/edge_check.py.
// Run: node --test labs/delaney-xcheck/tests/edge.test.mjs (checks the
// contract file exists and the runner's selfcheck passes end to end).
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..");

test("edge contract covers empty, salts, charged", () => {
  const src = execFileSync("python3", [join(dir, "tests/edge_check.py"), "--list"], { encoding: "utf8" });
  assert.match(src, /empty/);
  assert.match(src, /salt/);
  assert.match(src, /charged/);
});

test("runner selfcheck passes end to end", () => {
  const out = execFileSync("python3", [join(dir, "xcheck.py"), "--selfcheck"], { encoding: "utf8" });
  assert.match(out, /ok benzene/);
  assert.equal((out.match(/^ok /gm) || []).length, 5);
});
