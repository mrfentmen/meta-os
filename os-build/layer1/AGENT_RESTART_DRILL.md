# A2 restart drill — runtime died mid-run

Root: `/var/folders/r0/mc2kkvz94f32cfbmq91kj7p40000gn/T/restart-drill-UeCMpk`  (temp; the crash state is reconstructed, see the script header)

## Before the restart

- run `r-old` ledger: spawn  ← no exit: the run did not finish by itself
- baton on disk: { "state": "west wall half built", "artifacts": [ "wall.txt" ], "nextStep": "finish the west wall", "ts": "2026-11-02T09:48:21.535Z" }
- watchman state: {"claimed":["j1"],"resume":{}}

## Restart 1 — reconcile

- recovered: `[{"id":"j1","action":"resume","from":"r-old"}]`
- run `r-old` ledger now: spawn, run-orphaned

## The resumed run `worker-mvz2t869`

Brief orders (first lines):

```
Continuation of run r-old — pick up the baton, do not restart.
State: west wall half built
Artifacts so far: wall.txt
Next step: finish the west wall
```

- new run ledger: spawn, exit
- watchman ledger: bell, resume-from-orphan, baton-pass, bell, job-done
- result file: `/var/folders/r0/mc2kkvz94f32cfbmq91kj7p40000gn/T/restart-drill-UeCMpk/jobs/j1.result.json` exists=true

## Restart 2 — after the run completed

- recovered: `[]`
- spawns on this poll: 0
- claimed ids: j1

Verdict: the orphaned run is marked `run-orphaned`, the next run CONTINUES from its baton,
and a second restart neither re-runs the job nor spawns a duplicate.
