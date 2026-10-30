"""intel/capability.py -- capability refusal enforcement (OS-081, Milo).

A process that attempts an action outside its grant is refused,
the refusal is written as an alert record with a plain-English
explanation, and the watchdog surfaces it like any other alert
(DEMO.md Shot 8b evidence).

The grant shape is a plain dict, loaded by the caller from the
process's capability file; this module reads no file and holds
no secret, because the capability files themselves are OS-080
(Pax, not landed yet). Until OS-080 lands, the caller supplies
the grant dict in exactly the shape OS-080 specifies:

    {"identity": "milo",
     "bus_post": False, "spend": False, "network": False,
     "write_paths": ["crew/milo/"]}

The four actions are the four OS-080 grant fields: bus_post
(post to the bus), spend (spend money or API budget), network
(reach the network), and write_file (write a file, whose
subject is the path). A write is allowed only when the path
stays inside one of the grant's write_paths, matched on whole
path segments, so "crew/milo/" never authorizes "crew/milo2/x".

The division of labor is exact, and it matches the trust,
ladder, and gate modules before it. This module is the
judgment, not the hands: it never performs the attempted
action, never moves a claim, never writes a job record,
never posts to the bus, and has no push path, so a refusal
judged here can never ring a phone on its own. The OS layer
refuses from the decision; the watchman surfaces the journal
record on the board and in the brief, and the caller persists
the alert record through intel.store.write_alert, which is
where the record gains its id, status, and lifecycle.

Decision rules, in the order they are checked:

1. An attempt that is not a dict, or an action that is not a
   known action name, yields no decision: there is nothing
   to judge, and an unknown action is never silently
   allowed by a later rule.
2. A process with no grant dict, or a grant with no
   identity, is refused, reason "no capability grant on
   file". Default is deny: a process OS-080 has not
   described yet gets nothing, not everything.
3. A known action whose grant flag is not exactly True is
   refused, reason "capability not granted". The missing
   capability named is the action itself.
4. A write_file with no path is refused, reason "no file
   path given". A write whose path escapes its grant
   prefixes, or whose grant names no write paths, is
   refused, reason "write path outside grant". The
   missing capability named is "write:<path>", so the
   explanation names the exact path that was refused.
5. Everything else is allowed, and an allowed attempt
   journals nothing: capability silence is the normal
   case, not a record.
"""

from . import explanations as _explanations

__all__ = ["ACTIONS", "check_action", "refusal_alert",
           "refusal_note", "capability_tick", "brief_lines"]

ACTIONS = ("bus_post", "spend", "network", "write_file")


def _normalize_path(path):
    """Lexically normalize a relative path, or None if it escapes.

    Dot segments drop out, dot-dot segments pop the last
    segment, and a dot-dot with nothing left to pop means
    the path escapes its root and is refused outright.
    Absolute paths are treated as escaping too: a grant
    prefix is relative, so an absolute subject never
    matches one.
    """
    if not isinstance(path, str) or not path:
        return None
    if path.startswith("/"):
        return None
    parts = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(segment)
    if not parts:
        return None
    return "/".join(parts)


def _prefix_segments(prefix):
    normalized = _normalize_path(prefix)
    if normalized is None:
        return None
    return normalized.split("/")


def _path_inside(path, prefix):
    """True when path sits inside prefix, on whole segments."""
    path_parts = _normalize_path(path)
    prefix_parts = _prefix_segments(prefix)
    if path_parts is None or prefix_parts is None:
        return False
    parts = path_parts.split("/")
    return parts[:len(prefix_parts)] == prefix_parts


def _refused(identity, action, subject, missing, reason):
    return {"allowed": False, "identity": identity,
            "action": action, "subject": subject,
            "missing_capability": missing, "reason": reason}


def check_action(grant, action, subject=None, identity=None):
    """Judge one attempted action against one grant dict.

    Returns a decision dict: allowed True with reason and
    missing_capability None, or allowed False naming the
    missing capability and the reason. Returns None for an
    attempt with no action name to judge. Never mutates
    its inputs, never performs the action. The identity
    is the grant's when the grant names one; otherwise
    the caller's identity argument (the process the OS
    layer saw attempting) stands, so a refusal always
    names a process instead of an empty string.
    """
    if not isinstance(action, str) or not action:
        return None
    resolved = ""
    if isinstance(grant, dict):
        raw_identity = grant.get("identity")
        if isinstance(raw_identity, str):
            resolved = raw_identity
    if not resolved and isinstance(identity, str):
        resolved = identity
    identity = resolved
    if action not in ACTIONS:
        return _refused(identity, action, subject, action,
                        "unknown action")
    if not isinstance(grant, dict) or not identity:
        if action == "write_file" and isinstance(subject, str) \
                and subject:
            missing = "write:" + subject
        else:
            missing = action
        return _refused(identity, action, subject, missing,
                        "no capability grant on file")
    if action == "write_file":
        if not isinstance(subject, str) or not subject:
            return _refused(identity, action, subject,
                            "write_file", "no file path given")
        normalized = _normalize_path(subject)
        if normalized is None:
            return _refused(identity, action, subject,
                            "write:" + subject,
                            "write path outside grant")
        paths = grant.get("write_paths")
        if isinstance(paths, list):
            for prefix in paths:
                if _path_inside(normalized, prefix):
                    return {"allowed": True, "identity": identity,
                            "action": action, "subject": subject,
                            "missing_capability": None,
                            "reason": None}
        return _refused(identity, action, subject,
                        "write:" + normalized,
                        "write path outside grant")
    if grant.get(action) is True:
        return {"allowed": True, "identity": identity,
                "action": action, "subject": subject,
                "missing_capability": None, "reason": None}
    return _refused(identity, action, subject, action,
                    "capability not granted")


def refusal_alert(decision, now=None):
    """Build the alert dict for a refused decision.

    Kind "capability-refusal", severity warning, dedupe
    "capability-refusal:<identity>:<action>:<subject>".
    The explanation names the identity, the action, and
    the missing capability, rendered through the WDG-011
    template so the wording lives in exactly one place.
    Returns None for an allowed decision or no decision.
    The caller persists it via intel.store.write_alert.
    """
    if not isinstance(decision, dict) or decision.get("allowed"):
        return None
    identity = decision.get("identity") or ""
    action = decision.get("action") or ""
    capability = decision.get("missing_capability") or action
    subject = decision.get("subject")
    if not isinstance(subject, str) or not subject:
        subject = "-"
    explanation, fix = _explanations.render(
        "capability-refusal", identity=identity, action=action,
        capability=capability)
    return {"kind": "capability-refusal", "severity": "warning",
            "dedupe_key": "capability-refusal:" + identity
            + ":" + action + ":" + subject,
            "nick": identity, "explanation": explanation,
            "suggested_fix": fix, "created_at": now}


def refusal_note(decision):
    """The exact text the OS layer records on refusal.

    Names the identity, the action, the missing
    capability, and the reason. Returns None for an
    allowed decision or no decision.
    """
    if not isinstance(decision, dict) or decision.get("allowed"):
        return None
    return ("Refused: " + str(decision.get("identity"))
            + " attempted " + str(decision.get("action"))
            + "; missing capability "
            + str(decision.get("missing_capability"))
            + " (" + str(decision.get("reason")) + ").")


def _already_journaled(journal, dedupe_key):
    for record in journal or []:
        if isinstance(record, dict) \
                and record.get("dedupe_key") == dedupe_key:
            return True
    return False


def capability_tick(attempts, grants, journal, now):
    """Journal one refusal record per refused attempt.

    attempts: [{"identity", "action", "subject"}]. grants:
    identity to grant dict, as check_action takes it.
    journal: the existing refusal records, used only for
    dedupe, never mutated. Returns the new records only;
    an allowed attempt journals nothing, and a second
    tick over the same attempts journals nothing new.
    Inputs are never mutated, malformed attempts never
    crash the tick.
    """
    if not isinstance(attempts, list):
        return []
    if not isinstance(grants, dict):
        grants = {}
    records = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        identity = attempt.get("identity")
        action = attempt.get("action")
        subject = attempt.get("subject")
        decision = check_action(grants.get(identity), action,
                                subject, identity=identity)
        if decision is None or decision["allowed"]:
            continue
        alert = refusal_alert(decision, now=now)
        if alert is None:
            continue
        if _already_journaled(journal, alert["dedupe_key"]) \
                or _already_journaled(records,
                                      alert["dedupe_key"]):
            continue
        record = {"kind": "capability-refusal",
                  "dedupe_key": alert["dedupe_key"],
                  "identity": identity, "action": action,
                  "subject": subject,
                  "missing_capability":
                      decision["missing_capability"],
                  "reason": decision["reason"],
                  "explanation": alert["explanation"],
                  "suggested_fix": alert["suggested_fix"],
                  "created_at": now}
        records.append(record)
    return records


def brief_lines(records):
    """One brief line per capability-refusal record."""
    lines = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        if record.get("kind") != "capability-refusal":
            continue
        lines.append("Capability refusal: "
                     + str(record.get("identity"))
                     + " tried " + str(record.get("action"))
                     + ", missing "
                     + str(record.get("missing_capability")))
    return lines
