# OS-038 eval: demo thresholds drop-in

Task: OS-038 — metaos-demo.env loaded by a unit drop-in on the
demo image, separate from production thresholds, no code edits.

## What landed

- `os/services/relay-watchdog.service.d/demo-thresholds.conf`:
  `[Service]` + `EnvironmentFile=/opt/relay/intel/metaos-demo.env`
  only. No `ExecStart`, so the production command
  (`intel/watchdog.py --loop --room main --beat`, OS-033) runs
  exactly as shipped. The path is the image path: build-image.sh
  rsyncs the whole repo to `/opt/relay`, so the DEM-013 profile
  file arrives there with the payload, not from a separate copy.
- `os/build-image.sh`: installs the drop-in only when
  `METAOS_DEMO=1`. A production build (the default) never
  installs it, so production thresholds come from
  `intel/thresholds.py` defaults alone.
- Strict `EnvironmentFile` (no `-` prefix) on purpose: a demo
  image missing its profile fails loudly at unit start instead
  of silently demoing with 10-minute windows while the Shot 8
  catch never fires.
- Drill: `intel/drills/demo_thresholds_dropin.py` (OS-038: PASS).
  Transcript: `intel/evals/demo_thresholds_dropin.log`.
- Pinning tests: 4 new tests in
  `tests/test_intel_watchdog_service.py`
  (`WatchdogDemoThresholdsDropinTest`).

## Measured results (drill, 2026-10-27)

- Drop-in shape: PASS (env-only, correct image path).
- Demo profile in a subprocess: stall 1, progress-stall 1, all
  other values at production defaults (lease 5/2, dedupe 30,
  silent-room 60, beat 300, page 1000/1000).
- Production untouched: base unit has no `EnvironmentFile`;
  INT-021 tournament 3/3 clean in 0.15 s with no `WATCHDOG_*`
  variables set.
- `systemd-analyze verify` on the unit file emitted no
  diagnostics for the watchdog unit (host-only noise otherwise).
- Full suite: 1305 tests, only the 2 known pre-existing
  environmental failures (boss_trigger loader, bustools parity)
  — identical to the OS-037 baseline plus the 4 new tests.

## NOT proven here (owed on the demo image)

- Boot activation of the drop-in on a demo image, and the
  dashboard render under the demo profile: there is no test
  image in this repo, so a booted demo image is the only thing
  that proves those. The drop-in file says so in its header,
  and this note says so here, so neither is claimed from a
  file in the repo.
