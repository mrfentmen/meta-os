import { test } from "node:test";
import assert from "node:assert/strict";
import { budgetRemainingMs, elapsedMs } from "../agents/clock.mjs";

test("the same seed times give the same elapsed values twice", () => {
  const first = elapsedMs(1_000, 1_750);
  const second = elapsedMs(1_000, 1_750);
  assert.deepEqual(first, second);
  assert.deepEqual(first, { ms: 750, jumped: false, reason: null });
});

test("a backward jump is flagged, never returned as negative time", () => {
  const result = elapsedMs(2_000, 1_500);
  assert.equal(result.ms, 0);
  assert.equal(result.jumped, true);
  assert.equal(result.reason, "clock-went-backwards");
});

test("budget remaining is deterministic and clamps at zero", () => {
  assert.deepEqual(budgetRemainingMs({ capMs: 1_000, spentMs: 400 }), {
    remaining: 600,
    capped: true,
    overrun: false,
  });
  const over = budgetRemainingMs({ capMs: 1_000, spentMs: 1_200 });
  assert.equal(over.remaining, 0);
  assert.equal(over.overrun, true);
  assert.equal(budgetRemainingMs({ capMs: null, spentMs: 10 }).remaining, Infinity);
});
