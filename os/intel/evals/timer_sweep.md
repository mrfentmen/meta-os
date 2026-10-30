# OS-121 eval: timer fallback sweep (Milo)

Every agent runtime also wakes on a slow timer to sweep
the board and claim anything the bell missed, so a
missed wake delays work by minutes, never forever.

## What was built

- `intel/timer_sweep.py`: pure computation of one
  timer sweep tick from fixture queue state. The sweep
  is dormant while the watchman is healthy (zero claims,
  zero duplicates), claims open jobs addressed to the
  local roster when the watchman is dead, and holds
  (claims nothing) when watchman state is unknown.
  Lease discipline holds across both paths: claimed and
  done jobs are never re-claimed, and a job id in the
  sweep ledger is never claimed again. Outsider
  addressed and unaddressed jobs are never claimed and
  are reported in skipped, never silently dropped. The
  interval defaults to TIMER_SWEEP_INTERVAL_SECONDS
  from thresholds (300, env-overridable), a tick before
  last sweep plus interval does not run, and inputs are
  never mutated.
- `intel/drills/timer_sweep.py`: 20 checks, all PASS.
- Pinning tests: `tests/test_intel_timer_sweep.py`
  (14 tests).
- Threshold: TIMER_SWEEP_INTERVAL_SECONDS added to
  `intel/thresholds.py` (default 300, env
  WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS). It is not
  part of the INT-022 locked set, because the timer
  fallback did not exist at lock time.

## What the drill proves

- With the watchman dead, a job posted at 100 is
  claimed at the 300 tick (delay 200) and a job posted
  at 550 at the 600 tick (delay 50): every claim lands
  within one sweep interval of posting.
- With the watchman healthy, the same jobs across the
  same ticks yield zero claims and an empty ledger, so
  repeated sweeps produce zero duplicate claims.
- With watchman state unknown, the sweep holds and
  claims nothing: missing evidence is never read as a
  dead watchman.
- A claimed job is never re-claimed even with the
  watchman dead; a done job is never claimed; repeat
  sweeps with a dead watchman claim nothing new.
- A job addressed to an outsider is never claimed by
  this machine's sweep, and an unaddressed job is never
  claimed (routing it would invent a worker).
- A tick before last sweep plus interval does not run;
  a future job is never claimed early; a duplicate input
  is claimed once; malformed records never claim and
  never crash.
- Inputs are never mutated, the note carries no push and
  no announcement field, and the module imports no push
  module.

## What this does NOT claim

- A live agent actually woken by a timer, a live bell
  missed and recovered on a booted test image (no test
  image runs in this repo), or the resident watchman
  itself (Pax OS-118). This is the decision layer on
  fixtures only, not the runtime timer mechanism.
- The unknown-watchman hold is deliberate, not a gap
  filled by guessing: flagging an unknown watchman is
  the watchdog's job (OS-122), and the sweep must not
  double claim against a watchman that is alive but
  unreported.
