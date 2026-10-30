"""spark_guardrail.py — the $75 spend guardrail for the direct
Spark transport, ported from custom.meta-model-api/bin/spark_call.py.

Del's rule (2026-10-27): $75 build/test budget, $75 reserved. Every
direct-transport call is counted in spark_guardrail_state.json beside
this module, its estimated cost is logged (usage tokens x published
rate card — $1.25/M input, $4.25/M output, estimates only), and any
call that would start at or beyond the budget is REFUSED before it is
sent.

Scope, honestly: this guardrail counts the DIRECT transport
(SPARK_API_KEY path in spark_gen.py). The DEV helper transport
(TRIO_SPARK_VIA_HELPER=1) delegates to spark_call.py, whose own
guardrail_state.json beside that script is the counter on that path —
calls are never counted in both.
"""
import json
import os
import threading
from datetime import datetime, timezone

TEST_BUDGET_USD = 75.00
RATE_IN_PER_M = 1.25
RATE_OUT_PER_M = 4.25

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "spark_guardrail_state.json")

_lock = threading.Lock()


class GuardrailStop(RuntimeError):
    """Raised before any call that would start at/past the budget."""


def load_state(path=None):
    path = path or STATE_PATH
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"calls": 0, "est_cost_usd": 0.0, "log": []}


def _save_state(state, path):
    with open(path, "w") as f:
        json.dump(state, f, indent=1)


def check(state=None, path=None):
    """Refuse (raise GuardrailStop) when the budget is already spent."""
    with _lock:
        state = state if state is not None else load_state(path)
    if state["est_cost_usd"] >= TEST_BUDGET_USD:
        raise GuardrailStop(
            f"GUARDRAIL STOP: estimated test spend "
            f"${state['est_cost_usd']:.4f} has reached the "
            f"${TEST_BUDGET_USD:.2f} test budget. No call sent.")


def estimate(usage):
    usage = usage or {}
    in_tok = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    out_tok = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    return in_tok / 1e6 * RATE_IN_PER_M + out_tok / 1e6 * RATE_OUT_PER_M


def record(kind, model, usage, latency_ms, path=None):
    """Count one completed call. Returns its estimated cost."""
    with _lock:
        state = load_state(path)
        est = estimate(usage)
        state["calls"] += 1
        state["est_cost_usd"] = round(state["est_cost_usd"] + est, 6)
        state["log"].append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "model": model,
            "usage": {
                "input_tokens":
                    (usage or {}).get("prompt_tokens")
                    or (usage or {}).get("input_tokens") or 0,
                "output_tokens":
                    (usage or {}).get("completion_tokens")
                    or (usage or {}).get("output_tokens") or 0,
            },
            "latency_ms": latency_ms,
            "est_cost_usd": round(est, 6),
            "cum_est_cost_usd": state["est_cost_usd"],
        })
        _save_state(state, path or STATE_PATH)
        return est


def status(path=None):
    state = load_state(path)
    return {
        "calls": state["calls"],
        "est_cost_usd": state["est_cost_usd"],
        "test_budget_usd": TEST_BUDGET_USD,
        "remaining_usd": round(TEST_BUDGET_USD - state["est_cost_usd"], 4),
    }
