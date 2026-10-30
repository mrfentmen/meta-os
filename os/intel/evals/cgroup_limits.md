# OS-035 cgroup limits

Slice file: os/services/relay-workers.slice. Drill:
intel/drills/cgroup_limits.py. Transcript: cgroup_limits.log.
Pinning tests: tests/test_os_workers_slice.py.

## Values (starting defaults, now the spec record in META_OS.md)

| Setting | Value | Why |
| --- | --- | --- |
| CPUQuota | 100% | One CPU-equivalent per worker; a runaway cannot take every CPU the bus, queue, and dashboard need |
| MemoryMax | 1G | A leak is capped before it threatens the box |

## Basis, stated plainly

The plan names INT-019 load numbers as the tuning source. The
load numbers actually in the repo are wall-clock timings, not
worker resource profiles: Pax INT-006 (snapshot 0.004s, brief
0.009s, tick 0.001s over a 200-job queue and 2000-message room)
and Milo INT-023 (watchdog tick 0.002-0.003s under a failing
200-job queue). Those bound tick cost; they do not measure
worker RSS or CPU, so they cannot tune these values. The values
above are conservative starting defaults, not tuned measurements.
The tuning pass against measured worker RSS and CPU on the test
image is still owed.

## Drill result on this dev VM

| Phase | Result |
| --- | --- |
| file (slice parses, both values exact) | PASS |
| verify (systemd-analyze verify, exit 0) | PASS |
| gate (cpu and memory controllers present) | ENVIRONMENT-BLOCKED |
| enforcement (burner throttled, hog killed) | NOT RUN (gate failed) |

Drill exit code on this host: 2, by design. The enforcement
phase runs only when the gate passes, so a blocked host yields
a blocked verdict, never a faked pass.

## Host block evidence (all observed this run)

- /sys/fs/cgroup/cgroup.controllers is empty; cgroup.subtree_control
  is empty.
- Writing "+cpu +memory" to cgroup.subtree_control fails (exit 1).
- A cgroup directory can be created, but no cpu.max or memory.max
  file appears in it: no cpu or memory controller exists in this
  hierarchy at all.
- Transient scopes do not stay tracked here: a scope running
  "sleep 5" already reads ActiveState=inactive with an empty
  ControlGroup immediately after launch, though its process runs
  (its marker file appears). Transient services fail outright:
  "Failed to connect to bus" (no dbus system bus socket).
- systemd-analyze verify on the slice file passes (exit 0): the
  unit shape is valid even though this host cannot enforce it.

## What is NOT proven here

- A runaway worker throttled by this slice on the test image.
- Bus responsiveness while a worker is throttled (no live bus
  here to measure, and no test image in this repo).
- Attachment: relay-worker@.service (Pax OS-017) is not landed,
  so no worker instance sets Slice=relay-workers.slice yet.
  The drill uses transient units in the slice instead.
- Tuned values: see Basis above.

## Still owed

- OS-017 worker fleet units set Slice=relay-workers.slice.
- Enforcement probe green on the test image (drill exit 0).
- Tuning pass against measured worker RSS/CPU, replacing the
  starting defaults here and in the slice file.
