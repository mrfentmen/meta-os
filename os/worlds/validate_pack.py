"""worlds/validate_pack.py: world pack manifest validator (WORLDS-001).

A world pack is a definition, not a running system: a PACK.md a
human can read plus a pack.json manifest a machine can check. This
validator checks a manifest against the pack contract in
worlds/README.md and returns a list of error strings; an empty
list means the manifest satisfies the contract. It follows the
repo's validator convention (intel/brief.py
validate_brief_record, intel/store.py validate_alert): pure
function, no I/O in validate_pack itself, errors as strings.

The contract it enforces, in short:

- The manifest names the pack, its version, its status, and its
  institution type. Status is honest: "spec" means definition
  only, nothing here runs a real institution.
- Watchers, agents, alerts, firstboot fields, and urgency classes
  are all present and well formed. Agent "serves" entries must
  reference watcher ids that exist in the same manifest.
- Alert kinds are single tokens in the shared alert language
  (FND-020 shapes, extended not replaced): severity is
  "critical" or "warning", privacy is "local" or "summary".
- Privacy is enforced structurally: an alert may only cross the
  bus (crosses_bus true) when its privacy class is "summary",
  and every cross-world send must declare a non-empty
  never_carries list (what the message must never contain).
- Urgency classes come from the shared set in worlds/README.md
  (life-safety, urgent, routine, digest) with unique ranks, so a
  life-safety message from one world outranks a routine message
  from any other world on the shared bus.

CLI: python3 worlds/validate_pack.py [pack.json ...]
With no arguments it validates every worlds/*/pack.json under
the repo root. Exit code 0 means every manifest passed.
"""

import glob
import json
import os
import re
import sys

TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FIELD_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")

STATUSES = ("spec", "partial", "built")
SEVERITIES = ("critical", "warning")
PRIVACY_CLASSES = ("local", "summary")
URGENCY_CLASSES = ("life-safety", "urgent", "routine", "digest")

REQUIRED_KEYS = (
    "pack", "pack_name", "version", "status", "institution_type",
    "summary", "watchers", "agents", "alerts", "privacy_classes",
    "cross_world", "firstboot", "urgency",
)


def _is_token(value):
    return isinstance(value, str) and bool(TOKEN_RE.match(value))


def _nonempty_str(value):
    return isinstance(value, str) and bool(value.strip())


def validate_pack(manifest):
    """Return a list of contract errors for a pack manifest dict.

    An empty list means the manifest satisfies the pack contract.
    """
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]

    for key in REQUIRED_KEYS:
        if key not in manifest:
            errors.append("missing required key: %s" % key)
    if errors:
        return errors

    if not _is_token(manifest["pack"]):
        errors.append("pack must be a lowercase token: %r"
                      % (manifest["pack"],))
    for key in ("pack_name", "version", "institution_type", "summary"):
        if not _nonempty_str(manifest[key]):
            errors.append("%s must be a non-empty string" % key)
    if manifest["status"] not in STATUSES:
        errors.append("status must be one of %s: %r"
                      % (", ".join(STATUSES), manifest["status"]))

    watcher_ids = set()
    watchers = manifest["watchers"]
    if not isinstance(watchers, list) or not watchers:
        errors.append("watchers must be a non-empty list")
    else:
        for i, watcher in enumerate(watchers):
            where = "watchers[%d]" % i
            if not isinstance(watcher, dict):
                errors.append("%s is not an object" % where)
                continue
            if not _is_token(watcher.get("id")):
                errors.append("%s.id must be a lowercase token" % where)
            elif watcher["id"] in watcher_ids:
                errors.append("duplicate watcher id: %s" % watcher["id"])
            else:
                watcher_ids.add(watcher["id"])
            if not _nonempty_str(watcher.get("watches")):
                errors.append("%s.watches must be a non-empty string"
                              % where)
            inputs = watcher.get("inputs")
            if (not isinstance(inputs, list) or not inputs
                    or not all(_nonempty_str(x) for x in inputs)):
                errors.append("%s.inputs must be a non-empty list of "
                              "strings" % where)

    nicks = set()
    agents = manifest["agents"]
    if not isinstance(agents, list) or not agents:
        errors.append("agents must be a non-empty list")
    else:
        for i, agent in enumerate(agents):
            where = "agents[%d]" % i
            if not isinstance(agent, dict):
                errors.append("%s is not an object" % where)
                continue
            if not _is_token(agent.get("nick")):
                errors.append("%s.nick must be a lowercase token" % where)
            elif agent["nick"] in nicks:
                errors.append("duplicate agent nick: %s" % agent["nick"])
            else:
                nicks.add(agent["nick"])
            if not _nonempty_str(agent.get("role")):
                errors.append("%s.role must be a non-empty string" % where)
            serves = agent.get("serves", [])
            if not isinstance(serves, list):
                errors.append("%s.serves must be a list" % where)
            else:
                for wid in serves:
                    if wid not in watcher_ids:
                        errors.append("%s.serves names unknown watcher: "
                                      "%s" % (where, wid))

    kinds = set()
    alerts = manifest["alerts"]
    if not isinstance(alerts, list) or not alerts:
        errors.append("alerts must be a non-empty list")
    else:
        for i, alert in enumerate(alerts):
            where = "alerts[%d]" % i
            if not isinstance(alert, dict):
                errors.append("%s is not an object" % where)
                continue
            if not _is_token(alert.get("kind")):
                errors.append("%s.kind must be a lowercase token" % where)
            elif alert["kind"] in kinds:
                errors.append("duplicate alert kind: %s" % alert["kind"])
            else:
                kinds.add(alert["kind"])
            if alert.get("severity") not in SEVERITIES:
                errors.append("%s.severity must be one of %s"
                              % (where, ", ".join(SEVERITIES)))
            if alert.get("privacy") not in PRIVACY_CLASSES:
                errors.append("%s.privacy must be one of %s"
                              % (where, ", ".join(PRIVACY_CLASSES)))
            if not isinstance(alert.get("crosses_bus"), bool):
                errors.append("%s.crosses_bus must be a boolean" % where)
            elif alert["crosses_bus"] and alert.get("privacy") != "summary":
                errors.append("%s crosses the bus but its privacy is not "
                              "'summary'; only summaries may cross"
                              % where)
            if not _nonempty_str(alert.get("carries")):
                errors.append("%s.carries must be a non-empty string"
                              % where)
            if alert.get("urgency") not in URGENCY_CLASSES:
                errors.append("%s.urgency must be one of %s"
                              % (where, ", ".join(URGENCY_CLASSES)))

    classes = manifest["privacy_classes"]
    if not isinstance(classes, dict):
        errors.append("privacy_classes must be an object")
    else:
        for key in ("local_only", "bus_summary"):
            value = classes.get(key)
            if (not isinstance(value, list) or not value
                    or not all(_nonempty_str(x) for x in value)):
                errors.append("privacy_classes.%s must be a non-empty "
                              "list of strings" % key)

    cross = manifest["cross_world"]
    if not isinstance(cross, dict):
        errors.append("cross_world must be an object")
    else:
        for key in ("sends", "receives"):
            if not isinstance(cross.get(key), list):
                errors.append("cross_world.%s must be a list" % key)
        for i, send in enumerate(cross.get("sends") or []):
            where = "cross_world.sends[%d]" % i
            if not isinstance(send, dict):
                errors.append("%s is not an object" % where)
                continue
            if not _is_token(send.get("to")):
                errors.append("%s.to must be a lowercase token" % where)
            if not _is_token(send.get("kind")):
                errors.append("%s.kind must be a lowercase token" % where)
            if not _nonempty_str(send.get("carries")):
                errors.append("%s.carries must be a non-empty string"
                              % where)
            never = send.get("never_carries")
            if (not isinstance(never, list) or not never
                    or not all(_nonempty_str(x) for x in never)):
                errors.append("%s.never_carries must be a non-empty list "
                              "of strings; a message that may cross the "
                              "bus must say what it never carries" % where)
        for i, recv in enumerate(cross.get("receives") or []):
            where = "cross_world.receives[%d]" % i
            if not isinstance(recv, dict):
                errors.append("%s is not an object" % where)
                continue
            if not _is_token(recv.get("from")):
                errors.append("%s.from must be a lowercase token" % where)
            if not _is_token(recv.get("kind")):
                errors.append("%s.kind must be a lowercase token" % where)
            if not _nonempty_str(recv.get("carries")):
                errors.append("%s.carries must be a non-empty string"
                              % where)

    fields = set()
    firstboot = manifest["firstboot"]
    if not isinstance(firstboot, list) or not firstboot:
        errors.append("firstboot must be a non-empty list")
    else:
        for i, entry in enumerate(firstboot):
            where = "firstboot[%d]" % i
            if not isinstance(entry, dict):
                errors.append("%s is not an object" % where)
                continue
            field = entry.get("field")
            if not (isinstance(field, str) and FIELD_RE.match(field)):
                errors.append("%s.field must be a lowercase field name"
                              % where)
            elif field in fields:
                errors.append("duplicate firstboot field: %s" % field)
            else:
                fields.add(field)
            if not _nonempty_str(entry.get("label")):
                errors.append("%s.label must be a non-empty string"
                              % where)
            if not isinstance(entry.get("required"), bool):
                errors.append("%s.required must be a boolean" % where)

    seen_classes = set()
    seen_ranks = set()
    urgency = manifest["urgency"]
    if not isinstance(urgency, list) or not urgency:
        errors.append("urgency must be a non-empty list")
    else:
        for i, entry in enumerate(urgency):
            where = "urgency[%d]" % i
            if not isinstance(entry, dict):
                errors.append("%s is not an object" % where)
                continue
            if entry.get("class") not in URGENCY_CLASSES:
                errors.append("%s.class must be one of %s"
                              % (where, ", ".join(URGENCY_CLASSES)))
            elif entry["class"] in seen_classes:
                errors.append("duplicate urgency class: %s"
                              % entry["class"])
            else:
                seen_classes.add(entry["class"])
            rank = entry.get("rank")
            if not isinstance(rank, int) or isinstance(rank, bool) \
                    or rank < 1:
                errors.append("%s.rank must be a positive integer"
                              % where)
            elif rank in seen_ranks:
                errors.append("duplicate urgency rank: %s" % rank)
            else:
                seen_ranks.add(rank)
            if not _nonempty_str(entry.get("meaning")):
                errors.append("%s.meaning must be a non-empty string"
                              % where)

    return errors


def validate_pack_at(path):
    """Load the pack.json at path; return (manifest, errors)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        return None, ["%s: cannot load manifest: %s" % (path, exc)]
    errors = validate_pack(manifest)
    if isinstance(manifest, dict):
        dirname = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if manifest.get("pack") != dirname:
            errors.append("pack name %r does not match its directory %r"
                          % (manifest.get("pack"), dirname))
    return manifest, errors


def _default_paths():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return sorted(glob.glob(os.path.join(root, "worlds", "*", "pack.json")))


def main(argv):
    paths = argv[1:] or _default_paths()
    if not paths:
        print("no pack manifests found")
        return 1
    failed = 0
    for path in paths:
        _, errors = validate_pack_at(path)
        if errors:
            failed += 1
            print("%s: FAIL" % path)
            for err in errors:
                print("  - %s" % err)
        else:
            print("%s: OK" % path)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
