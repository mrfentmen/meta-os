# Section N — watchman and watchdog death and recovery (R13-326..350)

Run: `node os-build/layer1/loop_drills.mjs N`. Machine record: `LOOP_DRILLS.json`.

Counts: {"total":25,"OBSERVED":21,"OBSERVED-GAP":2,"GAP":2}

Setup: a real `createWatchman()` driver over a drill registry, killed with SIGKILL at a point read from the driver's own log (`poll-start` = mid-cycle, `poll-end` = between cycles). Detection is `checkBeat()` polling a real heartbeat file; latency is measured from the kill, not estimated.

**Standing finding, every row: nothing restarts the watchman.** `agents/watchdog.mjs` alarms once and exits; it has no spawn path. The only restart measured is a manual respawn by the drill.

| task | loop | mode | status | what happened |
|---|---|---|---|---|
| R13-326 | mid | mid | OBSERVED | watchman killed mid-cycle |
| R13-327 | between | between | OBSERVED | watchman killed between cycles |
| R13-328 | watchdog | watchdog | OBSERVED-GAP | the alarm has no watcher of its own: kill the checker and no beat, no line, no restart happens |
| R13-329 | both | both | OBSERVED | both watchers killed |
| R13-330 | baton | baton | OBSERVED | watchman killed during a baton pass |
| R13-331 | stop | stop | OBSERVED | watchman killed during a STOP drill |
| R13-332 | budget | budget | OBSERVED | watchman killed during a budget kill |
| R13-333 | stale | stale | OBSERVED | watchman restarts onto a stale job file |
| R13-334 | missing | missing | OBSERVED | claim released and the job re-filed on the next poll |
| R13-335 | corrupt | corrupt | OBSERVED | torn job file refused and logged as job-unreadable, not skipped silently |
| R13-336 | watchdog | restart-x2 | OBSERVED-GAP | nothing in this repo restarts the watchman; a death is detected only if someone runs the checker |
| R13-337 | load | load | OBSERVED | detection time at load |
| R13-338 | idle | idle | OBSERVED | detection time at idle |
| R13-339 | locked | locked | OBSERVED | a read-only ledger surfaced as poll-error EACCES: permission denied, open '/Users/test/Desktop/meta-os/os-build/round13/ag and the watchman kept polling |
| R13-340 | no-entry | no-entry | OBSERVED | unknown agent recorded as job-unmatched and the claim is retained |
| R13-341 | draft | draft | OBSERVED | the watchman spawned a draft:true agent; draft is not a fence at spawn |
| R13-342 | aegis | aegis | OBSERVED | restart path during an aegis sweep |
| R13-343 | watchman | cadence | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-344 | handsfree | handsfree | OBSERVED | restart path during a handsfree intake |
| R13-345 | renamed | renamed | OBSERVED | a moved beat file is indistinguishable from a dead relay: this is a false-death path |
| R13-346 | chaos | chaos | OBSERVED | death during a chaos drill |
| R13-347 | watchman | federation | GAP | no federation module exists in this repo; nothing federates, so nothing can die under it |
| R13-348 | stop-present | stop-present | OBSERVED | no STOP file is honoured at the watchman level; the child runtime owns it |
| R13-349 | budget-spent | budget-spent | OBSERVED | death with budget already spent |
| R13-350 | final | final | OBSERVED | death on the final step of a job |

