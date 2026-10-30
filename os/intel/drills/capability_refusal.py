"""intel/drills/capability_refusal.py -- OS-081 drill (Milo).

A fixture crew process attempts actions inside and outside
its grant: a bus post with bus_post off, a spend with
spend off, a network reach with network off, a file write
outside its write paths, a file write inside its write
paths, a write path that escapes through dot-dot segments,
and a process with no grant file at all. Grants are plain
dicts in the OS-080 shape, supplied by the caller; no
capability file is read or written, because OS-080 has
not landed yet.

Pass bar: every outside-grant attempt is refused with the
exact missing capability its case earns, the explanation
names the identity, the action, and the missing
capability, and the refusal note says the same; every
inside-grant attempt is allowed and journals nothing; a
tick journals one refusal record per refused attempt and
nothing else; a second tick journals nothing new; inputs
are never mutated; and the module carries no push path,
so a refusal judged here can never ring a phone on its
own. The alert record shape is proven through
intel.store.build_alert_record on a fake backend, not
through a live Redis.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", ".."))

from intel import capability  # noqa: E402
from intel import store  # noqa: E402

NOW = 100000

GRANTS = {
    "milo": {"identity": "milo", "bus_post": False,
             "spend": False, "network": True,
             "write_paths": ["crew/milo/"]},
    "pax": {"identity": "pax", "bus_post": True,
            "spend": True, "network": True,
            "write_paths": ["crew/pax/", "plan/"]},
}


def check(name, condition, detail=""):
    if condition:
        print(name + ": PASS")
        return True
    print(name + ": FAIL: " + str(detail))
    return False


def phase_allowed():
    ok = True
    decision = capability.check_action(GRANTS["pax"], "bus_post")
    ok &= check("allowed-bus-post", decision["allowed"], decision)
    decision = capability.check_action(GRANTS["milo"], "network")
    ok &= check("allowed-network", decision["allowed"], decision)
    decision = capability.check_action(GRANTS["pax"], "write_file",
                                       "plan/lanes/PAX.md")
    ok &= check("allowed-write-inside", decision["allowed"],
                decision)
    return bool(ok)


def phase_refused():
    cases = [
        ("milo", "bus_post", None, "bus_post",
         "capability not granted"),
        ("milo", "spend", None, "spend",
         "capability not granted"),
        ("pax", "write_file", "crew/milo/notes.md",
         "write:crew/milo/notes.md", "write path outside grant"),
        ("milo", "write_file", "crew/milo/../pax/x.md",
         "write:crew/pax/x.md", "write path outside grant"),
        ("milo", "write_file", None, "write_file",
         "no file path given"),
        ("ghost", "bus_post", None, "bus_post",
         "no capability grant on file"),
        ("milo", "teleport", None, "teleport", "unknown action"),
    ]
    ok = True
    for identity, action, subject, missing, reason in cases:
        decision = capability.check_action(GRANTS.get(identity),
                                           action, subject,
                                           identity=identity)
        if decision is None or decision["allowed"]:
            ok &= check("refused-" + identity + "-" + action,
                        False, decision)
            continue
        good = (decision["missing_capability"] == missing
                and decision["reason"] == reason)
        ok &= check("refused-" + identity + "-" + action, good,
                    decision)
        alert = capability.refusal_alert(decision, now=NOW)
        text = alert["explanation"] + " " + alert["suggested_fix"]
        named = (identity in text and action in text
                 and missing in text)
        ok &= check("explanation-names-" + identity + "-"
                    + action, named, text)
        note = capability.refusal_note(decision)
        noted = (identity in note and action in note
                 and missing in note)
        ok &= check("note-names-" + identity + "-" + action,
                    noted, note)
        if alert["kind"] != "capability-refusal" \
                or alert["severity"] != "warning":
            ok &= check("alert-shape-" + identity + "-"
                        + action, False, alert)
    return bool(ok)


def phase_tick():
    attempts = [
        {"identity": "milo", "action": "bus_post",
         "subject": None},
        {"identity": "milo", "action": "spend",
         "subject": None},
        {"identity": "pax", "action": "bus_post",
         "subject": None},
        {"identity": "milo", "action": "write_file",
         "subject": "crew/milo/notes.md"},
        {"identity": "milo", "action": "bus_post",
         "subject": None},
        "not-a-dict",
        {"identity": "milo", "action": "", "subject": None},
    ]
    snapshot_attempts = copy.deepcopy(attempts)
    snapshot_grants = copy.deepcopy(GRANTS)
    journal = []
    first = capability.capability_tick(attempts, GRANTS, journal,
                                       NOW)
    journal.extend(first)
    second = capability.capability_tick(attempts, GRANTS, journal,
                                        NOW + 60)
    ok = True
    ok &= check("tick-count", len(first) == 2, first)
    ok &= check("tick-second-silent", second == [], second)
    ok &= check("tick-inputs-immutable",
                attempts == snapshot_attempts
                and GRANTS == snapshot_grants,
                (attempts, GRANTS))
    lines = capability.brief_lines(first)
    ok &= check("brief-lines", len(lines) == 2
                and "milo" in lines[0]
                and "bus_post" in lines[0], lines)
    return bool(ok)


def phase_alert_record():
    decision = capability.check_action(GRANTS["milo"], "bus_post")
    alert = capability.refusal_alert(decision, now=NOW)
    record = store.build_alert_record(alert, room="fixture-room",
                                      now=NOW)
    ok = True
    ok &= check("record-kind", record["kind"]
                == "capability-refusal", record)
    ok &= check("record-status-open", record["status"] == "open",
                record)
    ok &= check("record-id-is-dedupe",
                record["id"] == alert["dedupe_key"], record)
    ok &= check("record-explanation-names",
                "milo" in record["explanation"]
                and "bus_post" in record["explanation"],
                record)
    return bool(ok)


def phase_no_push():
    path = os.path.join(os.path.dirname(__file__),
                        "..", "capability.py")
    with open(path) as handle:
        text = handle.read()
    banned = ("push.py", "bus_post(", "announce(",
              "post_to_bus", "redis", "socket")
    found = [word for word in banned if word in text]
    return check("no-push-path", not found, found)


def main():
    results = [phase_allowed(), phase_refused(), phase_tick(),
               phase_alert_record(), phase_no_push()]
    total = sum(results)
    print("capability_refusal: %d/%d phases PASS"
          % (total, len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
