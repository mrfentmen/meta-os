// Node mirror of the Python spend guardrail
// (server/queue/spark_guardrail.py), for the DIRECT Node Spark
// transport in server/model.mjs. Before this module existed, the
// Python queue path enforced the $75 test budget but the Node direct
// path (which server/assess.mjs falls back to on any queue failure)
// called Muse Spark with no spend check at all.
//
// Both implementations share ONE ledger: the same state file the
// Python guardrail uses (server/queue/spark_guardrail_state.json),
// the same JSON shape, the same rate card, and the same semantics:
//   - state: { calls, est_cost_usd, log: [ { ts, kind, model,
//     usage: { input_tokens, output_tokens }, latency_ms,
//     est_cost_usd, cum_est_cost_usd } ] }
//   - a missing state file is a fresh ledger (calls 0, $0.00);
//   - checkBudget refuses BEFORE a call when the recorded estimate
//     has reached the budget;
//   - recordBudgetCall counts one completed call, after the fact,
//     at estimated cost (usage tokens x rate card — estimates only).
// A state file that exists but cannot be read or parsed is a hard
// stop (fail closed): BudgetError propagates and no call is sent.
//
// Scope, honestly (same as the Python module): the DEV helper
// transport (TRIO_SPARK_VIA_HELPER=1, explicit opt-in only) still
// delegates to spark_call.py, whose own guardrail_state.json beside
// that script is the counter on that path — calls are never counted
// in both ledgers.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const TEST_BUDGET_USD = 75.0;
export const RATE_IN_PER_M = 1.25;
export const RATE_OUT_PER_M = 4.25;

export const DEFAULT_BUDGET_STATE_PATH = fileURLToPath(
  new URL("./queue/spark_guardrail_state.json", import.meta.url),
);

export class BudgetError extends Error {
  constructor(message) {
    super(message);
    this.name = "BudgetError";
  }
}

export class BudgetStop extends BudgetError {
  constructor(message) {
    super(message);
    this.name = "BudgetStop";
  }
}

function round6(x) {
  return Math.round(x * 1e6) / 1e6;
}

// Python load_state: missing file -> fresh ledger; an existing file
// that cannot be read or parsed raises. Malformed shapes (wrong
// types) raise here too, mirroring the KeyError/TypeError the Python
// guardrail would hit on the same data.
export function loadBudgetState(path = DEFAULT_BUDGET_STATE_PATH) {
  if (!existsSync(path)) {
    return { calls: 0, est_cost_usd: 0.0, log: [] };
  }
  let raw;
  try {
    raw = readFileSync(path, "utf8");
  } catch (err) {
    throw new BudgetError(
      `GUARDRAIL STOP: budget state at ${path} cannot be read (${err.message}). No call sent.`,
    );
  }
  let state;
  try {
    state = JSON.parse(raw);
  } catch {
    throw new BudgetError(
      `GUARDRAIL STOP: budget state at ${path} is not valid JSON. No call sent.`,
    );
  }
  if (
    typeof state !== "object" ||
    state === null ||
    typeof state.calls !== "number" ||
    typeof state.est_cost_usd !== "number" ||
    !Array.isArray(state.log)
  ) {
    throw new BudgetError(
      `GUARDRAIL STOP: budget state at ${path} is malformed. No call sent.`,
    );
  }
  return state;
}

function saveBudgetState(state, path) {
  // Python writes json.dump(state, indent=1).
  writeFileSync(path, JSON.stringify(state, null, 1));
}

// Python check(): refuse when the recorded spend has reached the
// budget. Reads the state fresh so a Python-side call recorded a
// moment ago is honored here.
export function checkBudget(path = DEFAULT_BUDGET_STATE_PATH) {
  const state = loadBudgetState(path);
  if (state.est_cost_usd >= TEST_BUDGET_USD) {
    throw new BudgetStop(
      `GUARDRAIL STOP: estimated test spend $${state.est_cost_usd.toFixed(4)} has reached the ` +
        `$${TEST_BUDGET_USD.toFixed(2)} test budget. No call sent.`,
    );
  }
}

// Python estimate(): usage tokens x published rate card.
export function estimateCostUsd(usage) {
  const u = usage ?? {};
  const inTok = u.prompt_tokens || u.input_tokens || 0;
  const outTok = u.completion_tokens || u.output_tokens || 0;
  return (inTok / 1e6) * RATE_IN_PER_M + (outTok / 1e6) * RATE_OUT_PER_M;
}

// Python record(): count one completed call. Returns its estimated
// cost. Synchronous read-modify-write, so calls within one Node
// process cannot interleave mid-update; the Python guardrail's lock
// has exactly the same (single-process) scope.
export function recordBudgetCall(kind, model, usage, latencyMs, path = DEFAULT_BUDGET_STATE_PATH) {
  const state = loadBudgetState(path);
  const est = estimateCostUsd(usage);
  state.calls += 1;
  state.est_cost_usd = round6(state.est_cost_usd + est);
  state.log.push({
    // Python: datetime.now(timezone.utc).isoformat() — "+00:00" form.
    ts: new Date().toISOString().replace("Z", "+00:00"),
    kind,
    model,
    usage: {
      input_tokens: (usage ?? {}).prompt_tokens || (usage ?? {}).input_tokens || 0,
      output_tokens: (usage ?? {}).completion_tokens || (usage ?? {}).output_tokens || 0,
    },
    latency_ms: latencyMs,
    est_cost_usd: round6(est),
    cum_est_cost_usd: state.est_cost_usd,
  });
  saveBudgetState(state, path);
  return est;
}

// Python status().
export function budgetStatus(path = DEFAULT_BUDGET_STATE_PATH) {
  const state = loadBudgetState(path);
  return {
    calls: state.calls,
    est_cost_usd: state.est_cost_usd,
    test_budget_usd: TEST_BUDGET_USD,
    remaining_usd: Math.round((TEST_BUDGET_USD - state.est_cost_usd) * 10000) / 10000,
  };
}
