"""DSH-037: static payload dev pack for the dashboard lane.

Rowan builds the intel panels against checked-in example JSON, not
against a live room. The JSON lives in intel/devpack/ next to this
module; this module holds only the pure shaping functions that turn
real producer output into panel payloads, plus a loader for the
checked-in files:

- brief_entry(record, as_of): a brief record (intel/brief.py) plus
  the age_seconds the reader computes at read time (BRF-020).
  Record fields are copied verbatim; nothing is reworded.
- plan_preview(plan, order): a validated plan (intel/dispatch.py)
  reduced to the DSP-037 preview shape: summary, jobs in plan
  order, the topological posting order, and attempt budgets.
- alerts_feed(records): alert records (intel/store.py) newest
  first, the DSH-013 feed order.
- crew_board(presence, caps, jobs): the three DSH-003 sources
  exactly as the viewer reads them: presence nicks, capability
  records, and jobs.py list --json rows. The panel derives its
  rows from these sources; the pack does not invent a row shape.

No network, no Redis, no bus post, no Spark call anywhere in
this module: the producers run in the test (tests/
test_intel_devpack.py), which rebuilds every payload from real
code on fixtures and asserts it equals the checked-in JSON. If
that test fails on equality, the checked-in pack is stale: fix
the producers or regenerate the JSON, never hand-edit a payload
to match a panel. Regeneration is the test file run as a script:
python3 tests/test_intel_devpack.py --dump intel/devpack
"""

import json
import os

PACK_FILES = {
    "brief": "brief.json",
    "plan_preview": "plan_preview.json",
    "alerts": "alerts.json",
    "crew_board": "crew_board.json",
}

__all__ = ["brief_entry", "plan_preview", "alerts_feed",
           "crew_board", "load_pack", "PACK_FILES"]


def _copy(value):
    return json.loads(json.dumps(value))


def brief_entry(record, as_of):
    """A brief record plus its read-time age (BRF-020).

    record is a generate_brief record; as_of is epoch seconds.
    Raises ValueError when either timestamp is not an int, so a
    pack entry can never carry a guessed age.
    """
    if not isinstance(record, dict):
        raise ValueError("brief record must be a dict")
    generated_at = record.get("generated_at")
    if (isinstance(generated_at, bool)
            or not isinstance(generated_at, int)):
        raise ValueError("brief record needs an int generated_at")
    if isinstance(as_of, bool) or not isinstance(as_of, int):
        raise ValueError("as_of must be an int epoch timestamp")
    entry = _copy(record)
    entry["as_of"] = as_of
    entry["age_seconds"] = as_of - generated_at
    return entry


def plan_preview(plan, order):
    """A validated plan in the DSP-037 preview shape.

    order is the topological posting order (check_dep_graph).
    Raises ValueError when the order does not cover exactly the
    plan's jobs, mirroring the poster's own check.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"), list):
        raise ValueError("plan must be a validated plan dict")
    jobs = plan["jobs"]
    keys = [job.get("key") for job in jobs]
    if sorted(order) != sorted(keys):
        raise ValueError("posting order must cover exactly the plan jobs")
    by_key = {job["key"]: job for job in jobs}
    preview_jobs = [{
        "key": job["key"],
        "title": job["title"],
        "files": list(job["files"]),
        "deps": list(job["deps"]),
        "max_attempts": job["max_attempts"],
        "accept": list(job["accept"]),
        "req": list(job.get("req", [])),
    } for job in jobs]
    return {
        "summary": plan["summary"],
        "jobs": preview_jobs,
        "posting_order": [by_key[key]["key"] for key in order],
        "budgets": {
            "jobs": len(jobs),
            "max_attempts_total": sum(
                job["max_attempts"] for job in jobs),
        },
    }


def alerts_feed(records):
    """Alert records newest first (DSH-013 feed order).

    Ties break on id so the order is stable across runs.
    """
    ordered = sorted(_copy(records),
                     key=lambda r: (r.get("created_at", 0),
                                    r.get("id", "")),
                     reverse=True)
    return ordered


def crew_board(presence, caps, jobs):
    """The three DSH-003 sources, exactly as the viewer reads them."""
    return {
        "presence": list(presence),
        "caps": _copy(caps),
        "jobs": _copy(jobs),
    }


def load_pack(directory=None):
    """Load the checked-in pack; returns {brief, plan_preview,
    alerts, crew_board} with each file's parsed JSON."""
    base = directory or os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "devpack")
    pack = {}
    for name, filename in PACK_FILES.items():
        with open(os.path.join(base, filename)) as fh:
            pack[name] = json.load(fh)
    return pack
