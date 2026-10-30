"""intel/drills/wake.py -- OS-119 drill (Milo).

Acceptance: a sleeping fixture agent, given a
posted job and zero human contact, wakes, claims,
and starts work with the bundle in place. Its first
bus action is the claim or progress on that job,
not a status check. A job addressed to a different
agent does not wake it.

What fixtures can prove, and what they cannot,
stated plainly. The module (intel/wake.py) judges
fixture job and agent records and composes the
bundle; it never starts a real session, never
touches a process, and never posts to the bus.
The drill's fake Muse runtime applies the start,
so the session-start half is simulated, not a
session started through a live Muse runtime. The
resident watchman that actually rings is Pax
OS-118, and the mind image loader is OS-102, which
has not landed: a bundle whose job carries no mind
image reference says the loader is pending instead
of inventing a reference. No booted test image
runs in this repo, so a live wake on a booted
image is not claimed here.

Phases, all on fixtures with a fake clock (base
time T0):

- wake-and-claim: sleeping agent hana on machine
  hana-box, job job-1 addressed to hana with a
  spec, acceptance checks, and a mind image
  reference. One tick yields exactly one wake
  record whose bundle carries the goal, the spec,
  the acceptance checks, and the mind image
  reference. The fake runtime starts a session
  with that bundle, and the session's first bus
  action is claim, never status. A session started
  with no bundle polls status instead, and the
  drill proves that shape fails the first-act rule,
  so the bundle is what makes the wake a wake.
- wrong-addressee: a job addressed to rowan does
  not wake hana, and a job addressed to hana does
  not wake rowan. Cross-addressed pairs yield zero
  wake records, and neither fake session starts.
- awake-and-other-runtime: an awake hana needs no
  wake, and a sleeping agent whose runtime is not
  muse is not this adapter's wake. Both yield zero
  wake records.
- dedupe-and-second-job: a second tick over the
  same job and agent yields nothing new, but a
  second job addressed to the same sleeping agent
  yields a second wake record with its own dedupe
  key. Dedupe is per pair, not per agent.
- no-mind-image-honesty: a job with no mind image
  reference still wakes and claims, but its bundle
  carries mind_image None plus a note naming the
  OS-102 loader as pending. The gap is visible in
  the bundle, not hidden.
- malformed-and-immutable: malformed jobs, agents,
  and journal entries yield no records and no
  crash; the tick leaves its inputs unchanged; the
  module's imports contain no socket, bus, or
  network module, and the drill's sent ledger
  stays empty, so nothing here can ring a phone.

Pass bar: 6/6 phases PASS, zero human contact in
every phase, first bus action claim in every start
that uses a bundle.
"""

import ast
import copy
import os
import sys

sys.path.insert(0, ".")

from intel import wake  # noqa: E402

T0 = 100000
SENT = []


def check(name, ok, detail=""):
    """One phase line. Returns ok for the tally."""
    if ok:
        print("%s: PASS" % name)
    else:
        print("%s: FAIL %s" % (name, detail))
    return ok


class FakeMuseRuntime:
    """A fixture Muse runtime. start(bundle) opens a
    session whose first bus action is the claim of
    the bundled job, or a status poll when started
    with no bundle. The session never touches a
    real runtime, bus, or network."""

    def __init__(self):
        self.sessions = []

    def start(self, bundle):
        if bundle is None:
            session = {"bundle": None, "first_bus_action": "status",
                       "claimed_job": None, "progress": []}
        else:
            session = {"bundle": copy.deepcopy(bundle),
                       "first_bus_action": "claim",
                       "claimed_job": bundle.get("job_id"),
                       "progress": ["started job %s"
                                    % bundle.get("job_id")]}
        self.sessions.append(session)
        return session


def hana_agent(asleep=True, runtime="muse"):
    return {"nick": "hana", "machine": "hana-box",
            "runtime": runtime, "asleep": asleep}


def rowan_agent(asleep=True, runtime="muse"):
    return {"nick": "rowan", "machine": "rowan-box",
            "runtime": runtime, "asleep": asleep}


def job(job_id, addressed_to, mind_image=True):
    record = {"id": job_id, "addressed_to": addressed_to,
              "goal": "Write the watchdog brief line",
              "spec": "Goal: Write the watchdog brief line\n"
                      "Steps: draft, check, file",
              "acceptance_checks": ["brief line names the alert",
                                    "brief line names the machine"],
              "files": ["intel/brief.py"]}
    if mind_image:
        record["mind_image_ref"] = "mind/hana-base-v3"
    return record


def phase_wake_and_claim():
    agent = hana_agent()
    posted = job("job-1", "hana")
    new = wake.wake_tick([posted], [agent], [], T0)
    if len(new) != 1 or new[0]["kind"] != "wake":
        return check("wake-and-claim", False,
                     "tick yielded %d records" % len(new))
    bundle = new[0]["bundle"]
    if bundle["goal"] != "Write the watchdog brief line":
        return check("wake-and-claim", False, "bundle goal wrong")
    if bundle["spec"] is None or "Goal:" not in bundle["spec"]:
        return check("wake-and-claim", False, "bundle spec missing")
    if bundle["acceptance_checks"] != ["brief line names the alert",
                                       "brief line names the machine"]:
        return check("wake-and-claim", False, "bundle checks wrong")
    if bundle["mind_image"] != "mind/hana-base-v3":
        return check("wake-and-claim", False, "bundle mind image wrong")
    runtime = FakeMuseRuntime()
    session = runtime.start(bundle)
    if session["first_bus_action"] != "claim":
        return check("wake-and-claim", False,
                     "first bus action was %s"
                     % session["first_bus_action"])
    if session["claimed_job"] != "job-1":
        return check("wake-and-claim", False, "session claimed wrong job")
    if session["progress"] != ["started job job-1"]:
        return check("wake-and-claim", False, "session progress wrong")
    polling = runtime.start(None)
    if polling["first_bus_action"] != "status":
        return check("wake-and-claim", False,
                     "a bundle-free start did not poll status")
    if wake.brief_lines(new) != ["Wake: hana woken for job job-1 "
                                 "on hana-box"]:
        return check("wake-and-claim", False, "brief line wrong")
    return check("wake-and-claim", True)


def phase_wrong_addressee():
    hana = hana_agent()
    rowan = rowan_agent()
    for posted, agents, label in (
            (job("job-1", "rowan"), [hana], "rowan job woke hana"),
            (job("job-1", "hana"), [rowan], "hana job woke rowan")):
        new = wake.wake_tick([posted], agents, [], T0)
        if new:
            return check("wrong-addressee", False, label)
        runtime = FakeMuseRuntime()
        if runtime.sessions:
            return check("wrong-addressee", False,
                         "a session started without a wake")
    return check("wrong-addressee", True)


def phase_awake_and_other_runtime():
    posted = job("job-1", "hana")
    awake = hana_agent(asleep=False)
    if wake.wake_tick([posted], [awake], [], T0):
        return check("awake-and-other-runtime", False,
                     "an awake agent woke")
    other = hana_agent(runtime="freebuff")
    if wake.wake_tick([posted], [other], [], T0):
        return check("awake-and-other-runtime", False,
                     "a non-muse runtime woke")
    unknown = {"nick": "hana", "machine": "hana-box", "asleep": True}
    if wake.wake_tick([posted], [unknown], [], T0):
        return check("awake-and-other-runtime", False,
                     "a runtime-free record woke")
    return check("awake-and-other-runtime", True)


def phase_dedupe_and_second_job():
    agent = hana_agent()
    first = job("job-1", "hana")
    journal = wake.wake_tick([first], [agent], [], T0)
    if len(journal) != 1:
        return check("dedupe-and-second-job", False,
                     "first tick yielded %d" % len(journal))
    if wake.wake_tick([first], [agent], journal, T0):
        return check("dedupe-and-second-job", False,
                     "second tick re-woke the same pair")
    second = job("job-2", "hana")
    new = wake.wake_tick([first, second], [agent], journal, T0)
    if len(new) != 1 or new[0]["job"] != "job-2":
        return check("dedupe-and-second-job", False,
                     "second job yielded %d records" % len(new))
    if new[0]["dedupe_key"] != "wake:job-2:hana":
        return check("dedupe-and-second-job", False,
                     "dedupe key wrong")
    return check("dedupe-and-second-job", True)


def phase_no_mind_image_honesty():
    agent = hana_agent()
    posted = job("job-1", "hana", mind_image=False)
    new = wake.wake_tick([posted], [agent], [], T0)
    if len(new) != 1:
        return check("no-mind-image-honesty", False,
                     "tick yielded %d records" % len(new))
    bundle = new[0]["bundle"]
    if bundle["mind_image"] is not None:
        return check("no-mind-image-honesty", False,
                     "bundle invented a mind image")
    note = bundle.get("mind_image_note") or ""
    if "OS-102" not in note or "pending" not in note:
        return check("no-mind-image-honesty", False,
                     "bundle note does not name OS-102 pending")
    runtime = FakeMuseRuntime()
    session = runtime.start(bundle)
    if session["first_bus_action"] != "claim":
        return check("no-mind-image-honesty", False,
                     "first bus action was not claim")
    return check("no-mind-image-honesty", True)


def phase_malformed_and_immutable():
    jobs = [None, "not-a-job", {"id": "job-1"},
            {"addressed_to": "hana"}, job("job-1", "hana")]
    agents = [None, "not-an-agent", {"nick": "hana"},
              hana_agent()]
    jobs_before = copy.deepcopy(jobs)
    agents_before = copy.deepcopy(agents)
    journal = ["not-a-record", {"kind": "wake"}]
    journal_before = copy.deepcopy(journal)
    new = wake.wake_tick(jobs, agents, journal, T0)
    if len(new) != 1 or new[0]["job"] != "job-1":
        return check("malformed-and-immutable", False,
                     "malformed tick yielded %d records" % len(new))
    if jobs != jobs_before or agents != agents_before:
        return check("malformed-and-immutable", False,
                     "tick mutated jobs or agents")
    if journal != journal_before:
        return check("malformed-and-immutable", False,
                     "tick mutated the journal")
    if wake.wake_tick(None, None, None, T0):
        return check("malformed-and-immutable", False,
                     "None inputs yielded records")
    module_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "..", "wake.py")
    with open(os.path.normpath(module_path)) as handle:
        tree = ast.parse(handle.read())
    banned = {"socket", "urllib", "requests", "redis", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
            if names & banned:
                return check("malformed-and-immutable", False,
                             "module imports a banned module")
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in banned:
                return check("malformed-and-immutable", False,
                             "module imports a banned module")
    if SENT:
        return check("malformed-and-immutable", False,
                     "sent ledger is not empty")
    return check("malformed-and-immutable", True)


def main():
    phases = [phase_wake_and_claim,
              phase_wrong_addressee,
              phase_awake_and_other_runtime,
              phase_dedupe_and_second_job,
              phase_no_mind_image_honesty,
              phase_malformed_and_immutable]
    results = [phase() for phase in phases]
    print("%d/%d phases PASS" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
