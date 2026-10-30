# Agent driver contract (OS-053)

A Meta agent does not shell out to a coding agent and hope. It drives
it through an agent driver adapter, the way an OS drives hardware
through a device driver. This file is the contract every driver
implements. The reference implementation is `stub_driver.py` in this
directory. The conformance checklist is `CONFORMANCE.md`.

## The interface

Every driver implements these four operations, with these exact
meanings:

- `start(job_spec)` - launch the agent process against a signed job
  spec: files owned, acceptance checks, attempt budget. The spec
  format is the FND/DSP spec format, unchanged. Starting against an
  unsigned spec is a hard error: the driver spawns nothing.
- `stop()` - terminate the process cleanly. A wedged process is killed
  by the supervisor, never by hand. Stopping a finished process is
  safe and changes nothing.
- `heartbeat()` - emit one progress record in the bus progress
  format, so the watchdog's existing stall detectors work on driver
  processes with zero new detector code. See below.
- `artifacts()` - on exit, return the changed file list, the driver
  log, and a status record the overseer's acceptance layer
  (`mos/acceptance.py`) can verify exactly as it verifies a crew
  worker's job.

## The job spec a driver accepts

A spec is a dict with these fields, all required:

- `id` - the job id, a non empty string.
- `title` - the job title, a non empty string.
- `spec` - the job spec text, a non empty string.
- `files` - the owned file list, a non empty list of non empty
  path strings. Paths are relative to the workdir.
- `accept` - acceptance lines in `mos/acceptance.py` formats
  (`file-exists`, `tests-pass`, `command-ok`, `contains`), parseable
  by `mos/acceptance.parse_accept`. Unparseable accept text is a hard
  error at `start()`, never at verification time.
- `sig` - the job signature, a non empty string. The driver enforces
  presence only. Cryptographic verification of the signature stays
  where it belongs: `jobs.py verify_job` at claim time, against the
  keyring. A driver that verified signatures itself would need the
  keyring in every agent process, which the OS-012 secrets rule
  forbids in spirit: secrets enter once, at firstboot, and stay out
  of agent command lines and process environments that do not need
  them.

Optional spec fields a driver may honor: `max_attempts` (attempt
budget, default 3). A driver ignores fields it does not know rather
than failing on them, so specs stay forward compatible.

## The heartbeat record

One heartbeat is one dict:

- `line` - `PROGRESS:<job_id> <note>`, the exact bus progress
  format `jobs.py` announces. The note is free text.
- `job_id` - the job id.
- `note` - the note text.
- `ts` - Unix time in seconds, when the heartbeat was emitted.

The watchdog keys stall detection on progress age, so a driver that
never heartbeats looks exactly like a wedged worker to the existing
detectors. That is the point: no driver special casing in
`intel/watchdog.py`, proven by the OS-056/OS-057 drills.

## The artifacts record

`artifacts()` returns one dict after the process exits:

- `job_id` - the job id.
- `status` - `done`, `failed`, or `stopped`: `done` when the process
  exited 0, `failed` when it exited nonzero, `stopped` when it was
  terminated by `stop()`.
- `exit_code` - the process exit code, or None if it was killed
  before reporting one.
- `changed_files` - paths under the workdir whose content changed
  during the run, relative paths, sorted. The driver log itself is
  never listed here.
- `unowned_files` - the subset of `changed_files` not in the spec's
  owned `files` list. Reported, never hidden: a driver that touches
  files outside its grant is visible in the record, and the OS-080
  capability layer decides what that means.
- `log` - the path of the driver log file, which holds the child
  process stdout and stderr verbatim.
- `acceptance` - the `mos/acceptance.verify` result for the spec's
  accept lines against the workdir: `{"ok": bool, "results": [...]}`.
  Acceptance is computed from the workdir on disk, not from anything
  the agent process claims about itself.

## What a driver never does

- Never posts to the bus itself. Heartbeat records go to a sink the
  caller supplies (in the stub driver, an in memory list by default).
  Posting is an outward action; it happens only through a path Dale's
  rules approve, never as a driver side effect.
- Never restarts itself, never reclaims a job, never touches a job
  record. Process death belongs to systemd under the OS-034 contract;
  silent-but-alive failure belongs to the watchdog; reassignment
  belongs to the overseer through the OS-125 baton pass. A driver
  that did any of those would fight all three.
- Never puts a secret on its command line or in a log. The stub
  driver takes no secret at all.

## Supervision

Driver processes are first class citizens, identical in standing to
`relay-worker@` instances: each runs as a systemd unit in
`relay-drivers.slice` (OS-056) under the same supervision contract
(systemd owns process death; the watchdog owns silent stalls), under
per process cgroup limits, with every action in journald and the bus
record. The per driver systemd template is owed with the driver
runner programs (OS-054 and later); the slice already exists.

## Status of this contract (first light, OS-053)

Landed here: this contract, the stub driver, the conformance
checklist, and pinning tests that run the checklist against the stub.
OS-054 adds the Muse Code driver (muse_driver.py), its runner
(run_driver.py), and the relay-driver@.service template, with
pinning tests that run the checklist against the driver using a
fixture stand-in executable in place of the `muse` binary.

Still owed, stated plainly, not hidden:

- A live run on the test image (no test image in this repo yet), so
  the acceptance line "the driver passes every checklist item
  on the test image" is met on a developer machine only, not on
  Meta OS itself.
- The overseer handoff (OS-055) that writes a driver spec file
  and consumes the artifacts JSON back into the queue.
- The checklist run against a real `muse` binary: OS-054 proves
  the driver mechanics against a fixture stand-in executable
  (tests/test_os_driver_muse.py); the `muse exec --prompt-file`
  argv shape is the documented headless form, not a shape proven
  against a live CLI here, and no approval bypass flag is passed.
