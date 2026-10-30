# OS-056: driver supervision integration (Milo, 2026-10-27)

OS-056's acceptance, proven as far as fixtures can prove it: driver
processes run as systemd units in a relay-drivers.slice under the
OS-034 contract (systemd owns process death; the watchdog owns
silent stalls), and driver heartbeats feed the existing WDG stall
detectors unchanged.

## What landed

- `os/services/relay-drivers.slice`: the driver cgroup slice, kept
  separate from relay-workers.slice so a runaway driver cannot eat
  the worker budget and vice versa. Starting defaults shared with
  OS-035: CPUQuota=100%, MemoryMax=1G. The per-driver template unit
  joins it with Slice=relay-drivers.slice when the driver runner
  program lands; the slice needs no Install section, systemd
  creates it on demand.
- Drill `intel/drills/driver_supervision.py`, transcript
  `intel/evals/driver_supervision.log`: file phase (slice values),
  verify phase (systemd-analyze verify exit 0), detector phase (a
  driver nick gone from presence with a claimed job past the stall
  window yields exactly one presence-stall alert naming the driver
  and job, severity critical; present and fresh cases yield
  nothing; watchdog.py contains no driver special-casing), and
  contract phase (a full tick alerts but leaves the job claimed
  with the driver, so the watchdog cannot fight systemd over a
  restart).
- Pinning tests `tests/test_intel_driver_supervision.py` (7 tests):
  slice values, META_OS.md record, drill presence and phases,
  detector behavior on the fixture snapshot, and the no-em-dash
  rule on the new files.
- Spec record in `plan/META_OS.md`, next to the OS-035 paragraph:
  slice filename, defaults, join instruction, and the owed items.

## NOT proven here

- A driver process appearing in this slice on the test image: no
  test image exists in this repo, and no driver runner program
  exists yet for a template unit to start, so the template unit
  itself is owed with the driver programs, not invented here.
- Live cgroup enforcement on this dev VM: its cgroup hierarchy
  exposes no cpu or memory controller, so enforcement is owed on
  the test image exactly as OS-035's was.
- The kill -9 restart itself: that is systemd's job under the
  OS-034 contract, and it is owed on the test image with the
  driver units. The wedge case (driver alive, heartbeat stale) is
  OS-057's drill, not this one; the detector phase here proves
  the presence-stall half only.
- Tuned limits: the 100%/1G values are the OS-035 starting
  defaults, not measured driver profiles; tuning against driver
  RSS and CPU on the test image is still owed.
