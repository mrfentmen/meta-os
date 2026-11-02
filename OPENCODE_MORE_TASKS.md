# OPENCODE — MORE TASKS (boss order, 2026-11-02)

## The 24-hour freeze is REMOVED

By the boss's direct order (2026-11-02 ~07:33 EST): any
24-hour freeze, 24-hour merge-watch window, or H+9 stop that
older OpenCode lists put on this lane is lifted. That kills
R6-4 "freeze support" in OPENCODE_TASKS_ROUND6.md and the
finish-line freeze in OPENCODE_FINISH_TONIGHT.md, for the
OpenCode lane. OpenCode does not stop at a clock mark.
OpenCode builds, proves, and captures through the submission
deadline (Wed Nov 4, 9:00 PM ET), taking the next task on
this list whenever one closes. The only freeze-shaped duty
left is the submission-day state snapshot, and only when Pax
calls for it by name.

Standing rules unchanged: your branch, named artifacts, no
claim without its log, simulated stays labelled, Pax merges.

## 1. Demo capture (R6-2) — still first

The film is the biggest missing submission piece. Follow
os-build/demo/DEMO_SCRIPT.md beat by beat; land the capture
files plus CAPTURE.md naming each beat's file and duration.
A beat the tree cannot do is reported missing, never staged.

## 2. Readkey gate run

Rowan's pack (rowan/kernel-readkey-merge @ 419c209): run
os-build/gate.sh, land the boot log. Required in the log:
user readkey entry, 8 tasks, no panic, two-reader proof.
Green log: Pax merges readkey the same run.

## 3. Post-merge proof duty (new, standing)

Every time Pax lands a merge batch on main, prove the new
main from a clean clone: gate.sh 7/7, the cargo workspace
check, the node suite against the 55-failure baseline, the
queue python suite. Land one PROOF-<tip>.md per batch under
os-build/logs/ with the tip, the four results, and the exact
commands. A red result is a finding on room 1, not a quiet
rerun.

## 4. Kernel build-out proofs (as Rowan's work lands)

For each kernel build-out item that reaches a branch
(KERNEL_BUILDOUT_SPEC.md K1-K6), run its proof boot on the
Mac and land the log: framebuffer screendump for K1, the
demand-paging fault-and-retry log for K3, the talker/listener
exchange for K4, the write-reboot-read file proof for K5.
If an item's branch is not ready, say so once and move on.

## 5. Bootloader / framebuffer spike, executed

Rowan's spike part 2 names the route on paper. Execute it:
on a scratch branch, move the bootloader to the version the
spike names, build, boot in QEMU, and land the screendump —
or the exact build/boot failure that blocks it. Evidence
either way; the route call gets made on your artifact.

## 6. Face build long tail (resume and finish)

Return to OPENCODE_FACE_BUILD.md after items 1-2 and close
the remaining sections in order. Same proof rule: a section
is done when its screendump or log is committed. When the
face list empties, this list is the queue — not a stop.

## 7. Image proofs still owed

- UTM / hardware boot of the face image: boot it on the real
  machine path, photograph or log the result either way.
- Toolchain in the bake: prove OpenCode and the crew
  toolchain are inside the current image (a listing), or land
  the finding that they are absent.

## 8. Userspace pack proofs

When Buffy's userspace programs (hog, talker, listener,
quitter) land, boot each on the Mac and land its log against
the line its spec promised. A program whose log line does
not match its spec is a finding on room 1.

## 9. Endurance

One 2-hour QEMU soak on the latest main: panic watch on,
tick/ps sampled at start, middle, and end. Land the summary
log. Any panic stops the soak and the log is the report.

## 10. Submission rehearsal

Build the submission tree from a clean clone exactly as the
submission will: run every suite, record the counts, walk
DEMO_SCRIPT.md against the committed logs and name any beat
whose evidence is missing. Land SUBMISSION_REHEARSAL.md.
This is a rehearsal, not the freeze: work continues after it.

## Order

1, 2, then 3 as merges land, 4-5 as branches appear, 6 in
the gaps, 7-10 before the deadline. When this list runs out,
ask Pax on room 1 — do not stop at the end of a list.
