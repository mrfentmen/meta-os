"""Lab runtime config: model endpoint, per-agent budget caps, cycle action caps.

Hitting a cap stops the run: check_budget() returns (False, reason) and the
caller must stop and file the stop with write_receipt(). Caps are local
policy, not evidence; a stopped run earns no level and files no claim.
"""

import json
import os
from datetime import datetime, timezone

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_config.json")


def load_config(path=DEFAULT_CONFIG_PATH):
    """Load lab config JSON. Returns dict with endpoint/agents/cycle.

    `name` is required and named in the error when absent. Unknown
    top-level keys are ignored (the documented behaviour), and empty
    optional sections receive their documented defaults.
    """
    with open(path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    if not isinstance(cfg, dict):
        raise ValueError("lab config must be a JSON object")
    name = cfg.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("lab config missing required field 'name'")
    cfg["name"] = name.strip()
    cfg.setdefault("endpoint", "file://local - Muse Spark endpoint via helper, key on Mac line1 only")
    cfg.setdefault("agents", {}).setdefault("default", {"maxCalls": 50, "maxSpend": 5.0})
    cfg.setdefault("cycle", {}).setdefault("maxActions", 200)
    return cfg


def _agent_cap(config, agent):
    agents = config.get("agents", {})
    cap = agents.get(agent, agents.get("default", {}))
    return (cap.get("maxCalls"), cap.get("maxSpend"))


def check_budget(config, agent, spend, calls, actions=None):
    """Check caps. Returns (allowed: bool, reason: str).

    spend/calls are this agent's cumulative totals; actions (optional) is
    the cycle-wide action count checked against cycle maxActions.
    Over cap -> (False, reason); caller must stop the run and write_receipt().
    """
    max_calls, max_spend = _agent_cap(config, agent)
    if max_calls is not None and calls > max_calls:
        return (False, "budget-cap-reached: agent %r calls %s > maxCalls %s" % (agent, calls, max_calls))
    if max_spend is not None and spend > max_spend:
        return (False, "budget-cap-reached: agent %r spend %s > maxSpend %s" % (agent, spend, max_spend))
    max_actions = config.get("cycle", {}).get("maxActions")
    if actions is not None and max_actions is not None and actions > max_actions:
        return (False, "budget-cap-reached: cycle actions %s > maxActions %s" % (actions, max_actions))
    return (True, "ok: agent %r within budget (calls %s/%s, spend %s/%s)" % (agent, calls, max_calls, spend, max_spend))


def write_receipt(path, agent, spend, calls, reason, actions=None):
    """Write a budget-stop receipt JSON (cap hits stop the run, with receipt)."""
    receipt = {
        "kind": "budget-receipt",
        "agent": agent,
        "spend": spend,
        "calls": calls,
        "reason": reason,
        "stopped": True,
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if actions is not None:
        receipt["actions"] = actions
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, sort_keys=True, indent=2)
        fh.write("\n")
    return receipt
