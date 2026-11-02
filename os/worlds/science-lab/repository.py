"""Knowledge Repository (Section 6, tasks 57-58). stdlib only.

Filed claims, experiments, cycles and sources, queryable by level,
department, agent and date. Only verifier-agreed results enter as
confirmed; everything else enters as unconfirmed with its capped
level (see verify.gate_write).

Storage: records/repository/<kind>.jsonl, one JSON object per line.
Kinds: claims, experiments, cycles, sources.
"""

import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.join(BASE_DIR, "records", "repository")

KINDS = ("claims", "experiments", "cycles", "sources")

_LEVEL_KEYS = ("level", "evidence_level", "evidenceLevel")
_DEPT_KEYS = ("department", "dept")
_AGENT_KEYS = ("agent", "produced_by", "producer", "filed_by", "created_by",
               "recorded_by", "verified_by", "verifier")
_DATE_KEYS = ("recorded_at", "date", "filed_at", "compared_at", "created_at")


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _root(base=None):
    return base or DEFAULT_ROOT


def _path(kind, base=None):
    if kind not in KINDS:
        raise ValueError("unknown repository kind %r (known: %s)."
                         % (kind, list(KINDS)))
    root = _root(base)
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "%s.jsonl" % kind)


def _read_all(kind, base=None):
    path = _path(kind, base)
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _entry_id(entry, kind):
    for key in ("claim_id", "experiment_id", "cycle_id", "source_id", "id",
                "dispute_id"):
        if entry.get(key) is not None:
            return str(entry[key])
    return "?"


def _file(kind, entry, base=None):
    """Append one entry to a kind file. Returns the filed copy."""
    if not isinstance(entry, dict):
        raise ValueError("repository entries must be dicts.")
    filed = dict(entry)
    filed.setdefault("recorded_at", _utcnow())
    if "date" not in filed:
        filed["date"] = filed["recorded_at"][:10]
    path = _path(kind, base)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(filed, sort_keys=True) + "\n")
    return filed


def file_claim(claim, base=None):
    """File a claim. Requires claim_id, statement, level 0-6."""
    if not isinstance(claim, dict):
        raise ValueError("claim must be a dict.")
    for key in ("claim_id", "statement", "level"):
        if claim.get(key) is None:
            raise ValueError("claim requires %r." % (key,))
    level = claim["level"]
    if isinstance(level, bool) or not isinstance(level, int) or level not in range(7):
        raise ValueError("claim level must be an int 0-6, got %r." % (level,))
    return _file("claims", claim, base)


def file_experiment(experiment, base=None):
    """File an experiment pointer. Requires experiment_id and level 0-3."""
    if not isinstance(experiment, dict):
        raise ValueError("experiment must be a dict.")
    for key in ("experiment_id", "level"):
        if experiment.get(key) is None:
            raise ValueError("experiment requires %r." % (key,))
    level = experiment["level"]
    if isinstance(level, bool) or not isinstance(level, int) or level not in range(4):
        raise ValueError("experiment level must be an int 0-3, got %r."
                         % (level,))
    return _file("experiments", experiment, base)


def file_cycle(cycle, base=None):
    """File a cycle pointer. Requires cycle_id."""
    if not isinstance(cycle, dict) or not cycle.get("cycle_id"):
        raise ValueError("cycle requires a cycle_id.")
    return _file("cycles", cycle, base)


def file_source(source, base=None):
    """File a source pointer. Requires source_id."""
    if not isinstance(source, dict) or not source.get("source_id"):
        raise ValueError("source requires a source_id.")
    return _file("sources", source, base)


def _field(entry, keys):
    for key in keys:
        if entry.get(key) is not None:
            return entry[key]
    return None


def _matches(entry, level=None, department=None, agent=None,
             date_from=None, date_to=None):
    if level is not None:
        got = _field(entry, _LEVEL_KEYS)
        try:
            if int(got) != int(level):
                return False
        except (TypeError, ValueError):
            return False
    if department is not None:
        got = _field(entry, _DEPT_KEYS)
        if got is None or str(got).strip().lower() != str(department).strip().lower():
            return False
    if agent is not None:
        want = str(agent).strip()
        agents = {str(entry[k]).strip() for k in _AGENT_KEYS
                  if entry.get(k) is not None and str(entry[k]).strip()}
        if want not in agents:
            return False
    day = str(_field(entry, _DATE_KEYS) or "")[:10]
    if date_from is not None and day < str(date_from)[:10]:
        return False
    if date_to is not None and day > str(date_to)[:10]:
        return False
    return True


def query(kind="claims", level=None, department=None, agent=None,
          date_from=None, date_to=None, base=None):
    """Query one repository kind by level/department/agent/date range.

    kind is one of claims/experiments/cycles/sources (default claims).
    Filters left as None are not applied. Returns a list of entries.
    """
    return [e for e in _read_all(kind, base)
            if _matches(e, level, department, agent, date_from, date_to)]


def query_by_level(level, kind="claims", base=None):
    """Convenience: all entries of one kind at one evidence level."""
    return query(kind=kind, level=level, base=base)


def show_claim(claim_id, base=None):
    """Return one filed claim by id, or raise LookupError."""
    for entry in _read_all("claims", base):
        if str(entry.get("claim_id", entry.get("id"))) == str(claim_id):
            return entry
    raise LookupError("no claim %r in the repository." % (claim_id,))


def provenance(claim_id, base=None):
    """Walk a claim's full provenance chain back to sources.

    Follows claim -> experiment_ids -> filed experiments, claim ->
    source_ids -> filed sources, and claim -> cycle_id -> filed cycle.
    Missing links are reported in "gaps", never invented.
    Returns {"claim": ..., "experiments": [...], "sources": [...],
             "cycles": [...], "gaps": [...]}.
    """
    claim = show_claim(claim_id, base)
    experiments = _read_all("experiments", base)
    sources = _read_all("sources", base)
    cycles = _read_all("cycles", base)

    def _by_id(entries, id_keys, want):
        for e in entries:
            for k in id_keys:
                if e.get(k) is not None and str(e[k]) == str(want):
                    return e
        return None

    found_experiments, gaps = [], []
    exp_ids = claim.get("experiment_ids") or (
        [claim["experiment_id"]] if claim.get("experiment_id") else [])
    for eid in exp_ids:
        hit = _by_id(experiments, ("experiment_id", "id"), eid)
        if hit is None:
            gaps.append("experiment %r linked but not filed" % (eid,))
        else:
            found_experiments.append(hit)

    found_sources = []
    for sid in claim.get("source_ids") or []:
        hit = _by_id(sources, ("source_id", "id"), sid)
        if hit is None:
            gaps.append("source %r linked but not filed" % (sid,))
        else:
            found_sources.append(hit)

    found_cycles = []
    if claim.get("cycle_id") is not None:
        hit = _by_id(cycles, ("cycle_id", "id"), claim["cycle_id"])
        if hit is None:
            gaps.append("cycle %r linked but not filed" % (claim["cycle_id"],))
        else:
            found_cycles.append(hit)

    return {
        "claim": claim,
        "experiments": found_experiments,
        "sources": found_sources,
        "cycles": found_cycles,
        "gaps": gaps,
    }


__all__ = [
    "KINDS",
    "file_claim",
    "file_experiment",
    "file_cycle",
    "file_source",
    "query",
    "query_by_level",
    "show_claim",
    "provenance",
]
