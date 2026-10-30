"""intel/soak_review.py -- seven-day soak journal review (OS-074, Milo).

OS-074 asks for a seven-day soak: the full crew plus all
drivers run unattended on Meta OS for 7 days, and the
watchdog journal is reviewed end to end. The acceptance
is strict: every silent failure in the log has an alert
or a filed bug, and zero unexplained gaps remain.

This module is the review half only, as pure functions
of fixture journal entries. It reads a journal, it never
runs a crew, never touches a live machine, and never
posts to the bus. The soak itself is not claimed here:
no booted Meta OS image runs in this repo, the crew
does not run on Meta OS here, and seven days have not
elapsed on any such image. What this module proves is
that the review rule is mechanical and checkable: given
a journal, it names exactly which failures are covered
and which are unexplained gaps, so a real soak report
cannot fudge a count.

Journal entry shapes (all other shapes are malformed
and are reported in skipped, never counted, never a
crash):

- {"kind": "silent_failure", "id": "f1", "day": 3}
  A silent failure observed on soak day 3. The day must
  be an integer 1 to 7; a failure without a usable day
  still counts as a failure, but it is also listed in
  undated so the report never pretends to know its day.
- {"kind": "alert", "failure_id": "f1"}
  An alert record covering failure f1.
- {"kind": "bug", "failure_id": "f1"}
  A filed bug covering failure f1.

Coverage rule: a failure is covered when at least one
alert or one bug names its id. An alert or bug naming
no failure, or naming a failure id that never appears
as a silent_failure entry, is an orphan: reported in
orphans, never counted as coverage, because coverage
of nothing is not coverage. Duplicate alerts or bugs
for the same failure still count as one coverage: the
report lists each covering record id, but covered is a
count of failures, not of records.

Verdict: "clean" when unexplained_gaps is empty, else
"gaps". Days are reported, not judged: days_present
lists the soak days seen in any entry, days_missing
lists 1 to 7 not seen, so a partial journal is visible
as partial instead of silently passing as a full week.
A clean verdict on a journal missing days is still a
clean failure verdict, and the missing days say plainly
that the week is not complete.

Inputs are never mutated. The report carries no push
and no announcement field, and this module imports no
push module.

Usage: review_journal(entries) returns the report dict
(with its brief lines via soak_brief_lines(report)).
"""

__all__ = ["review_journal", "soak_brief_lines"]

SOAK_DAYS = (1, 2, 3, 4, 5, 6, 7)


def _is_failure(entry):
    return (isinstance(entry, dict)
            and entry.get("kind") == "silent_failure"
            and isinstance(entry.get("id"), str)
            and entry.get("id") != "")


def _is_cover(entry):
    return (isinstance(entry, dict)
            and entry.get("kind") in ("alert", "bug")
            and isinstance(entry.get("failure_id"), str)
            and entry.get("failure_id") != "")


def review_journal(entries):
    """Review one soak journal and return the report dict."""
    if not isinstance(entries, list):
        entries = []
    failures = {}
    order = []
    undated = []
    days_present = set()
    covers = {}
    orphans = []
    skipped = []
    for entry in entries:
        if _is_failure(entry):
            failure_id = entry["id"]
            if failure_id not in failures:
                failures[failure_id] = {"id": failure_id,
                                        "alerts": [], "bugs": []}
                order.append(failure_id)
            day = entry.get("day")
            if isinstance(day, int) and not isinstance(day, bool) \
                    and day in SOAK_DAYS:
                days_present.add(day)
            else:
                if failure_id not in undated:
                    undated.append(failure_id)
        elif _is_cover(entry):
            day = entry.get("day")
            if isinstance(day, int) and not isinstance(day, bool) \
                    and day in SOAK_DAYS:
                days_present.add(day)
            covers.setdefault(entry["failure_id"], []).append(entry)
        elif isinstance(entry, dict) and entry.get("kind") in ("alert", "bug"):
            skipped.append(entry)
        else:
            skipped.append(entry)
    coverage = {}
    covered = []
    gaps = []
    for failure_id in order:
        records = covers.get(failure_id, [])
        alerts = [r.get("id") for r in records
                  if r.get("kind") == "alert"
                  and isinstance(r.get("id"), str)]
        bugs = [r.get("id") for r in records
                if r.get("kind") == "bug"
                and isinstance(r.get("id"), str)]
        named = bool(records)
        coverage[failure_id] = {"alerts": alerts, "bugs": bugs,
                                "covered": named}
        if named:
            covered.append(failure_id)
        else:
            gaps.append(failure_id)
    for failure_id, records in covers.items():
        if failure_id not in failures:
            for record in records:
                orphans.append({"failure_id": failure_id,
                                "kind": record.get("kind"),
                                "id": record.get("id")})
    days_missing = [day for day in SOAK_DAYS if day not in days_present]
    report = {
        "total_failures": len(order),
        "covered_failures": len(covered),
        "covered": covered,
        "unexplained_gaps": gaps,
        "coverage": coverage,
        "orphans": orphans,
        "undated": undated,
        "days_present": sorted(days_present),
        "days_missing": days_missing,
        "skipped": len(skipped),
        "verdict": "clean" if not gaps else "gaps",
    }
    return report


def soak_brief_lines(report):
    """Plain brief lines for a soak report."""
    lines = [
        "Soak review: %d failures, %d covered, %d unexplained gaps."
        % (report["total_failures"], report["covered_failures"],
           len(report["unexplained_gaps"])),
        "Soak verdict: %s." % (report["verdict"],),
    ]
    for failure_id in report["unexplained_gaps"]:
        lines.append("Unexplained gap: failure %s has no alert and no bug."
                     % (failure_id,))
    if report["days_missing"]:
        lines.append("Soak days missing: %s."
                     % (", ".join(str(d) for d in report["days_missing"])))
    else:
        lines.append("Soak days: all 7 days present.")
    return lines
