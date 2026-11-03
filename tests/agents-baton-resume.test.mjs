// CB2-385 — resuming from a baton continues the job; it never restarts it.
//
// The step-run log is the evidence: the resume path is asked what is left,
// and the test runs exactly those steps, so a completed step can only appear
// once. `stepIndex` is the last DONE step, so index 1 of [a, b, c] means c is
// the only step left.
import test from "node:test";
import assert from "node:assert/strict";
import { stepsRemaining } from "../agents/baton.mjs";

const STEPS = ["site the wall", "raise the wall", "cap the wall"];

test("CB2-385 a resumed job runs only the steps after the baton's last done step", () => {
  const baton = { jobId: "job-1", stepIndex: 1, state: "wall raised", artifacts: ["wall.txt"] };
  const remaining = stepsRemaining(baton, STEPS);
  assert.deepEqual(remaining, ["cap the wall"]);

  // Run the plan the way the watchman does, and keep the step-run log.
  const ran = [];
  for (const step of remaining) ran.push(step);
  assert.deepEqual(ran, ["cap the wall"], "a completed step is never run again");
  assert.equal(ran.filter((s) => s === "site the wall").length, 0);
  assert.equal(ran.filter((s) => s === "raise the wall").length, 0);
});

test("CB2-385b a baton at the last step has nothing left, and one before the first has everything", () => {
  assert.deepEqual(stepsRemaining({ stepIndex: 2 }, STEPS), [], "the last step is done");
  assert.deepEqual(stepsRemaining({ stepIndex: 3 }, STEPS), [], "past the end is still nothing left");
  assert.deepEqual(stepsRemaining({ stepIndex: -1 }, STEPS), STEPS, "nothing done yet means every step");
});

test("CB2-385c a baton that cannot be resumed is refused, never restarted from zero", () => {
  for (const bad of [null, {}, { stepIndex: null }, { stepIndex: 1.5 }, { stepIndex: -2 }]) {
    assert.throws(
      () => stepsRemaining(bad, STEPS),
      /baton resume: baton has no usable step index/,
      "refused by name: " + JSON.stringify(bad),
    );
  }
  assert.throws(() => stepsRemaining({ stepIndex: 0 }, []), /a step list is required/);
  assert.throws(() => stepsRemaining({ stepIndex: 0 }, null), /a step list is required/);
});
