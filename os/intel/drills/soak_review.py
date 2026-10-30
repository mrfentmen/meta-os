"""Seven-day soak journal review drill (Milo lane, OS-074 prep).

OS-074 acceptance: the full crew plus all drivers run
unattended on Meta OS for 7 days, and the watchdog
journal is reviewed end to end: every silent failure
in the log has an alert or a filed bug, and zero
unexplained gaps remain.

This drill does NOT run the soak and does NOT claim
it: no booted Meta OS image runs in this repo, the
crew does not run on Meta OS here, and seven days
have not elapsed on any such image. What it proves is
the review half on fixtures, so a real soak report
cannot fudge a count: a clean 7-day journal reads
clean with zero gaps, a journal with one uncovered
failure names exactly that failure as its gap, and
partial, orphan, duplicate, and malformed input is
reported instead of silently passed.

Fixture journal, clean week: failures f1 (day 1,
alert a1), f2 (day 3, bug b1), f3 (day 5, alert a2
plus bug b2), plus one cover entry per day so all 7
days are present. Gap week: the same journal minus
the bug for f2, so f2 is the one unexplained gap.
"""

import copy
import sys

sys.path.insert(0, ".")

from intel import soak_review  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    print(("PASS " if condition else "FAIL ") + name
          + ((" -- " + detail) if detail else ""))
    return condition


def clean_journal():
    journal = [
        {"kind": "silent_failure", "id": "f1", "day": 1},
        {"kind": "alert", "id": "a1", "failure_id": "f1", "day": 1},
        {"kind": "silent_failure", "id": "f2", "day": 3},
        {"kind": "bug", "id": "b1", "failure_id": "f2", "day": 3},
        {"kind": "silent_failure", "id": "f3", "day": 5},
        {"kind": "alert", "id": "a2", "failure_id": "f3", "day": 5},
        {"kind": "bug", "id": "b2", "failure_id": "f3", "day": 5},
        {"kind": "alert", "id": "a-day2", "failure_id": "f1", "day": 2},
        {"kind": "alert", "id": "a-day4", "failure_id": "f1", "day": 4},
        {"kind": "alert", "id": "a-day6", "failure_id": "f1", "day": 6},
        {"kind": "alert", "id": "a-day7", "failure_id": "f1", "day": 7},
    ]
    return journal


def main():
    journal = clean_journal()
    original = copy.deepcopy(journal)
    report = soak_review.review_journal(journal)
    check("clean week reads clean with zero gaps",
          report["verdict"] == "clean"
          and report["unexplained_gaps"] == [],
          "verdict=%s gaps=%s" % (report["verdict"],
                                  report["unexplained_gaps"]))
    check("clean week counts 3 failures, 3 covered",
          report["total_failures"] == 3
          and report["covered_failures"] == 3)
    check("all 7 days present in clean week",
          report["days_present"] == [1, 2, 3, 4, 5, 6, 7]
          and report["days_missing"] == [])
    check("bug coverage counts as coverage",
          report["coverage"]["f2"]["covered"] is True
          and report["coverage"]["f2"]["bugs"] == ["b1"])
    check("alert plus bug both listed for one failure",
          report["coverage"]["f3"]["alerts"] == ["a2"]
          and report["coverage"]["f3"]["bugs"] == ["b2"])

    gap_journal = [e for e in clean_journal()
                   if not (e.get("kind") == "bug"
                           and e.get("failure_id") == "f2")]
    gap = soak_review.review_journal(gap_journal)
    check("one uncovered failure is the one gap",
          gap["verdict"] == "gaps"
          and gap["unexplained_gaps"] == ["f2"],
          "gaps=%s" % (gap["unexplained_gaps"],))
    check("gap week still counts 2 of 3 covered",
          gap["covered_failures"] == 2
          and gap["total_failures"] == 3)

    partial = [e for e in clean_journal() if e.get("day") in (1, 3, 5)]
    partial_report = soak_review.review_journal(partial)
    check("partial journal names its missing days",
          partial_report["days_present"] == [1, 3, 5]
          and partial_report["days_missing"] == [2, 4, 6, 7])

    orphan_journal = clean_journal() + [
        {"kind": "alert", "id": "a-orphan",
         "failure_id": "f-ghost", "day": 2},
        {"kind": "bug", "id": "b-orphan",
         "failure_id": "f-ghost", "day": 2},
    ]
    orphan = soak_review.review_journal(orphan_journal)
    check("orphan covers are reported, never counted",
          orphan["total_failures"] == 3
          and orphan["covered_failures"] == 3
          and len(orphan["orphans"]) == 2)

    dup_journal = clean_journal() + [
        {"kind": "alert", "id": "a1-dup", "failure_id": "f1", "day": 1},
    ]
    dup = soak_review.review_journal(dup_journal)
    check("duplicate alert still counts as one coverage",
          dup["covered_failures"] == 3
          and dup["coverage"]["f1"]["covered"] is True)

    messy = clean_journal() + [
        "not-a-record",
        {"kind": "silent_failure"},
        {"kind": "alert", "day": 2},
        {"kind": "silent_failure", "id": "f4"},
    ]
    messy_report = soak_review.review_journal(messy)
    check("malformed entries are skipped, never a crash",
          messy_report["skipped"] == 3
          and messy_report["total_failures"] == 4)
    check("failure without a day is listed undated",
          messy_report["undated"] == ["f4"])
    check("undated uncovered failure is still a gap",
          "f4" in messy_report["unexplained_gaps"])

    empty = soak_review.review_journal([])
    check("empty journal is clean with zero failures",
          empty["verdict"] == "clean"
          and empty["total_failures"] == 0
          and empty["days_missing"] == [1, 2, 3, 4, 5, 6, 7])
    check("non-list journal reads as empty, never crashes",
          soak_review.review_journal(None)["total_failures"] == 0)

    check("inputs never mutated",
          journal == original)
    check("no Dale contact in report",
          "push" not in report and "announcement" not in report)
    import inspect
    source = inspect.getsource(soak_review)
    check("no push import in module",
          "import push" not in source
          and "from intel import push" not in source)
    lines = soak_review.soak_brief_lines(gap)
    check("brief lines name the gap and the verdict",
          any("f2" in line for line in lines)
          and any("gaps" in line for line in lines))
    clean_lines = soak_review.soak_brief_lines(report)
    check("brief lines for clean week say all 7 days present",
          any("all 7 days present" in line for line in clean_lines))

    failed = [name for name, ok, _ in RESULTS if not ok]
    print("%d PASS, %d FAIL" % (len(RESULTS) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
