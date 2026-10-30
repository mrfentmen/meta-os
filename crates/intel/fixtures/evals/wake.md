# OS-119 eval: Muse wake adapter (Milo)

Module: `intel/wake.py`. Drill:
`intel/drills/wake.py` (6/6 phases PASS).
Tests: `tests/test_intel_wake.py` (14 tests).

What was proven on fixtures:

- A sleeping fixture agent, given a posted job and
  zero human contact, wakes, claims, and starts
  work with the bundle in place: one tick yields
  exactly one wake record whose bundle carries the
  goal, the spec text, the acceptance checks, the
  files, and the mind image reference. The fake
  Muse runtime starts a session with that bundle,
  and the session's first bus action is claim, never
  status. A session started with no bundle polls
  status instead, which proves the bundle is what
  makes the wake a wake rather than a poll.
- A job addressed to a different agent does not
  wake this one: cross-addressed pairs yield zero
  wake records and no session starts, in both
  directions.
- An awake agent needs no wake, and a sleeping
  agent whose runtime is not muse is not this
  adapter's wake. Both yield zero wake records, as
  does a record with no runtime at all: missing
  evidence is never read as permission to wake a
  stranger.
- Dedupe is per job and agent pair, not per agent:
  a second tick over the same pair journals nothing
  new, while a second job addressed to the same
  sleeping agent earns a second wake record with
  its own dedupe key.
- A job with no mind image reference still wakes
  and claims, but its bundle carries mind_image
  None plus a note naming the OS-102 loader as
  pending. The gap is visible in the bundle, not
  hidden by an invented reference.
- The tick never mutates its jobs, agents, or
  journal, malformed inputs yield no records and
  no crash, and the module imports no socket, bus,
  or network module, so nothing here can ring a
  phone or post to the bus on its own.

What is NOT proven here:

- A live Muse session actually started: the start
  in the drill is applied by a fake runtime, not
  through a live Muse runtime's session mechanism,
  and no booted test image runs in this repo.
- The bell actually ringing: the resident watchman
  that rings is Pax OS-118, not this module.
- A mind image actually loaded: the OS-102 loader
  has not landed, so bundles without a reference
  say so plainly, and bundles with a reference
  carry the reference through without loading it.
- A wake on a booted test image, or a wake of a
  real sleeping Hana or Rowan instance: both need
  the live halves above, and are not claimed here.

Related: the watchman whose bell this adapter
answers is OS-118 (Pax), the ladder a wake feeds
into on failure is OS-095, the gate at the end of
that ladder is OS-096, and the baton a reassign
would hand the next worker is OS-125.
