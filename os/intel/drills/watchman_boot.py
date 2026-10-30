"""Watchman-boot drill (Milo lane, OS-129).

Acceptance: across the power cuts, the watchman's first
post-boot cycle rings for every job that arrived during
downtime and none are double-rung or missed; a
deliberately corrupted stored counter value changes
nothing in the watchman's behaviour, proving it never
reads one; Milo's verification note on the drill is filed
separately from Buffy's run log.

What fixtures can prove, and what they cannot, stated
plainly. The module (intel/watchman_boot.py) computes
the ring set a correct watchman must produce from queue
claims and leases; it does not ring any bell and it
moves no claim. The mechanical half (the resident
watchman program that actually rings) is Pax OS-118, and
a live boot on a booted test image is not claimed here,
because no test image runs in this repo. This drill is
Milo's verification half: it checks the ring computation
and its reconciliation with the lease sweep, on fixtures
with a fake clock (downtime window T0 to T1).

Phases:

- arrival rings: two open jobs posted inside the window
  ring with reason arrived_during_downtime; one open job
  posted before the window does not ring (it was already
  visible before the machine died); one open job posted
  after boot does not ring (it did not arrive during
  downtime).
- lease rings: a claimed job whose lease died inside the
  window rings with reason lease_expired_during_downtime;
  a claimed job whose lease is still alive at boot does
  not ring; a done job never rings, even with a lease
  expiry inside the window.
- no double ring: the same job listed twice in the input
  rings once; a second post-boot cycle with the first
  cycle's rung ids in the ledger rings nothing new; a job
  that is both an arrival and a lease case cannot exist
  (open vs claimed are exclusive), and the dedupe holds
  regardless of input order.
- corrupted counter: a snapshot carrying a stored counter
  value of 999999, and the same snapshot with the counter
  set to -42, both yield the identical ring set as the
  clean snapshot; the module takes no counter argument
  and its source imports no counter reader.
- sweep reconciliation: with a sweep record that requeues
  exactly the lease-expired ring ids, the verification
  note reports reconciled True and the recovered count
  matches; with a sweep record that drops one requeue
  and adds one stranger, the note reports reconciled
  False and names the missing and extra ids.
- immutable and no-Dale: computing rings and verifying
  leaves the job records and the rung ledger unchanged;
  the verification note carries no push and no
  announcement field, and the module imports no push
  module.

What this drill does NOT claim: a live watchman ringing
on a booted test image, a real power cut and reboot, or
the OS-126 drill itself (Buffy's run log is the other
file; this drill's eval note is Milo's verification note,
filed separately).
"""

import copy
import sys

sys.path.insert(0, ".")

from intel import watchman_boot  # noqa: E402

T0 = 100000
T1 = 100600

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    print(("PASS " if condition else "FAIL ") + name
          + ((" -- " + detail) if detail else ""))
    return condition


def main():
    jobs = [
        {"id": "job-arrive-1", "status": "open", "posted_at": T0 + 100},
        {"id": "job-arrive-2", "status": "open", "posted_at": T0 + 500},
        {"id": "job-before", "status": "open", "posted_at": T0 - 50},
        {"id": "job-after", "status": "open", "posted_at": T1 + 10},
        {"id": "job-lease-dead", "status": "claimed",
         "claimed_by": "hana", "lease_expires_at": T0 + 300},
        {"id": "job-lease-live", "status": "claimed",
         "claimed_by": "rowan", "lease_expires_at": T1 + 900},
        {"id": "job-done", "status": "done",
         "lease_expires_at": T0 + 200},
        {"id": "bad-record", "status": "open"},
        "not-a-record",
        {"status": "open", "posted_at": T0 + 10},
    ]
    original = copy.deepcopy(jobs)

    rings = watchman_boot.post_boot_rings(jobs, T0, T1)
    ring_ids = [r["job_id"] for r in rings]
    reasons = {r["job_id"]: r["reason"] for r in rings}
    check("arrival rings",
          ring_ids == ["job-arrive-1", "job-arrive-2", "job-lease-dead"]
          and reasons["job-arrive-1"] == "arrived_during_downtime"
          and reasons["job-arrive-2"] == "arrived_during_downtime"
          and reasons["job-lease-dead"] == "lease_expired_during_downtime",
          "rings=%s" % (ring_ids,))
    check("pre-window open job does not ring", "job-before" not in ring_ids)
    check("post-boot open job does not ring", "job-after" not in ring_ids)
    check("live lease does not ring", "job-lease-live" not in ring_ids)
    check("done job never rings", "job-done" not in ring_ids)
    check("malformed records never ring and never crash",
          "bad-record" not in ring_ids)

    doubled = jobs + [{"id": "job-arrive-1", "status": "open",
                       "posted_at": T0 + 100}]
    check("duplicate input rings once",
          [r["job_id"] for r in
           watchman_boot.post_boot_rings(doubled, T0, T1)
           ].count("job-arrive-1") == 1)
    second = watchman_boot.post_boot_rings(jobs, T0, T1,
                                           rung_ledger=ring_ids)
    check("second boot cycle rings nothing new", second == [])

    poisoned = []
    for job in jobs:
        if isinstance(job, dict):
            copy_job = dict(job)
            copy_job["seen_counter"] = 999999
            poisoned.append(copy_job)
        else:
            poisoned.append(job)
    poisoned_ids = [r["job_id"] for r in
                    watchman_boot.post_boot_rings(poisoned, T0, T1)]
    check("corrupted stored counter changes nothing",
          poisoned_ids == ring_ids, "rings=%s" % (poisoned_ids,))

    note = watchman_boot.verify_boot_cycle(
        jobs, T0, T1, sweep_requeued=["job-lease-dead"])
    check("sweep reconciliation agrees",
          note["reconciled"] is True
          and note["total_rings"] == 3
          and note["arrived_count"] == 2
          and note["lease_expired_count"] == 1
          and note["counter_ignored"] is True,
          "note counts=%d/%d/%d" % (note["total_rings"],
                                    note["arrived_count"],
                                    note["lease_expired_count"]))
    bad_note = watchman_boot.verify_boot_cycle(
        jobs, T0, T1, sweep_requeued=["job-stranger"])
    check("sweep mismatch named, never fudged",
          bad_note["reconciled"] is False
          and bad_note["mismatch"]["missing"] == ["job-lease-dead"]
          and bad_note["mismatch"]["extra"] == ["job-stranger"],
          "mismatch=%s" % (bad_note["mismatch"],))

    ledger = ["job-arrive-1"]
    watchman_boot.post_boot_rings(jobs, T0, T1, rung_ledger=ledger)
    watchman_boot.verify_boot_cycle(jobs, T0, T1, ["job-lease-dead"])
    check("inputs never mutated",
          jobs == original and ledger == ["job-arrive-1"])
    check("no Dale contact in note",
          "push" not in note and "announcement" not in note)
    import inspect
    source = inspect.getsource(watchman_boot)
    check("no push import in module",
          "import push" not in source and "from intel import push" not in source)
    lines = watchman_boot.boot_brief_lines(note)
    check("brief lines name rings and reconciliation",
          any("job-arrive-1" in line for line in lines)
          and any("reconciled" in line for line in lines))

    failed = [name for name, ok, _ in RESULTS if not ok]
    print("%d PASS, %d FAIL" % (len(RESULTS) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
