# OS-129 eval: watchman state after reboot (Milo verification note)

This file is Milo's verification note on the OS-129 drill,
filed separately from Buffy's OS-126 run log, as the lane
task requires.

## What was built

- `intel/watchman_boot.py`: pure computation of the first
  post-boot ring set from queue claims and leases only.
  No counter argument exists on any function, and no
  function reads a stored counter, so the stale-counter
  drift failure mode is designed out rather than patched.
- `intel/drills/watchman_boot.py`: 15 checks, all PASS.
- Pinning tests: `tests/test_intel_watchman_boot.py`.

## What the drill proves

- Two open jobs posted during the downtime window ring
  with reason arrived_during_downtime; a job posted
  before the window and a job posted after boot do not.
- A claimed job whose lease died inside the window rings
  with reason lease_expired_during_downtime; a claimed
  job with a live lease does not; a done job never rings.
- No double ring: the same job listed twice rings once,
  and a second post-boot cycle with the first cycle's
  rung ids in the ledger rings nothing new.
- A corrupted stored counter value (999999, and -42 in
  the counter-proof path) yields the identical ring set:
  the watchman never reads a counter, so a corrupted one
  changes nothing.
- Sweep reconciliation: with a sweep record requeuing
  exactly the lease-expired ring id, the verification
  note reports reconciled True with counts 3 total, 2
  arrived, 1 lease-expired. With a sweep record that
  drops the requeue and adds a stranger, the note
  reports reconciled False and names the missing and
  extra ids, never a fudged count.
- Inputs are never mutated, the note carries no push and
  no announcement field, and the module imports no push
  module: verification alone can never contact Dale.

## What is NOT proven here

- A live watchman ringing on a booted test image: no
  test image runs in this repo, and the mechanical half
  (the resident watchman program that actually rings)
  is Pax OS-118, not this module.
- A real power cut and reboot: the drill runs on
  fixtures with a fake clock, not on a killed machine.
- The OS-126 plug-pull drill itself: that run log is
  Buffy's file, not this note. This note verifies the
  ring computation and its sweep reconciliation only.
- The cross-machine case (a job addressed to a machine
  other than the booting one) is out of scope for this
  verification: the ring set here is per-machine queue
  state, and machine addressing belongs to the watchman
  itself (OS-118).
