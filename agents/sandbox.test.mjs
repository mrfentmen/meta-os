// Tests for the Meta OS ephemeral sandboxes (agents/sandbox.mjs).
//
// Run from the worktree root:  node --test agents/sandbox.test.mjs
//
// These tests run REAL containers. If no docker runtime or no
// ubuntu:24.04 image is present, they skip (NO_DOCKER/NO_IMAGE) instead
// of failing — the module's contract is to fail loudly, the tests'
// contract is to never invent an environment.

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, test } from "node:test";

import { imagePresent, probeDocker, runSandbox } from "./sandbox.mjs";

const IMAGE = process.env.SANDBOX_TEST_IMAGE || "ubuntu:24.04";

function available() {
  if (!probeDocker().ok) return false;
  return imagePresent(IMAGE);
}

describe("sandbox", () => {
  test("probe reports the runtime", () => {
    const p = probeDocker();
    if (!p.ok) {
      console.log("# SKIP: no docker runtime");
      return;
    }
    assert.ok(p.server.length > 0);
  });

  test("echo runs, output captured, /work shared", () => {
    if (!available()) {
      console.log("# SKIP: need docker + " + IMAGE);
      return;
    }
    const r = runSandbox(["sh", "-c", "echo from-inside > /work/out.txt; echo done"], { image: IMAGE, timeoutMs: 60000 });
    assert.equal(r.exit, 0);
    assert.match(r.stdout, /done/);
    assert.equal(readFileSync(path.join(r.work, "out.txt"), "utf8"), "from-inside\n");
    rmSync(r.work, { recursive: true, force: true });
  });

  test("default network is none: only loopback exists", () => {
    if (!available()) {
      console.log("# SKIP: need docker + " + IMAGE);
      return;
    }
    const r = runSandbox(["sh", "-c", "ls /sys/class/net | tr '\\n' ' '"], { image: IMAGE, timeoutMs: 60000 });
    assert.equal(r.exit, 0);
    assert.match(r.stdout.trim(), /^lo\b/);
    assert.doesNotMatch(r.stdout, /eth0/);
    rmSync(r.work, { recursive: true, force: true });
  });

  test("timeout kills a stuck run", () => {
    if (!available()) {
      console.log("# SKIP: need docker + " + IMAGE);
      return;
    }
    const t0 = Date.now();
    const r = runSandbox(["sleep", "60"], { image: IMAGE, timeoutMs: 5000 });
    const dt = Date.now() - t0;
    assert.equal(r.timedOut, true);
    assert.ok(dt < 30000, `kill took too long: ${dt}ms`);
    rmSync(r.work, { recursive: true, force: true });
  });

  test("missing image fails loudly without pulling", () => {
    if (!probeDocker().ok) {
      console.log("# SKIP: no docker runtime");
      return;
    }
    try {
      runSandbox(["true"], { image: "no-such-image-xyz:0", timeoutMs: 15000 });
      assert.fail("should have refused the missing image");
    } catch (e) {
      assert.equal(e.code, "NO_IMAGE");
    }
  });
});
