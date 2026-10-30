"""Budget gate drill (Milo lane, OS-085).

Scenario: the spark lane spends its way toward its cap, and
the crew must hear about it before the silence, not after.
At 70 of 100 the watchdog stays quiet and claims flow; at 80
of 100 (the warning threshold) the watchdog raises exactly
one budget-warning alert naming the lane, the spent figure,
and the cap; at 100 of 100 the queue holds new claims — the
job stays open for a later, funded run — and the brief's
budget line says so in plain words.

Runs unattended on fixtures: no network, no Redis, no bus
posts. The queue half is a fake with jobs.py claim semantics
(a claim that is refused leaves the job open, never claimed):
the live jobs.py claim path does not read the budget gate yet
because there is no spend ledger in Redis for it to read
from, and a gate wired to a ledger nobody writes would
refuse or allow claims on stale figures. The drill proves
the gate itself — the same pure function the live path will
call once the ledger exists — and the eval doc names that
wiring as owed, not proven.

The brief half uses the real renderer (intel/brief.py
memory_budget_lines over a snapshot memory_budget record),
so the "new claims held" wording in the drill is the wording
the brief will actually print.

Usage: python3 intel/drills/budget_gate.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import budgets  # noqa: E402
from intel import brief  # noqa: E402
from intel import watchdog  # noqa: E402

LANE = "spark"
CAP = 100
NOW = 100000


class FakeQueue:
    """A fixture job queue with the OS-085 budget gate.

    claim() mirrors jobs.py's outcome shape: a granted claim
    marks the job claimed; a refused claim leaves the job
    open and records the hold. The gate itself is
    intel/budgets.py claim_allowed — the drill never
    re-implements "at cap", so a gate change retunes the
    drill instead of silently disagreeing with it.
    """

    def __init__(self):
        self.jobs = {}
        self.holds = []

    def post(self, job_id, lane):
        self.jobs[job_id] = {"id": job_id, "lane": lane,
                             "status": "open"}
        return self.jobs[job_id]

    def claim(self, job_id, spent, cap):
        job = self.jobs[job_id]
        if not budgets.claim_allowed(spent, cap):
            self.holds.append(job_id)
            return False
        job["status"] = "claimed"
        return True


def _snapshot(spent):
    return {"jobs": [], "messages": [], "presence": [],
            "caps": {},
            "budgets": [{"lane": LANE, "spent": spent,
                         "cap": CAP}]}


def _budget_warnings(snapshot):
    return [a for a in watchdog.tick(snapshot, now=NOW)
            if a["kind"] == "budget-warning"]


def main(argv=None):
    try:
        queue = FakeQueue()
        queue.post("1", LANE)
        # Phase 1: under the warning threshold — quiet, claims flow.
        assert _budget_warnings(_snapshot(70)) == [], (
            "70 of 100 must yield no budget warning")
        assert queue.claim("1", 70, CAP) is True, (
            "claim under cap must be granted")
        assert queue.jobs["1"]["status"] == "claimed"
        print("budget_gate drill: PASS phase 1 — 70/100: no "
              "warning, claim granted")
        # Phase 2: at the warning threshold — exactly one warning,
        # and claims still flow (the lane is at risk, not stopped).
        warnings = _budget_warnings(_snapshot(80))
        assert len(warnings) == 1, (
            f"80 of 100 must yield exactly one warning, got {warnings}")
        alert = warnings[0]
        assert alert["severity"] == "warning", alert
        assert alert["lane"] == LANE and alert["spent"] == 80 \
            and alert["cap"] == CAP, alert
        assert "spark" in alert["explanation"] \
            and "80" in alert["explanation"], alert
        assert alert["dedupe_key"] == "budget-warning:spark", alert
        queue.post("2", LANE)
        assert queue.claim("2", 80, CAP) is True, (
            "claim at warning threshold must still be granted")
        print("budget_gate drill: PASS phase 2 — 80/100: one "
              "budget-warning alert (spark, 80 of 100), claim "
              "still granted")
        # Phase 3: at cap — no warning (the hold is the louder
        # signal), the claim is held, the job stays open, and
        # the brief's budget line says so.
        assert _budget_warnings(_snapshot(100)) == [], (
            "100 of 100 must yield no warning — the hold "
            "replaces it, not doubles it")
        queue.post("3", LANE)
        assert queue.claim("3", 100, CAP) is False, (
            "claim at cap must be held")
        assert queue.jobs["3"]["status"] == "open", (
            "a held claim leaves the job open")
        assert queue.holds == ["3"], queue.holds
        lines = brief.memory_budget_lines({
            "budgets": [budgets.hold_entry(LANE, 100, CAP)]})
        held = [line for line in lines if "spark" in line]
        assert len(held) == 1 and "new claims held" in held[0], lines
        print("budget_gate drill: PASS phase 3 — 100/100: "
              "no warning, claim held, job stays open, "
              "brief line reads: " + held[0])
        # Phase 4: negatives — an unbudgeted lane and malformed
        # entries never warn, never hold, never crash.
        assert _budget_warnings(
            {"budgets": [{"lane": "unbudgeted"}]}) == [], (
            "a lane with no cap must not warn")
        assert _budget_warnings(
            {"budgets": [{"lane": "bad", "spent": "lots",
                          "cap": "none"},
                         {"spent": 90, "cap": 100},
                         "not-a-dict"]}) == [], (
            "malformed entries must be skipped, not guessed")
        assert budgets.claim_allowed(None, None) is True, (
            "an unbudgeted lane always allows claims")
        print("budget_gate drill: PASS phase 4 — unbudgeted "
              "and malformed entries: no warning, no hold, "
              "no crash")
    except AssertionError as exc:
        print(f"budget_gate drill: FAIL: {exc}")
        return 1
    print("budget_gate drill: PASS — warning at threshold, "
          "hold at cap, brief line names the hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
