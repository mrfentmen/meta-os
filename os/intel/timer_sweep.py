"""intel/timer_sweep.py -- timer fallback sweep (OS-121, Milo).

Every agent runtime also wakes on a slow timer to sweep
the board and claim anything the bell missed: shift
worker clock in as the safety net under the bell, so a
missed wake delays work by minutes, never forever.

Rules, all pure functions of queue state:

- The sweep is dormant while the watchman is healthy.
  When watchman_alive is True the tick runs but claims
  nothing: the bell owns claiming while it lives, and a
  sweep that also claimed would double claim the same
  job. The acceptance for the healthy case is exactly
  this: zero claims, zero duplicates.
- When watchman_alive is False the sweep claims. A job
  posted at time t is claimed by the first sweep tick at
  or after t, and ticks run every sweep interval, so a
  posted job is claimed within one sweep interval of
  posting. That is the timing guarantee the drill proves.
- When watchman_alive is None (unknown) the sweep holds
  and claims nothing. Missing evidence is never read as
  a dead watchman: claiming on unknown state could
  double claim against a watchman that is alive but
  unreported. The watchdog (OS-122) owns flagging the
  unknown watchman; the sweep does not guess.
- Lease discipline holds across both paths. The sweep
  only ever claims open jobs. A claimed job is never
  re-claimed, whatever the watchman state: the lease
  sweep (OS-129) owns requeueing dead leases, not this
  module. A done job is never claimed. A job id already
  in the sweep ledger (claimed by an earlier sweep) is
  never claimed again, so repeated sweeps produce zero
  duplicate claims even when the watchman stays dead.
- Addressing holds. A job addressed to an agent outside
  the local roster is never claimed by this machine's
  sweep: it belongs to another machine's agents, and
  claiming it here would be work exchanged with the
  wrong machine. A job with no addressed agent is never
  claimed either: routing an unaddressed job belongs to
  the watchman, and the sweep must not invent a worker
  for it. Both cases are reported in skipped, never
  silently dropped.
- Cadence: a tick before last_sweep_at plus the
  interval does not run (ran False, no claims, no
  ledger change). The first tick, with no last sweep
  recorded, always runs. The interval defaults to
  TIMER_SWEEP_INTERVAL_SECONDS from thresholds (300),
  env-overridable there, never hardcoded here.
- Malformed records (not a dict, no id, no usable
  posted time for an open job) never claim and never
  crash: an absent subject is not a subject to claim.
- Inputs are never mutated: the ledger passed in is
  left alone, and the note carries the ledger after the
  tick so the caller can chain ticks honestly.

This module is decision only. It never starts a
session, never rings a bell, never moves a claim in a
live queue, and never posts to the bus: it computes
the claim set a correct timer sweep must produce from
fixture queue state. The mechanical half (the runtime
timer that actually wakes an agent) is outside this
repo's fixture layer, and a live sweep on a booted test
image is not claimed here, because no test image runs
in this repo.

Usage: sweep_cycle(jobs, now, watchman_alive,
sweep_interval_seconds, last_sweep_at, sweep_ledger,
local_agents) returns the tick note dict (with its
claims and its brief lines via sweep_brief_lines(note)).
"""

from intel import thresholds

__all__ = ["sweep_cycle", "sweep_brief_lines",
           "default_interval_seconds"]


def default_interval_seconds():
    """The OS-121 sweep interval from thresholds."""
    return thresholds.TIMER_SWEEP_INTERVAL_SECONDS


def _num(value):
    """An int/float timestamp, else None. Bools are not times."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _job_id(job):
    if not isinstance(job, dict):
        return None
    job_id = job.get("id")
    if isinstance(job_id, str) and job_id.strip():
        return job_id.strip()
    return None


def sweep_cycle(jobs, now, watchman_alive,
                sweep_interval_seconds=None,
                last_sweep_at=None, sweep_ledger=None,
                local_agents=None):
    """One timer sweep tick over fixture queue state.

    jobs: iterable of job records. now: the tick time.
    watchman_alive: True (healthy), False (dead), or
    None (unknown). sweep_interval_seconds: seconds
    between ticks; None means the thresholds default.
    last_sweep_at: the previous tick time; None means
    this is the first tick. sweep_ledger: job ids already
    claimed by earlier sweeps. local_agents: the roster
    of agents on this machine; None means no roster was
    supplied, and then no job is claimed (routing without
    a roster would invent a worker).

    Returns a note dict: ran, reason, claims (each
    {"job_id", "claimed_by", "claimed_at", "via"}),
    skipped (each {"job_id", "reason"}), next_sweep_at,
    and sweep_ledger_after (the ledger after this tick).
    """
    interval = sweep_interval_seconds
    if interval is None:
        interval = default_interval_seconds()
    if not isinstance(interval, (int, float)) or interval <= 0:
        interval = default_interval_seconds()
    ledger = set(sweep_ledger or [])
    ledger_after = sorted(ledger)
    if last_sweep_at is not None:
        due_at = last_sweep_at + interval
        if now < due_at:
            return {
                "ran": False,
                "reason": "sweep not due until %s" % due_at,
                "claims": [],
                "skipped": [],
                "next_sweep_at": due_at,
                "watchman_alive": watchman_alive,
                "sweep_ledger_after": ledger_after,
            }
    next_sweep_at = now + interval
    if watchman_alive is True:
        return {
            "ran": True,
            "reason": "watchman healthy, sweep dormant",
            "claims": [],
            "skipped": [],
            "next_sweep_at": next_sweep_at,
            "watchman_alive": True,
            "sweep_ledger_after": ledger_after,
        }
    if watchman_alive is None:
        return {
            "ran": True,
            "reason": "watchman state unknown, sweep holds",
            "claims": [],
            "skipped": [],
            "next_sweep_at": next_sweep_at,
            "watchman_alive": None,
            "sweep_ledger_after": ledger_after,
        }
    roster = set(local_agents or [])
    claims = []
    skipped = []
    seen = set()
    for job in jobs or []:
        job_id = _job_id(job)
        if job_id is None or job_id in seen:
            continue
        seen.add(job_id)
        status = job.get("status") if isinstance(job, dict) else None
        if status != "open":
            if status in ("claimed", "done"):
                skipped.append({"job_id": job_id,
                                "reason": "not open (%s)" % status})
            continue
        if job_id in ledger:
            skipped.append({"job_id": job_id,
                            "reason": "already swept"})
            continue
        posted_at = _num(job.get("posted_at"))
        if posted_at is None or posted_at > now:
            continue
        addressed_to = job.get("addressed_to")
        if not isinstance(addressed_to, str) or not addressed_to.strip():
            skipped.append({"job_id": job_id,
                            "reason": "unaddressed, routing belongs "
                            "to the watchman"})
            continue
        addressed_to = addressed_to.strip()
        if addressed_to not in roster:
            skipped.append({"job_id": job_id,
                            "reason": "addressed elsewhere"})
            continue
        claims.append({
            "job_id": job_id,
            "claimed_by": addressed_to,
            "claimed_at": now,
            "via": "timer_sweep",
        })
        ledger_after.append(job_id)
    ledger_after = sorted(set(ledger_after))
    return {
        "ran": True,
        "reason": "watchman dead, sweep claiming",
        "claims": claims,
        "skipped": skipped,
        "next_sweep_at": next_sweep_at,
        "watchman_alive": False,
        "sweep_ledger_after": ledger_after,
    }


def sweep_brief_lines(note):
    """Brief lines for a sweep tick note."""
    if not note["ran"]:
        return ["timer sweep: %s" % note["reason"]]
    lines = ["timer sweep: %s, %d claim(s)"
             % (note["reason"], len(note["claims"]))]
    for claim in note["claims"]:
        lines.append("sweep claimed %s for %s at %s"
                     % (claim["job_id"], claim["claimed_by"],
                        claim["claimed_at"]))
    for skip in note["skipped"]:
        lines.append("sweep skipped %s: %s"
                     % (skip["job_id"], skip["reason"]))
    lines.append("next sweep at %s" % note["next_sweep_at"])
    return lines
