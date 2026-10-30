"""Demo drill: budget forecast + preemption (Milo lane, OS-091).

Five phases on fixtures, no network, no Redis, no bus posts:

1. Forecast: lane "spark" at 80 spent of 100 cap after 8 hours
   of ledger projects 240 by end of day — over cap, medium
   confidence, basis naming the 8 hours.
2. Preempt: a running low-priority job in that warning lane is
   paused, its progress field untouched, never failed/killed.
3. No preempt: a running high-priority job in the same lane is
   left exactly as it was.
4. Resume: the lane's budget frees (new period, 10 of 100),
   the paused job resumes to running with progress unchanged.
5. Brief lines: the forecast renders as one plain line naming
   lane, spent, cap, projected spend, basis, confidence, and
   the breach verdict — no bullet, so the BRF-007 trim keeps it.

Usage: python3 intel/drills/budget_forecast.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import sys

sys.path.insert(0, ".")

from intel import budgets
from intel import forecast


def _check(name, condition):
    print(("PASS" if condition else "FAIL") + ": " + name)
    if not condition:
        sys.exit(1)


def main():
    lane = {"lane": "spark", "spent": 80, "cap": 100}
    state = budgets.budget_state(lane)
    _check("warning lane state", state == "warning")

    # Phase 1: forecast.
    entry = forecast.forecast_entry("spark", 80, 100, 8)
    _check("forecast projects 240 by end of day",
           entry is not None and entry["projected"] == 240.0)
    _check("forecast flags the breach", entry["over_cap"] is True)
    _check("forecast confidence is medium",
           entry["confidence"] == "medium")
    _check("forecast basis names the 8 hours",
           "8 hours of ledger" in entry["basis"])

    # Phase 2: preempt the low-priority running job, progress kept.
    low_job = {"id": "job-low", "priority": "low", "status": "running",
               "progress": "step 3 of 5 done"}
    _check("low-priority running job pauses",
           forecast.preempt_decision(low_job, state) == "pause")
    paused = dict(low_job, status="paused")
    _check("pause keeps progress, never fails the job",
           paused["progress"] == "step 3 of 5 done"
           and paused["status"] != "failed")
    record = forecast.preempt_record("job-low", "spark", "paused",
                                     "lane at warning, low priority")
    _check("pause journal record names job, lane, action",
           record["job"] == "job-low" and record["lane"] == "spark"
           and record["action"] == "paused")

    # Phase 3: high-priority work is never preempted.
    high_job = {"id": "job-high", "priority": "high",
                "status": "running", "progress": "step 1 of 2 done"}
    _check("high-priority job untouched",
           forecast.preempt_decision(high_job, state) is None)

    # Phase 4: budget frees, the paused job resumes cleanly.
    freed = budgets.budget_state({"lane": "spark", "spent": 10,
                                  "cap": 100})
    _check("freed lane state", freed == "ok")
    _check("paused job resumes when budget frees",
           forecast.preempt_decision(paused, freed) == "resume")
    resumed = dict(paused, status="running")
    _check("resume keeps progress, no repeated work",
           resumed["progress"] == "step 3 of 5 done"
           and resumed["status"] == "running")

    # Phase 5: brief line.
    lines = forecast.forecast_lines(
        [{"lane": "spark", "spent": 80, "cap": 100,
          "elapsed_hours": 8}])
    _check("one forecast brief line",
           len(lines) == 1 and lines[0].startswith(
               "Budget forecast for lane spark: 80 spent of 100 cap, "
               "projected 240 by end of day")
           and "8 hours of ledger" in lines[0]
           and "medium confidence" in lines[0]
           and "breach expected before end of day" in lines[0]
           and not lines[0].lstrip().startswith(("-", "*")))

    print("PASS: budget forecast drill complete (5/5 phases)")


if __name__ == "__main__":
    main()
