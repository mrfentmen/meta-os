// Tests for the Meta OS approval airlock (agents/approve.mjs).
//
// Run from the worktree root:  node --test agents/approve.test.mjs
//
// Policy + approvals + audit all live in temp dirs. The only commands
// ever executed by gateCommand in tests are `true`-style no-ops.

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, test } from "node:test";

import {
  checkCommand,
  gateCommand,
  loadPolicy,
  readApproval,
  recordApproval,
  requestApproval,
} from "./approve.mjs";

function setup() {
  const dir = mkdtempSync(path.join(tmpdir(), "approve-"));
  const policy = path.join(dir, "policy.json");
  writeFileSync(
    policy,
    JSON.stringify({
      rules: [
        { match: "^true$|^echo ", decision: "allow", reason: "harmless builtins" },
        { match: "rm -rf|mkfs|dd ", decision: "deny", reason: "destructive" },
        { match: "curl|wget", decision: "ask", reason: "network egress" },
      ],
      default: "ask",
    }),
  );
  return { dir, policy, audit: path.join(dir, "audit.jsonl"), approvals: path.join(dir, "appr") };
}

describe("approve", () => {
  test("allow/deny/ask routing with first-match-wins", () => {
    const s = setup();
    try {
      const p = loadPolicy(s.policy);
      assert.equal(checkCommand(p, "echo hi").decision, "allow");
      assert.equal(checkCommand(p, "rm -rf /tmp/x").decision, "deny");
      assert.equal(checkCommand(p, "curl https://x").decision, "ask");
      assert.equal(checkCommand(p, "unlisted-thing").decision, "ask");
    } finally {
      rmSync(s.dir, { recursive: true, force: true });
    }
  });

  test("bad policy files fail loudly", () => {
    const { dir } = setup();
    const bad = path.join(dir, "bad.json");
    writeFileSync(bad, "{not json");
    try {
      loadPolicy(bad);
      assert.fail("should have thrown");
    } catch (e) {
      assert.equal(e.code, "BAD_POLICY");
    }
    try {
      loadPolicy(path.join(dir, "missing.json"));
      assert.fail("should have thrown");
    } catch (e) {
      assert.equal(e.code, "NO_POLICY");
    }
    rmSync(dir, { recursive: true, force: true });
  });

  test("gate runs allowed, refuses denied, holds ask without human", () => {
    const s = setup();
    try {
      const p = loadPolicy(s.policy);
      const ok = gateCommand(p, ["true"], { audit: s.audit });
      assert.equal(ok.ran, true);
      assert.equal(ok.exit, 0);
      const no = gateCommand(p, ["rm", "-rf", "/tmp/x"], { audit: s.audit });
      assert.equal(no.ran, false);
      const held = gateCommand(p, ["curl", "https://x"], { audit: s.audit, approvals: s.approvals });
      assert.equal(held.ran, false);
      assert.equal(held.needsHuman, true);
      const lines = readFileSync(s.audit, "utf8").trim().split("\n");
      assert.equal(lines.length, 3);
      assert.ok(JSON.parse(lines[0]).decision);
    } finally {
      rmSync(s.dir, { recursive: true, force: true });
    }
  });

  test("ask runs after a recorded human yes, not after no", () => {
    const s = setup();
    try {
      const p = loadPolicy(s.policy);
      const req = requestApproval(s.approvals, "curl https://x");
      assert.equal(readApproval(s.approvals, req.token).approved, false);
      recordApproval(s.approvals, req.token, "yes");
      const yes = gateCommand(p, ["true"], { approvals: s.approvals, token: req.token });
      assert.equal(yes.ran, true);
      const req2 = requestApproval(s.approvals, "curl https://y");
      recordApproval(s.approvals, req2.token, "no");
      const no = gateCommand(p, ["curl", "https://y"], { approvals: s.approvals, token: req2.token });
      assert.equal(no.ran, false);
    } finally {
      rmSync(s.dir, { recursive: true, force: true });
    }
  });
});
