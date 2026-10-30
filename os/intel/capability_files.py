"""intel/capability_files.py -- capability files (OS-080, Pax).

Every crew and driver process runs as a named identity with an
explicit capability file. This module is the file half of that
rule: it loads and validates the files, and it is the loader a
process launcher calls at process start. It is judgment-adjacent,
not judgment: it never decides whether an action is allowed.
That decision stays in intel/capability.py (OS-081), which takes
exactly the grant dict this module produces.

File format: one JSON object per identity, named
<identity>.json, with exactly these keys:

    {"identity": "milo",
     "bus_post": False, "spend": False, "network": True,
     "write_paths": ["crew/milo/"]}

The three flags must be real JSON booleans, not 0/1 or strings,
so a typo like "bus_posts" or a 1 where True belongs fails the
file instead of silently changing the grant. write_paths entries
are relative prefixes matched on whole path segments by
capability.check_action, so "crew/milo/" never authorizes
"crew/milo2/x". A path that is absolute, empty, or escapes its
root with ".." is rejected here, before any judgment runs.

Rules, stated plainly because each one guards a silent
privilege failure:

- A missing file is not a grant. load_grant_for returns None,
  and capability.check_action refuses every action for a
  process with no grant. Default is deny.
- A present but invalid file is never treated as no grant.
  load_grant_for raises ValueError, so a launcher that calls
  it at process start fails the launch instead of starting
  an ungranted process. A corrupt grant file must block the
  process, not quietly ungrant it.
- A file whose identity disagrees with its filename is an
  error in load_crew_grants, never silently filed under the
  wrong identity.
- Returned grants are fresh copies. Mutating a returned
  dict never changes a later load, and loading never
  mutates its inputs.

This is NOT the mind-image bundle grant. A bundle's
grants.json (intel/mind_image.py layer 4) names an identity
plus an actions list for the bundle; these OS-080 files name
an identity plus the bus_post/spend/network/write_paths
policy that capability.check_action judges. The two layers
answer different questions and share only the identity name.

Shipped crew files live in intel/capabilities/, one per crew
nick. Their flags are PROVISIONAL: network is on because a
crew process must reach the bus and queue over the network to
work at all, while bus_post and spend stay off under Dale's
standing rules (no bus post without his word, no spend
without approval), and writes stay inside crew/<nick>/. The
shipped defaults are not Dale-approved policy; OS-082 owns
that approval, and until it lands these files are the
conservative starting point, not the final policy.
"""

import json
import os
import re

__all__ = ["GRANT_KEYS", "FLAG_KEYS", "validate_grant", "load_grant",
           "load_grant_for", "load_crew_grants", "shipped_directory"]

GRANT_KEYS = ("identity", "bus_post", "spend", "network", "write_paths")
FLAG_KEYS = ("bus_post", "spend", "network")

_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def shipped_directory():
    """Absolute path of the shipped crew capability files."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "capabilities")


def _path_escapes(path):
    """True when a write path is absolute, empty, or escapes root."""
    if not isinstance(path, str) or not path:
        return True
    if path.startswith("/"):
        return True
    depth = 0
    segments = 0
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if depth == 0:
                return True
            depth -= 1
            continue
        depth += 1
        segments += 1
    return segments == 0


def validate_grant(data, source="<grant>"):
    """Validate one parsed grant object, return a fresh grant dict.

    Raises ValueError naming the source and the exact problem.
    Unknown or missing keys fail: a grant file must carry
    exactly GRANT_KEYS, so a misspelled flag can never pass
    as a narrower grant.
    """
    if not isinstance(data, dict):
        raise ValueError("%s: grant must be a JSON object" % source)
    keys = set(data)
    expected = set(GRANT_KEYS)
    if keys != expected:
        missing = sorted(expected - keys)
        unknown = sorted(keys - expected)
        parts = []
        if missing:
            parts.append("missing keys: " + ", ".join(missing))
        if unknown:
            parts.append("unknown keys: " + ", ".join(unknown))
        raise ValueError("%s: %s" % (source, "; ".join(parts)))
    identity = data["identity"]
    if not isinstance(identity, str) or not identity:
        raise ValueError("%s: 'identity' must be a non-empty string"
                         % source)
    for flag in FLAG_KEYS:
        if type(data[flag]) is not bool:
            raise ValueError("%s: '%s' must be a JSON boolean"
                             % (source, flag))
    paths = data["write_paths"]
    if not isinstance(paths, list):
        raise ValueError("%s: 'write_paths' must be a list" % source)
    for entry in paths:
        if not isinstance(entry, str) or _path_escapes(entry):
            raise ValueError(
                "%s: write path %r is not a relative path inside "
                "its root" % (source, entry))
    return {"identity": identity,
            "bus_post": data["bus_post"],
            "spend": data["spend"],
            "network": data["network"],
            "write_paths": list(paths)}


def load_grant(path):
    """Load and validate the grant file at path.

    Raises FileNotFoundError when the file is absent and
    ValueError naming the file for bad JSON or a bad grant.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError("%s: not valid JSON: %s" % (path, exc))
    except UnicodeDecodeError as exc:
        raise ValueError("%s: not valid UTF-8: %s" % (path, exc))
    return validate_grant(data, source=path)


def load_grant_for(identity, directory):
    """Load the grant for one identity, or None when no file exists.

    The identity must be a plain filename stem (letters,
    digits, underscore, hyphen); anything else raises
    ValueError instead of letting an identity walk the
    filesystem. A present but invalid file raises
    ValueError: fail the launch, never run ungranted.
    """
    if not isinstance(identity, str) or not _IDENTITY_RE.match(identity):
        raise ValueError("identity %r is not a plain filename stem"
                         % (identity,))
    path = os.path.join(directory, identity + ".json")
    if not os.path.exists(path):
        return None
    return load_grant(path)


def load_crew_grants(directory):
    """Load every <identity>.json in a directory.

    Returns (grants, errors): grants maps identity to its
    validated grant dict, errors is a list of {"file", "reason"}
    for every file skipped. A file is skipped when it fails
    validation or when its identity disagrees with its
    filename. Nothing in this call raises for a bad file; a
    missing directory still raises FileNotFoundError from
    listdir, because that is a caller error, not a bad grant.
    """
    grants = {}
    errors = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        stem = name[:-len(".json")]
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        try:
            grant = load_grant(path)
        except ValueError as exc:
            errors.append({"file": name, "reason": str(exc)})
            continue
        if grant["identity"] != stem:
            errors.append({"file": name,
                           "reason": "%s: identity %r does not match "
                           "filename %r" % (path, grant["identity"],
                                            stem)})
            continue
        grants[stem] = grant
    return grants, errors
