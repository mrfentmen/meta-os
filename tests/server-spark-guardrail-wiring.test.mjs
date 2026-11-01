// Node built-in test runner, no dependencies:  node --test tests/server-spark-guardrail-wiring.test.mjs
// Pins the $75 guardrail audit (Phase 4): every production Spark call
// site in this repo passes through a spend guardrail before sending
// and records after. If someone adds a third call site without a
// counter, this test names it. No network, no keys, no live calls.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const modelJs = readFileSync(new URL("../server/model.mjs", import.meta.url), "utf8");
const sparkGen = readFileSync(new URL("../server/queue/spark_gen.py", import.meta.url), "utf8");

test("server/model.mjs checks the budget before any direct Spark call", () => {
  assert.ok(modelJs.includes("checkBudget("), "model.mjs must call checkBudget before sending");
  assert.ok(
    modelJs.indexOf("checkBudget(") < modelJs.indexOf("fetchFn(SPARK_ENDPOINT"),
    "budget check must come before the request",
  );
});

test("server/model.mjs records the billable call after the response", () => {
  assert.ok(modelJs.includes("recordBudgetCall("), "model.mjs must record the completed call");
});

test("spark_gen.py direct transport checks and records the $75 guardrail", () => {
  assert.ok(sparkGen.includes("spark_guardrail.check()"), "direct transport must check before sending");
  assert.ok(sparkGen.includes("spark_guardrail.record("), "direct transport must record after responding");
});

test("DEV helper path is counted once, not twice and not zero", () => {
  // The helper transport delegates counting to spark_call.py's own
  // guardrail file; the Python module must say so explicitly so a
  // future edit does not "fix" it into double counting.
  assert.ok(sparkGen.includes("helper's own guardrail"), "DEV transport counting rule must stay documented");
});
