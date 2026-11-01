"""musica loop budget guard (HN-051).

The composition loop honours a daily Spark spend cap from config.
Cap hit = logged stop, not an error: the session ends gracefully
with a budget_stop marker in session.json, exit code 0, and the
takes already logged stay logged.

Config (JSON): {"daily_cap_usd": 5.0}. Spend ledger (JSON list):
[{"date": "2026-11-01", "usd": 0.50, "take_id": "..."}]. Only
"sent" assist calls add spend; in this sandbox nothing is ever
sent, so spend stays 0 and the guard never trips in production
runs -- it is proven by test with a staged ledger, not by
pretending a real call happened.

This is the loop's own guard inside the shared $75 test budget
(server/budget.mjs); it does not replace that guardrail.
"""

import datetime
import json
import os


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        config = json.load(fh)
    cap = config.get("daily_cap_usd")
    if not isinstance(cap, (int, float)) or cap < 0:
        raise ValueError("daily_cap_usd must be a number >= 0")
    return {"daily_cap_usd": float(cap)}


def today_spend(ledger_path, today=None):
    """Sum today's spend from the ledger (0 when no ledger exists)."""
    if today is None:
        today = datetime.date.today().isoformat()
    if not os.path.exists(ledger_path):
        return 0.0
    with open(ledger_path, encoding="utf-8") as fh:
        entries = json.load(fh)
    return round(sum(e.get("usd", 0) for e in entries
                     if e.get("date") == today), 4)


def budget_allows(config, spend):
    """True when another assist call may proceed; False = stop."""
    return spend < config["daily_cap_usd"]


def record_stop(session_dir, cap, spend):
    """Write the budget_stop marker to session.json. Returns it."""
    session_path = os.path.join(session_dir, "session.json")
    session = {}
    if os.path.exists(session_path):
        with open(session_path, encoding="utf-8") as fh:
            session = json.load(fh)
    stop = {
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "daily_cap_usd": cap,
        "spend_usd": spend,
        "reason": "daily Spark spend cap reached; session stopped, not failed",
    }
    session["budget_stop"] = stop
    with open(session_path, "w", encoding="utf-8") as fh:
        json.dump(session, fh, indent=2, sort_keys=True)
    return stop
