# OS-057: driver stall drill (Milo, 2026-10-27)

OS-057's acceptance, proven as far as fixtures can prove it: wedge
a driver process (alive, heartbeat stale); the watchdog raises the
same STALL alert as for a crew worker and the driver is restarted
per contract without touching other drivers.

## What landed

- Drill `intel/drills/driver_stall.py`, transcript
  `intel/evals/driver_stall.log`: detector phase (a driver nick in
  caps, present, holding a claimed job with no progress past the
  production progress-stall window yields exactly one
  progress-stall alert naming driver-audio and job d1, severity
  critical, age 10m; the same snapshot yields no presence-stall,
  so the wedged driver is never double-alerted; fresh drivers
  yield nothing; watchdog.py contains no driver special-casing),
  worker-equivalence phase (the same wedge on worker pax fires
  the same progress-stall alert, critical, naming pax/w1),
  demo-profile phase (a subprocess under
  WATCHDOG_PROGRESS_STALL_MINUTES=1, the value in
  intel/metaos-demo.env, fires the wedge at 61s and stays quiet
  at 30s), and contract phase (a full tick alerts once for the
  wedged driver, leaves both driver jobs claimed by their
  drivers, and leaves the sibling driver unalerted).
- Pinning tests `tests/test_intel_driver_stall.py` (9 tests):
  drill presence and phases, spec record, detector behavior on
  the fixture snapshot, worker equivalence, demo-profile
  subprocess behavior, tick contract, and the no-em-dash rule
  on the new files.
- Spec record in `plan/META_OS.md`, next to the OS-056 paragraph:
  the wedge detector, the demo-threshold result, the contract
  half, and the owed items.

## NOT proven here

- A wedged driver actually restarted by systemd on a booted test
  image: no test image exists in this repo, and no driver runner
  program exists yet for a template unit to start, so the
  restart itself is systemd's job under the OS-034 contract and
  is owed on the test image exactly as OS-056's kill -9 restart
  was.
- A live sibling driver kept running through a real restart:
  proven here only at the watchdog level, where the tick leaves
  the sibling job claimed, unalerted, and untouched.
- Tuned limits: nothing in this drill retunes the OS-056 slice
  values; driver RSS and CPU profiles on the test image are
  still owed.
