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
import re
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.join(BASE_DIR, "records", "repository")

KINDS = ("claims", "experiments", "cycles", "sources")

SCHEMAS_DIR = os.path.join(BASE_DIR, "schemas")
SCHEMA_FILE_NAMES = (
    "cycle.schema.json",
    "experiment.schema.json",
    "hypothesis.schema.json",
    "repository.schema.json",
    "source.schema.json",
)

# The strict typed write path validates the record against the schema that
# owns its shape. Claims and pointers use the repository schema's $defs.
KIND_SCHEMA = {
    "claims": ("repository.schema.json", "#/$defs/claim"),
    "experiments": ("experiment.schema.json", None),
    "cycles": ("cycle.schema.json", None),
    "sources": ("source.schema.json", None),
}

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


def load_schemas():
    """Load every schema file in schemas/. Returns {stem: document}."""
    out = {}
    for name in SCHEMA_FILE_NAMES:
        path = os.path.join(SCHEMAS_DIR, name)
        with open(path, "r", encoding="utf-8") as fh:
            out[name.replace(".schema.json", "")] = json.load(fh)
    return out


def load_schema(name):
    """Load one schema by stem or filename."""
    filename = name if name.endswith(".json") else "%s.schema.json" % name
    path = os.path.join(SCHEMAS_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_ref(root, ref):
    if not str(ref).startswith("#/"):
        raise ValueError("unsupported schema reference %r" % (ref,))
    node = root
    for part in str(ref)[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[part]
    return node


def _type_ok(value, kind):
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    return True


def _validate_node(value, schema, root, path="$"):
    """Validate the JSON-schema subset the five lab schemas use."""
    if not isinstance(schema, dict):
        return []
    if "$ref" in schema:
        return _validate_node(value, _resolve_ref(root, schema["$ref"]),
                              root, path)
    errors = []
    for sub in schema.get("allOf", []):
        errors.extend(_validate_node(value, sub, root, path))
    if "if" in schema and not _validate_node(value, schema["if"], root, path):
        errors.extend(_validate_node(value, schema.get("then", {}), root, path))
    kind = schema.get("type")
    if kind is not None:
        kinds = kind if isinstance(kind, list) else [kind]
        if not any(_type_ok(value, k) for k in kinds):
            errors.append("%s: expected %s, got %s"
                          % (path, "/".join(kinds), type(value).__name__))
            return errors
    if "const" in schema and value != schema["const"]:
        errors.append("%s: %r is not the required constant %r"
                      % (path, value, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r is not one of %r"
                      % (path, value, schema["enum"]))
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append("%s: shorter than minLength %s"
                          % (path, schema["minLength"]))
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append("%s: does not match pattern %r"
                          % (path, schema["pattern"]))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append("%s: below minimum %s" % (path, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errors.append("%s: above maximum %s" % (path, schema["maximum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append("%s: required field %r missing" % (path, key))
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errors.extend(_validate_node(value[key], sub, root,
                                             "%s.%s" % (path, key)))
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors.extend(_validate_node(item, schema["items"], root,
                                         "%s[%d]" % (path, i)))
    return errors


def validate_record(kind, record):
    """Validate a record against its owning schema. Names the failing field."""
    if kind not in KIND_SCHEMA:
        raise ValueError("no schema for repository kind %r" % (kind,))
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    filename, pointer = KIND_SCHEMA[kind]
    root = load_schema(filename)
    schema = _resolve_ref(root, pointer) if pointer else root
    errors = _validate_node(record, schema, root)
    if errors:
        raise ValueError("record for %s fails %s: %s"
                         % (kind, filename, "; ".join(errors)))
    return record


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
    record_id = _entry_id(entry, kind)
    if record_id != "?":
        for existing in _read_all(kind, base):
            if _entry_id(existing, kind) == record_id:
                raise ValueError("duplicate %s id %r refused"
                                 % (kind, record_id))
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


def write_record(kind, record, base=None):
    """Strict typed write: validate against the kind's schema, then file.

    Unlike the pointer helpers above, this path refuses any record that
    fails its schema, and names the failing field in the error.
    """
    validate_record(kind, record)
    return _file(kind, record, base)


def list_records(kind, cycle_id=None, base=None):
    """List one kind in insertion order, optionally filtered by cycle id."""
    rows = _read_all(kind, base)
    if cycle_id is None:
        return rows
    return [row for row in rows
            if str(row.get("cycle_id", row.get("cycle"))) == str(cycle_id)]


def get_record(kind, record_id, base=None):
    """Read one record by id, or raise LookupError."""
    for row in _read_all(kind, base):
        if _entry_id(row, kind) == str(record_id):
            return row
    raise LookupError("no %s record %r in the repository."
                      % (kind, record_id))


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
