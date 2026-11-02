# OPENCODE — BLOCKERS CLEARED (Pax, 2026-11-02)

The boss ordered every blocker on this lane cleared. Here is
each one, cleared or named.

## Cleared

1. **The clock.** The 24-hour freeze, the H+9 stop, and the
   merge-watch window are lifted (OPENCODE_MORE_TASKS.md).
   Nothing on this lane stops at a time mark.
2. **The branch.** OPENCODE_FINISH_TONIGHT.md said to open
   `opencode/round6` only if Pax says. Pax says: work on
   `opencode/face` for the face build, `opencode/round7` for
   everything on the MORE TASKS list. No asking first.
3. **Demo capture dependencies.** R6-2 needs nothing that is
   not on main: the script (os-build/demo/DEMO_SCRIPT.md)
   and the shot list are committed. The readkey log does not
   gate the film. Shoot it.
4. **The readkey pack.** Rowan's pack is final at
   rowan/kernel-readkey-merge @ 419c209. Nothing is owed to
   it from Pax's side. Run the gate; a green log is merged
   the same run, a red log is a finding with the exact lines.
5. **The kernel-face route.** Rowan's spike part 2 is done
   (face-spike-2). MORE TASKS item 5 executes it — no design
   decision is waiting on anyone.
6. **Post-merge proof duty.** It runs per merge batch when
   Pax names the tip on room 1. It never blocks items 1-2
   or the face build; if no batch is named, skip to the
   next item on the list.
7. **The merge side.** Pax is merging now (W1 merged and
   verified; W7, W5, W3, C4, B10 in the queue). OpenCode
   work is never waiting on a Pax merge to continue — build
   on your branch, Pax pulls it in at checkpoints.

## The one blocker Pax cannot clear from here

The API key going in and out (the boss's report, 2026-11-02).
That is the Mac/provider side: when calls fail, log the
failure once in the run report and keep working the offline
items (gate runs, captures, image proofs need no model
calls). Do not idle waiting on the key, and do not retry in
a loop — the build has enough no-API work to never stop.
