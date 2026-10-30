# OS-056 follow-up: the muse_driver heartbeat bridge (Milo, 2026-10-28)

OS-054 (Pax) landed the driver program and template unit that
OS-056 was waiting on, so this follow-up closes the bridge from
that driver to the watchdog detectors, on fixtures. Drill:
`python3 intel/drills/driver_heartbeat_bridge.py` (transcript:
`intel/evals/driver_heartbeat_bridge.log`, pinning tests:
`tests/test_intel_driver_heartbeat_bridge.py`, 10 tests).

## What was checked

- Template: `os/services/relay-driver@.service` carries
  `Slice=relay-drivers.slice` in its [Service] section, and
  `systemd-analyze verify` accepts the template and the slice
  (exit 0). The slice values are unchanged: CPUQuota=100%,
  MemoryMax=1G.
- Driver: a real `MuseDriver` run against a fixture stand-in
  executable (it prints one line and exits) emits 2 heartbeat
  records: one streamed from the child stdout line, one from an
  explicit `heartbeat()` call. Every record carries
  `line` in the form `PROGRESS:d1 <note>`, `job_id` d1, and a
  numeric `ts`.
- Bridge: the only mapping rule is that a heartbeat ts becomes
  the job's `last_progress_at`, applied to a copy, never by
  mutating the input job. On that rule, a fresh heartbeat (30 s
  old) yields no stall alert; a stale heartbeat with the driver
  nick present yields exactly one progress-stall alert naming
  driver-audio/d1 and no presence-stall; the same stale
  heartbeat with the nick absent yields exactly one
  presence-stall and no progress-stall. Both detectors are the
  unchanged WDG-002/WDG-003 code, and `intel/watchdog.py` still
  mentions no drivers.
- Contract: a full tick on the stale-present snapshot alerts
  but leaves the job claimed, the OS-034 split: the watchdog
  records, systemd restarts.

## What is NOT proven here

- A heartbeat updates progress age only. It does not put the
  driver nick in presence, so a driver that heartbeats but never
  registers presence still reads as a presence-stall when its
  heartbeat goes stale. Presence registration for driver nicks
  is the overseer handoff's job (OS-055), not the driver's.
- A live driver run against a real muse binary (none exists on
  this machine; the stand-in proves driver mechanics only).
- A driver process actually appearing in the slice on a booted
  test image, live cgroup enforcement on this VM, and the kill -9
  systemd restart. Those stay owed on the test image, exactly as
  OS-054 and OS-056 recorded.
- No bus post was made by this work; the drill runs on fixtures
  with no Redis and no network.
