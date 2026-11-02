"""Validator for Hortus generation records.

records.py enforces these invariants on WRITE, against the whole log
(duplicate child ids across the file, children counted once). This
module checks ONE record, as read back in isolation, and returns named
errors instead of raising -- a log audit wants every bad line listed,
not only the first one.

Record shape (records.write_generation):

    {"kind": "generation-record", "generation": 3,
     "parent_ids": ["o1", "o2"], "child_ids": ["o3", "o4"]}

Optional `child_parents` map: {child_id: [parent_id, ...]}. A record
that carries it must point every child at parents listed in
parent_ids; that is how a bad lineage link gets reported by name.

Zero dependencies: stdlib only.
"""

ALLOWED_KEYS = ("kind", "generation", "parent_ids", "child_ids",
                "child_parents")
KIND = "generation-record"


def _is_id(value):
    return isinstance(value, str) and value.strip() != ""


def _validate_ids(path, ids, errors):
    if not isinstance(ids, list):
        errors.append(path + ": must be a list")
        return False
    if not ids:
        errors.append(path + ": must not be empty")
    seen = set()
    for i, value in enumerate(ids):
        if not _is_id(value):
            errors.append(path + "[" + str(i) + "]: must be a non-empty string")
            continue
        if value in seen:
            errors.append(path + "[" + str(i) + "]: duplicate id " + value)
        seen.add(value)
    return True


def validate_generation_record(record):
    """Return named errors for one generation record; [] when valid."""
    if not isinstance(record, dict):
        return ["record: must be an object"]
    errors = []
    for key in record:
        if key not in ALLOWED_KEYS:
            errors.append("unexpected field: " + key)
    if "kind" not in record:
        errors.append("kind: missing")
    elif record["kind"] != KIND:
        errors.append("kind: must be " + KIND)
    if "generation" not in record:
        errors.append("generation: missing")
    else:
        generation = record["generation"]
        if isinstance(generation, bool) or not isinstance(generation, int):
            errors.append("generation: must be an integer")
        elif generation < 0:
            errors.append("generation: must be >= 0")

    parents_ok = False
    children_ok = False
    if "parent_ids" not in record:
        errors.append("parent_ids: missing")
    else:
        parents_ok = _validate_ids("parent_ids", record["parent_ids"], errors)
    if "child_ids" not in record:
        errors.append("child_ids: missing")
    else:
        children_ok = _validate_ids("child_ids", record["child_ids"], errors)

    if parents_ok and children_ok:
        overlap = sorted(set(record["parent_ids"]) & set(record["child_ids"]))
        if overlap:
            errors.append(
                "child_ids: an organism cannot be its own parent: "
                + ", ".join(overlap))

    if "child_parents" in record:
        links = record["child_parents"]
        if not isinstance(links, dict):
            errors.append("child_parents: must be an object")
        else:
            known_parents = set(record.get("parent_ids") or [])
            known_children = set(record.get("child_ids") or [])
            for child, parent_ids in links.items():
                path = "child_parents." + str(child)
                if child not in known_children:
                    errors.append(path + ": child is not in child_ids")
                if not isinstance(parent_ids, list) or not parent_ids:
                    errors.append(path + ": must be a non-empty list")
                    continue
                for i, parent in enumerate(parent_ids):
                    if not _is_id(parent):
                        errors.append(
                            path + "[" + str(i) + "]: must be a non-empty string")
                    elif parent not in known_parents:
                        errors.append(
                            path + "[" + str(i) + "]: unknown parent " + parent)
    return errors
