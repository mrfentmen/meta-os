import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { handoffChain, readBaton, writeBaton } from "../agents/baton.mjs";

test("a baton carries the job id, step index, state, and artifacts", () => {
  const dir = mkdtempSync(join(tmpdir(), "agents-baton-"));
  try {
    writeBaton(dir, {
      jobId: "job-1",
      stepIndex: 2,
      state: "halfway",
      artifacts: ["a.txt"],
      nextStep: "finish b",
    });
    const baton = readBaton(dir);
    assert.equal(baton.jobId, "job-1");
    assert.equal(baton.stepIndex, 2);
    assert.equal(baton.state, "halfway");
    assert.deepEqual(baton.artifacts, ["a.txt"]);
    assert.equal(typeof baton.ts, "string");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a handoff chain with a changed job id is refused", () => {
  assert.throws(
    () =>
      handoffChain([
        { jobId: "job-1", author: "milo" },
        { jobId: "job-2", author: "bond" },
      ]),
    /job id changed at link 1/,
  );
});

test("a handoff chain keeps one job id and ordered authors", () => {
  assert.deepEqual(
    handoffChain([
      { jobId: "job-1", author: "milo" },
      { jobId: "job-1", author: "bond" },
    ]),
    { jobId: "job-1", authors: ["milo", "bond"] },
  );
});
