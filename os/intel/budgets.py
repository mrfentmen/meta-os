"""intel/budgets.py — per-lane and per-process budget config (OS-085, Milo).

Budgets are config the job queue reads before claiming, and the
watchdog reads before warning: a lane at its warning threshold
gets a budget-warning alert (the warning before the silence,
OS-085's point), and a lane at its cap holds new claims — the
queue refuses them, the job stays open, and the hold is visible
in the brief's budget line (OS-079), not hidden in a log.

A budget entry is the same shape OS-079's brief renderer reads:
a dict with "lane", "spent", and "cap" (or "remaining"). The
queue gate (claim_allowed) and the warning check (at_warning)
are pure functions over those three numbers so the drill, the
watchdog detector, and the queue all answer the same question
from the same figures — no second definition of "at cap"
anywhere. A lane with no usable cap is unbudgeted: claims are
allowed and no warning fires, because an absent budget is not
a zero budget. Malformed entries (non-integer spent or cap,
negative numbers, a missing lane name) are skipped by the
detector and treated as unbudgeted by the gate, never guessed.

The warning threshold is a percentage of cap, env-overridable
through WATCHDOG_BUDGET_WARN_PERCENT (default 80) in the same
style as intel/thresholds.py: an unset, blank, unparseable, or
out-of-range value falls back to the default silently, so a
typo in the environment never crashes the watchdog or invents
a threshold. Per-process caps use the same functions with the
process name as the lane: the shape is identical, only the
subject differs, and the watchdog's budget-warning detector
today watches lanes (the OS-085 acceptance); per-process
warnings ride the same gate when a caller supplies a process
entry.

The live jobs.py claim path does NOT read this module yet:
there is no spend ledger in Redis for it to read from, and a
gate wired to a ledger nobody writes would refuse or allow
claims on stale figures. The drill (intel/drills/budget_gate.py)
proves the gate against a fake queue with the same claim
semantics (claim at cap leaves the job open); wiring the gate
into jobs.py cmd_claim against a real ledger is owed on the
ledger, and is named as NOT proven in the OS-085 eval doc.
"""

import os

__all__ = ["BUDGET_WARN_PERCENT", "spend_ratio", "at_warning",
           "at_cap", "claim_allowed", "budget_state",
           "budgets_from_snapshot", "hold_entry"]


def _env_int(name, default, minimum, maximum):
    """One env-overridable integer, falling back on bad input.

    Mirrors intel/thresholds.py's _env_int: blank, unparseable,
    or out-of-range values return the default rather than
    raising, because a bad environment must never crash the
    watchdog or invent a threshold.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < minimum or value > maximum:
        return default
    return value


# Budget warning threshold (OS-085): warn when a lane has spent
# this percentage of its cap. Env: WATCHDOG_BUDGET_WARN_PERCENT.
# Range 1-100: 0 would warn on the first unit spent, over 100
# would never warn before the cap, and both are nonsense.
BUDGET_WARN_PERCENT = _env_int("WATCHDOG_BUDGET_WARN_PERCENT", 80, 1, 100)


def _usable_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def spend_ratio(spent, cap):
    """Spent as a fraction of cap, or None when unusable.

    Unusable means: spent or cap is not a usable integer, cap
    is zero or negative, or spent is negative. A lane with no
    usable cap has no ratio, and therefore no warning and no
    hold — an absent budget is not a zero budget.
    """
    if not _usable_int(spent) or not _usable_int(cap):
        return None
    if cap <= 0 or spent < 0:
        return None
    return spent / cap


def at_warning(spent, cap, warn_percent=None):
    """True when spent has reached the warning threshold but not cap.

    The warning band is [warn_percent, 100%) of cap: at cap the
    lane is held, not warned — the hold is the louder signal,
    and warning about a lane that is already stopped would
    double-report the same condition. A lane with no usable cap
    is never at warning.
    """
    if warn_percent is None:
        warn_percent = BUDGET_WARN_PERCENT
    ratio = spend_ratio(spent, cap)
    if ratio is None:
        return False
    return ratio >= warn_percent / 100.0 and spent < cap


def at_cap(spent, cap):
    """True when spent has reached or passed cap.

    Overspend counts as at cap: a lane that blew past its cap
    holds claims just as firmly as one that stopped exactly
    at it. A lane with no usable cap is never at cap.
    """
    if spend_ratio(spent, cap) is None:
        return False
    return spent >= cap


def claim_allowed(spent, cap):
    """The queue gate (OS-085): False only when the lane is at cap.

    This is the function the job queue reads before claiming:
    a held lane's jobs stay open for a later, funded run
    instead of being claimed into work the lane cannot pay
    for. Unbudgeted lanes always allow claims.
    """
    return not at_cap(spent, cap)


def budget_state(entry):
    """One of "warning", "capped", "ok", or "unbudgeted" for an entry.

    "warning" is the pre-limit state OS-085 warns about;
    "capped" is the hold state; "ok" is under the warning
    threshold; "unbudgeted" covers missing, malformed, and
    cap-less entries alike — the caller never has to guess
    which absence it was looking at.
    """
    if not isinstance(entry, dict):
        return "unbudgeted"
    spent = entry.get("spent")
    cap = entry.get("cap")
    if at_cap(spent, cap):
        return "capped"
    if at_warning(spent, cap):
        return "warning"
    if spend_ratio(spent, cap) is not None:
        return "ok"
    return "unbudgeted"


def budgets_from_snapshot(snapshot):
    """The budget entries a snapshot carries, as usable dicts.

    The snapshot key is "budgets": a list of OS-079-shaped
    entries (lane, spent, cap). Non-list values, non-dict
    items, and entries without a non-empty lane name are
    skipped, never guessed — a malformed entry must not
    invent a lane or a figure.
    """
    snapshot = snapshot or {}
    budgets = snapshot.get("budgets")
    if not isinstance(budgets, (list, tuple)):
        return []
    entries = []
    for entry in budgets:
        if not isinstance(entry, dict):
            continue
        lane = entry.get("lane")
        if not (isinstance(lane, str) and lane):
            continue
        entries.append(entry)
    return entries


def hold_entry(lane, spent, cap):
    """An OS-079 budgets entry for a lane, with its hold flag set.

    The brief renderer (intel/brief.py memory_budget_lines)
    prints "new claims held" on entries with held True, so the
    hold is visible in the budget line itself — the reader of
    the brief sees the hold where they see the spend, not in
    a separate section they might skip. A lane under cap gets
    held False, so the same builder serves both states.
    """
    return {"lane": lane, "spent": spent, "cap": cap,
            "held": at_cap(spent, cap)}
