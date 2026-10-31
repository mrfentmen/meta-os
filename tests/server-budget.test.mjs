// Budget guardrail tests for the Node direct Spark path
// (LANE A fix, 2026-10-30): server/budget.mjs is the Node mirror of
// server/queue/spark_guardrail.py and shares its ledger file, so
// the queue path and the assess.mjs fallback path now enforce the
// same $75 test budget. All state here lives in temp directories;
// no test touches the real ledger and no test fires a live call
// (stub fetch only, fake test key).

import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  BudgetError,
  BudgetStop,
  TEST_BUDGET_USD,
  budgetStatus,
  checkBudget,
  estimateCostUsd,
  loadBudgetState,
  recordBudgetCall,
} from "../server/budget.mjs";
import { assessWithModel, ModelError, SPARK_MODEL } from "../server/model.mjs";

function tempStatePath() {
  return join(mkdtempSync(join(tmpdir(), "trio-budget-")), "spark_guardrail_state.json");
}

const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46]);
const INPUT = {
  product: "ignis",
  timestamp: "2026-10-30T12:00:00.000Z",
  imageBytes: JPEG_BYTES,
  mediaType: "image/jpeg",
};
const GATE_AND_KEY = { ASSESS_LIVE_MODEL: "1", SPARK_API_KEY: "test-key-not-real" };

function countingFetch(response) {
  const calls = [];
  const fn = async (url, opts) => {
    calls.push({ url, opts });
    return response;
  };
  fn.calls = calls;
  return fn;
}

function sparkJsonResponse() {
  const assessment = {
    product: "ignis",
    timestamp: INPUT.timestamp,
    observations: [],
    assessment: {
      category: "no hazard visible",
      summary: "Nothing visible.",
      uncertainty: [],
      requires_human_review: false,
    },
    processing: { model: SPARK_MODEL, latency_ms: null },
  };
  return {
    ok: true,
    status: 200,
    json: async () => ({
      model: SPARK_MODEL,
      usage: { prompt_tokens: 1000, completion_tokens: 1000 },
      choices: [{ message: { content: JSON.stringify(assessment) } }],
    }),
  };
}

test("budget: missing state file is a fresh ledger, check passes", () => {
  const path = tempStatePath();
  assert.deepEqual(loadBudgetState(path), { calls: 0, est_cost_usd: 0.0, log: [] });
  checkBudget(path); // must not throw
  assert.deepEqual(budgetStatus(path), {
    calls: 0,
    est_cost_usd: 0,
    test_budget_usd: TEST_BUDGET_USD,
    remaining_usd: 75,
  });
});

test("budget: record writes the Python guardrail's exact state shape and cost math", () => {
  const path = tempStatePath();
  const est = recordBudgetCall(
    "assess:ignis",
    SPARK_MODEL,
    { prompt_tokens: 1_000_000, completion_tokens: 1_000_000 },
    42,
    path,
  );
  assert.equal(est, 1.25 + 4.25); // rate card: $1.25/M in, $4.25/M out
  const state = JSON.parse(readFileSync(path, "utf8"));
  assert.equal(state.calls, 1);
  assert.equal(state.est_cost_usd, 5.5);
  assert.equal(state.log.length, 1);
  const entry = state.log[0];
  assert.equal(entry.kind, "assess:ignis");
  assert.equal(entry.model, SPARK_MODEL);
  assert.deepEqual(entry.usage, { input_tokens: 1_000_000, output_tokens: 1_000_000 });
  assert.equal(entry.latency_ms, 42);
  assert.equal(entry.est_cost_usd, 5.5);
  assert.equal(entry.cum_est_cost_usd, 5.5);
  assert.ok(entry.ts.endsWith("+00:00"), "ts matches Python isoformat (+00:00)");
  assert.equal(estimateCostUsd({ input_tokens: 500_000, output_tokens: 0 }), 0.625);
  assert.equal(estimateCostUsd(undefined), 0);
});

test("budget: the Python guardrail reads a Node-written ledger (shared format)", () => {
  const path = tempStatePath();
  recordBudgetCall("assess:vigiles", SPARK_MODEL, { prompt_tokens: 2000, completion_tokens: 500 }, 7, path);
  const out = execFileSync(
    "python3",
    [
      "-c",
      [
        "import importlib.util, json, sys",
        "spec = importlib.util.spec_from_file_location('g', 'server/queue/spark_guardrail.py')",
        "g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)",
        "print(json.dumps(g.status(sys.argv[1])))",
      ].join("\n"),
      path,
    ],
    { cwd: new URL("..", import.meta.url).pathname, encoding: "utf8" },
  );
  const status = JSON.parse(out);
  assert.equal(status.calls, 1);
  assert.equal(status.est_cost_usd, 0.004625);
  assert.equal(status.test_budget_usd, 75.0);
});

test("budget: check refuses at or past the cap, passes below it", () => {
  const atCap = tempStatePath();
  writeFileSync(atCap, JSON.stringify({ calls: 9, est_cost_usd: 75.0, log: [] }));
  assert.throws(() => checkBudget(atCap), BudgetStop);
  const below = tempStatePath();
  writeFileSync(below, JSON.stringify({ calls: 9, est_cost_usd: 74.99, log: [] }));
  checkBudget(below); // must not throw — mirrors the Python check
});

test("budget: corrupt or malformed state fails closed", () => {
  const corrupt = tempStatePath();
  writeFileSync(corrupt, "{not json");
  assert.throws(() => checkBudget(corrupt), BudgetError);
  const malformed = tempStatePath();
  writeFileSync(malformed, JSON.stringify({ calls: "many", est_cost_usd: 0, log: [] }));
  assert.throws(() => checkBudget(malformed), BudgetError);
});

test("model: at the budget cap the direct call is refused BEFORE any fetch", async () => {
  const path = tempStatePath();
  writeFileSync(path, JSON.stringify({ calls: 3, est_cost_usd: 75.0, log: [] }));
  const fetch = countingFetch(sparkJsonResponse());
  await assert.rejects(
    () => assessWithModel(INPUT, GATE_AND_KEY, { fetch, budgetPath: path }),
    (err) => err instanceof ModelError && /GUARDRAIL STOP/.test(err.message),
  );
  assert.equal(fetch.calls.length, 0);
});

test("model: an unreadable budget ledger fails closed, no fetch happens", async () => {
  const path = tempStatePath();
  writeFileSync(path, "not a ledger");
  const fetch = countingFetch(sparkJsonResponse());
  await assert.rejects(
    () => assessWithModel(INPUT, GATE_AND_KEY, { fetch, budgetPath: path }),
    (err) => err instanceof ModelError,
  );
  assert.equal(fetch.calls.length, 0);
});

test("model: a completed direct call is recorded in the shared ledger", async () => {
  const path = tempStatePath();
  const fetch = countingFetch(sparkJsonResponse());
  const result = await assessWithModel(INPUT, GATE_AND_KEY, { fetch, budgetPath: path });
  assert.equal(result.assessment.category, "no hazard visible");
  assert.equal(fetch.calls.length, 1);
  const state = JSON.parse(readFileSync(path, "utf8"));
  assert.equal(state.calls, 1);
  // 1000 in + 1000 out at the published rate card.
  assert.equal(state.est_cost_usd, 0.0055);
  assert.equal(state.log[0].kind, "assess:ignis");
});
