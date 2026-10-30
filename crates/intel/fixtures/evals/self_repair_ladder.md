# OS-095: the self-repair ladder (Milo, 2026-10-27)

OS-095's acceptance, proven on fixtures: three staged stalls
(unresponsive worker, dead worker, job held by the wrong
worker) are each resolved by the correct rung with zero
Dale contact, and every ladder action appears in the
journal and the next brief.

The ladder (intel/ladder.py) is the watchdog's judgment,
not its hands. Rung selection is a pure function of
snapshot facts: a registered worker that is present but
stale gets nudge, a registered worker absent from presence
gets restart, and a claimer outside the caps registry gets
reassign with a baton (title, deposited progress, files).
The drill (intel/drills/self_repair_ladder.py, transcript
intel/evals/self_repair_ladder.log) runs six phases, all
PASS:

- nudge: present worker pax, stale job 7, WDG-003 alert
  -> one nudge record, journal and brief line agree.
- restart: absent worker pax, stale job 7, WDG-002 alert
  -> one restart record; the job stays claimed by pax
  after the tick, and the simulated systemd restart note
  (severity info, kind worker-restart) is the restart half.
- reassign: walk-on ghost claims job 9 -> one reassign
  record carrying the baton exactly; the simulated
  overseer moves the claim to hana with progress and files
  unchanged, so no work repeats.
- idempotent: a second tick over the same stalls journals
  nothing new (dedupe key ladder:<job>:<rung>).
- no-dale: the journal holds only ladder-action records,
  the drill's push ledger stays empty, and the ladder
  module has no push or announcement path at all.
- immutable: a ladder tick leaves its input snapshot
  unchanged, so the ladder cannot fight systemd over a
  restart or steal a live worker's claim (the OS-034
  split, in code).

Pinning tests: tests/test_intel_self_repair_ladder.py (11
tests: each rung, malformed stall, missing job record,
idempotency, brief line, baton exactness, snapshot
immutability, no push surface, drill/eval/spec files
present, no em dash in the new files).

NOT proven here: a live worker actually nudged back to
work, a real systemd restart on a booted test image (no
test image in this repo, worker runner units owed to Pax),
a live overseer reassign, the watchman's mechanical
execution of the rungs (Pax OS-118), or the escalation
when every rung is spent (that is OS-096, owed after this
one). The decision, journal, brief, and zero-Dale-contact
halves are proven here; the live halves wait on the test
image and the watchman.
