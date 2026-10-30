"""Timer fallback sweep drill (Milo lane, OS-121).

Acceptance: with the watchman deliberately disabled, a
posted job is still claimed within one sweep interval
by the timer path alone; with the watchman healthy,
sweeps produce zero duplicate claims (lease discipline
holds across both paths).

What fixtures can prove, and what they cannot, stated
plainly. The module (intel/timer_sweep.py) computes the
claim set a correct timer sweep must produce from fixture
queue state; it does not wake any agent, ring any bell,
or move a claim in a live queue. The mechanical half
(the runtime timer that actually wakes an agent) is
outside this repo's fixture layer, and a live sweep on
a booted test image is not claimed here, because no test
image runs in this repo. This drill proves the decision
layer on fixtures with a fake clock: interval 300, ticks
at 0, 300, 600, 900, local roster milo, hana, rowan.

Phases:

- dead watchman claims within one interval: a job posted
  at 100 is claimed at the 300 tick (delay 200, inside
  the 300 interval); a job posted at 550 is claimed at
  the 600 tick (delay 50). No claimed job waits longer
  than one interval.
- healthy watchman claims nothing: the same jobs across
  the same ticks yield zero claims and zero duplicates,
  because the bell owns claiming while it lives.
- unknown watchman holds: with watchman state None, the
  sweep claims nothing, because missing evidence is never
  read as a dead watchman.
- lease discipline: a claimed job is never re-claimed
  by the sweep, even with the watchman dead; a done job
  is never claimed; a job already in the sweep ledger is
  never claimed again, so repeated sweeps with a dead
  watchman produce zero duplicate claims.
- addressing: a job addressed to an outsider is never
  claimed by this machine's sweep; an unaddressed job is
  never claimed (routing it would invent a worker).
- cadence: a tick before last sweep plus interval does
  not run and changes nothing; the first tick always
  runs; a future job (posted after now) is never claimed.
- immutable and no-Dale: computing a tick leaves the job
  records and the ledger unchanged; the note carries no
  push and no announcement field, and the module imports
  no push module.

What this drill does NOT claim: a live agent actually
woken by a timer, a live bell missed and recovered on a
booted test image, or the resident watchman itself
(Pax OS-118).
"""

import copy
import sys

sys.path.insert(0, ".")

from intel import timer_sweep  # noqa: E402

INTERVAL = 300
ROSTER = ["milo", "hana", "rowan"]

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    print(("PASS " if condition else "FAIL ") + name
          + ((" -- " + detail) if detail else ""))
    return condition


def main():
    jobs = [
        {"id": "job-early", "status": "open", "posted_at": 100,
         "addressed_to": "milo"},
        {"id": "job-late", "status": "open", "posted_at": 550,
         "addressed_to": "hana"},
        {"id": "job-future", "status": "open", "posted_at": 950,
         "addressed_to": "rowan"},
        {"id": "job-claimed", "status": "claimed",
         "claimed_by": "rowan", "posted_at": 50,
         "addressed_to": "rowan"},
        {"id": "job-done", "status": "done", "posted_at": 50,
         "addressed_to": "milo"},
        {"id": "job-outsider", "status": "open", "posted_at": 100,
         "addressed_to": "outsider"},
        {"id": "job-unaddressed", "status": "open", "posted_at": 100},
        "not-a-record",
        {"status": "open", "posted_at": 100, "addressed_to": "milo"},
    ]
    original = copy.deepcopy(jobs)

    tick0 = timer_sweep.sweep_cycle(jobs, 0, False,
                                     sweep_interval_seconds=INTERVAL,
                                     local_agents=ROSTER)
    check("first tick runs with dead watchman",
          tick0["ran"] is True and tick0["claims"] == [],
          "claims=%s" % (tick0["claims"],))
    tick300 = timer_sweep.sweep_cycle(
        jobs, 300, False, sweep_interval_seconds=INTERVAL,
        last_sweep_at=0, sweep_ledger=tick0["sweep_ledger_after"],
        local_agents=ROSTER)
    claim_ids_300 = [c["job_id"] for c in tick300["claims"]]
    check("job posted at 100 claimed at tick 300",
          claim_ids_300 == ["job-early"],
          "claims=%s" % (claim_ids_300,))
    check("claim delay inside one interval",
          tick300["claims"][0]["claimed_at"] - 100 <= INTERVAL,
          "delay=%s" % (tick300["claims"][0]["claimed_at"] - 100,))
    tick600 = timer_sweep.sweep_cycle(
        jobs, 600, False, sweep_interval_seconds=INTERVAL,
        last_sweep_at=300,
        sweep_ledger=tick300["sweep_ledger_after"],
        local_agents=ROSTER)
    claim_ids_600 = [c["job_id"] for c in tick600["claims"]]
    check("job posted at 550 claimed at tick 600",
          claim_ids_600 == ["job-late"],
          "claims=%s" % (claim_ids_600,))
    check("second claim delay inside one interval",
          tick600["claims"][0]["claimed_at"] - 550 <= INTERVAL,
          "delay=%s" % (tick600["claims"][0]["claimed_at"] - 550,))
    check("future job never claimed early",
          "job-future" not in claim_ids_300
          and "job-future" not in claim_ids_600)
    tick900 = timer_sweep.sweep_cycle(
        jobs, 900, False, sweep_interval_seconds=INTERVAL,
        last_sweep_at=600,
        sweep_ledger=tick600["sweep_ledger_after"],
        local_agents=ROSTER)
    check("repeat sweeps with dead watchman claim nothing new",
          tick900["claims"] == [],
          "claims=%s" % (tick900["claims"],))
    skipped_600 = {s["job_id"]: s["reason"]
                   for s in tick600["skipped"]}
    check("claimed job never re-claimed",
          "job-claimed" in skipped_600
          and "not open" in skipped_600["job-claimed"])
    check("done job never claimed",
          "job-done" in skipped_600
          and "not open" in skipped_600["job-done"])
    check("outsider job never claimed",
          "job-outsider" in skipped_600
          and skipped_600["job-outsider"] == "addressed elsewhere")
    check("unaddressed job never claimed",
          "job-unaddressed" in skipped_600
          and "unaddressed" in skipped_600["job-unaddressed"])

    healthy = timer_sweep.sweep_cycle(
        jobs, 300, True, sweep_interval_seconds=INTERVAL,
        local_agents=ROSTER)
    check("healthy watchman: sweep claims nothing",
          healthy["ran"] is True and healthy["claims"] == [],
          "claims=%s" % (healthy["claims"],))
    healthy2 = timer_sweep.sweep_cycle(
        jobs, 600, True, sweep_interval_seconds=INTERVAL,
        last_sweep_at=300,
        sweep_ledger=healthy["sweep_ledger_after"],
        local_agents=ROSTER)
    check("healthy watchman: repeated sweeps zero duplicates",
          healthy2["claims"] == []
          and healthy2["sweep_ledger_after"] == [])

    unknown = timer_sweep.sweep_cycle(
        jobs, 300, None, sweep_interval_seconds=INTERVAL,
        local_agents=ROSTER)
    check("unknown watchman: sweep holds, claims nothing",
          unknown["claims"] == []
          and "unknown" in unknown["reason"])

    early = timer_sweep.sweep_cycle(
        jobs, 150, False, sweep_interval_seconds=INTERVAL,
        last_sweep_at=0, local_agents=ROSTER)
    check("tick before interval does not run",
          early["ran"] is False and early["claims"] == []
          and early["next_sweep_at"] == 300)

    doubled = jobs + [{"id": "job-early", "status": "open",
                       "posted_at": 100, "addressed_to": "milo"}]
    dup = timer_sweep.sweep_cycle(
        doubled, 300, False, sweep_interval_seconds=INTERVAL,
        local_agents=ROSTER)
    check("duplicate input claimed once",
          [c["job_id"] for c in dup["claims"]].count("job-early") == 1)

    ledger = ["job-early"]
    timer_sweep.sweep_cycle(jobs, 300, False,
                            sweep_interval_seconds=INTERVAL,
                            sweep_ledger=ledger, local_agents=ROSTER)
    check("inputs never mutated",
          jobs == original and ledger == ["job-early"])
    check("no Dale contact in note",
          "push" not in tick600 and "announcement" not in tick600)
    import inspect
    source = inspect.getsource(timer_sweep)
    check("no push import in module",
          "import push" not in source
          and "from intel import push" not in source)
    lines = timer_sweep.sweep_brief_lines(tick600)
    check("brief lines name claims and next sweep",
          any("job-late" in line for line in lines)
          and any("next sweep" in line for line in lines))

    failed = [name for name, ok, _ in RESULTS if not ok]
    print("%d PASS, %d FAIL" % (len(RESULTS) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
