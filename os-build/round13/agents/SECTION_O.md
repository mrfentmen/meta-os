# Section O — chaos over the five loops (R13-351..375)

Run: `node os-build/layer1/loop_drills.mjs O`. Machine record: `LOOP_DRILLS.json`.

Counts: {"total":25,"OBSERVED":11,"GAP":5,"OBSERVED-GAP":9}

Musica (musica-studio) and Officina (officina-faber) stay NOT COVERED: both registry entries are draft:true with the reason that they live outside this repo, and their command is the placeholder `true`.

Faults with no injection seam in this repo (env, clock, slow dependency) are filed as observed gaps naming the module that would own the seam — they are not simulated by editing the loop.

| task | loop | mode | status | what happened |
|---|---|---|---|---|
| R13-351 | aegis | kill mid-run | OBSERVED |  |
| R13-352 | nervus | STOP file mid-run | OBSERVED |  |
| R13-353 | handsfree | budget set below cost | OBSERVED |  |
| R13-354 | imperium | input file removed mid-run | OBSERVED | patrol.py takes no input-file argument in this invocation and still does not terminate |
| R13-355 | cadence | duplicate start attempt | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-356 | aegis | watchman killed during cycle | OBSERVED | the loop is unaffected by the watchman's death: they share no state, so a dead relay does not stop a running loop |
| R13-357 | nervus | ledger write interrupted | OBSERVED | the loop appended after a torn line and left it in place: a reader that throws on one bad line loses every record after it |
| R13-358 | handsfree | network route down (osv route) | OBSERVED | the env path is exercised by run-sweep.mjs, not by the hosted loop |
| R13-359 | imperium | clock skew injected | OBSERVED-GAP | clock.mjs has elapsedMs(), which is the place a skew guard would live; the loop does not call it |
| R13-360 | cadence | oversized input | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-361 | aegis | empty input | OBSERVED-GAP | aegis takes no input file or text argument, so this fault has no subject in it |
| R13-362 | nervus | malformed input | OBSERVED-GAP | nervus takes no input file or text argument, so this fault has no subject in it |
| R13-363 | handsfree | slow dependency | OBSERVED-GAP | a slow dependency can only be simulated by editing the loop, which would test the edit |
| R13-364 | imperium | restart during drill | OBSERVED | two copies run without contention: no lock, no claim, no singleton guard on the imperium loop |
| R13-365 | cadence | second drill overlapping | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-366 | aegis | receipt directory missing | OBSERVED-GAP | os-build/aegis holds committed nested evidence or exceeds the 4 MB snapshot cap; deleting it to test mkdirSync would delete records, so it was not removed |
| R13-367 | nervus | job file corrupted | OBSERVED-GAP | covered by the Section N corrupt-job drill against the real watchman; this loop reads no job files |
| R13-368 | handsfree | registry entry missing | OBSERVED-GAP | spawnHosted does not consult the registry, so a missing entry is not a fence here; the check lives in watchman.mjs |
| R13-369 | imperium | command exits nonzero | OBSERVED-GAP | the loop hung and was stopped by the drill ceiling, so no exit code was produced — not a nonzero-exit observation |
| R13-370 | cadence | command hangs past timeout | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-371 | aegis | partial output written | OBSERVED-GAP | the loop's receipt is written with writeFileSync, which is not atomic: a kill inside the write leaves a truncated receipt. This run completed, so the window was not hit |
| R13-372 | nervus | state file truncated | OBSERVED | a truncated previous receipt is overwritten with a valid one on the next run |
| R13-373 | handsfree | env var missing | OBSERVED | the env path is exercised by run-sweep.mjs, not by the hosted loop |
| R13-374 | imperium | working dir moved | OBSERVED | a missing working directory kills the process that called spawnAgent: there is no 'error' listener on the child, so the runtime reports a bad cwd as an uncaught exception |
| R13-375 | cadence | drill repeated back-to-back | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |

