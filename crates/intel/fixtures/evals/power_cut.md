# OS-040 power-cut drill — eval

Drill: `intel/drills/power_cut.py` (exit 0, 29 PASS lines).
Transcript: `intel/evals/power_cut.log`.
Pinning tests: `tests/test_os_power_cut.py` (4 tests).

## Result: 3 of 3 runs recover, zero manual fixes

| Run | Cut state | Reboot tick | Sweep | Boot brief line | Reclaim |
| --- | --- | --- | --- | --- | --- |
| pax / job 7 | claimed, lease unreleased | 1 presence-stall | requeued [7] | 1 recovered, job 7, step 2 | second worker claims, healthy |
| rowan / job 8 | claimed, lease unreleased | 1 presence-stall | requeued [8] | 1 recovered, job 8, step 2 | second worker claims, healthy |
| hana / job 9 | claimed, lease unreleased | 1 presence-stall | requeued [9] | 1 recovered, job 9, step 2 | second worker claims, healthy |
| Control: reboot before lease expiry | claimed | 1 presence-stall | requeues nothing | n/a | job stays claimed |

Each run's only state change between cut and reclaim is the
jobs.py requeue rule (imported from the WDG-020 drill, not
re-implemented); the stall alert auto-resolves once the job
reopens, and the OS-127 recovery line reconciles the sweep
count (1) against the recovered record (1) instead of
claiming a recovery it cannot reconcile.

## NOT proven here (honest gaps, owed on the test image)

- A real hard kill of a booted Meta OS VM (power cut, not a
  modeled presence drop), and a real reboot after it — there
  is no test image in this repo, and killing this host VM
  would kill the drill itself.
- The lease sweep running as part of a real boot sequence
  (relay-jobs unit, OS-014) rather than the drill applying
  the same rule to a fixture snapshot.
- Timings on real hardware: the drill's reboot tick is past
  lease expiry by construction, so no wall-clock recovery
  time is measured here.
