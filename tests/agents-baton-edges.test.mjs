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

test("CB2-384 a baton with no usable step index is refused at construction", () => {
  const dir = mkdtempSync(join(tmpdir(), "agents-baton-"));
  try {
    // Every case here is a baton whose next step is unknowable. A written one
    // would be resumed from the wrong place, so nothing is written at all.
    for (const bad of [
      null,
      {},
      { state: "half way" },
      { stepIndex: null },
      { stepIndex: "2" },
      { stepIndex: 1.5 },
      { stepIndex: -2 },
    ]) {
      assert.throws(
        () => writeBaton(dir, bad),
        /baton refused: missing step index/,
        "refused by name: " + JSON.stringify(bad),
      );
    }
    assert.equal(readBaton(dir), null, "a refused baton leaves no file behind");

    // -1 is the real "nothing done yet" value, and 0 is the first step: both
    // are accepted, so the refusal is about an unknown index, not about zero.
    for (const stepIndex of [-1, 0, 3]) {
      const written = writeBaton(dir, { stepIndex, state: "s" });
      assert.equal(written.stepIndex, stepIndex);
      assert.equal(readBaton(dir).stepIndex, stepIndex, "the index survives the round trip");
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
