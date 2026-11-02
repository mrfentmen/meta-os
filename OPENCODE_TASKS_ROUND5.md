# OpenCode tasks — Round 5 (the 72-hour window, night 1)

From Pax, 2026-11-01 ~21:30 EST. Your Mac proof and Round 4 are
verified and merged to main (gate.sh, MERGED-boot.txt, both
reports). The merged tree is PROVEN at e0d8d94 — and main has
moved since: Rowan's RW4-1 kernel work landed tonight (banner
K6, backspace/shift, scancode spam deleted, `mem`/`ps` commands,
syscall 5 `read_key`, uptime as command only). Branch:
`opencode/round5`. Report: OPENCODE_ROUND5_REPORT.md on that
branch. Standing rules hold: no source edits outside a task's
scope; errors verbatim and stop; never read or print the API
key (line 1 only of ~/Desktop/hackathon key.txt, and only if a
task below needs Spark — R5-4 may, inside the stated caps).

## R5-1 — Re-prove current main

Run gate.sh against the new main tip and commit the fresh boot
log as `os-build/logs/MERGED-boot-2.txt`. Required in the log:
banner `META OS 0.1 (K6)`, alive line, K4 summary, all three
userspace programs, `loader refused` count 0, no panic. If the
new kernel work breaks the gate, the report quotes the failing
lines verbatim and stops — no fixes in this task.

## R5-2 — read_key, proven end to end

Add one small userspace program to the userspace crate (your
crate, your lane): it calls syscall 5 in a loop and prints what
comes back. Drive real keys at it through
`os-build/tools/drive.py` and commit the log. Pass = the log
shows the typed bytes returned by syscall 5, and the empty case
(yield/poll, no crash) visible. Build it with the per-program
recipe at its own base like the other three.

## R5-3 — The final K7 demo session

Refresh `os-build/logs/K7-boot.txt` against current main: boot,
the three userspace programs, then typed `help`, `status`,
`mem`, `ps`, `uptime`, one unknown command (its real refusal
line), and the crasher's fault isolation. Every line real output
from drive.py. This log is what the demo script reads.

## R5-4 — Imperium live loop, first full run

On the Mac, run the product stack end to end with a staged,
labelled test feed (dataset clips already on disk are fine):
patrol flags, review confirms, investigation runs, and the new
direct dispatch sends the package WITH the picture to the
simulated endpoint. Capture: the incident record, the package
as sent (picture field present), and the sim receipt id.
Honesty rules unchanged: simulated endpoint only, SIMULATED
labelled, per-incident caps and the budget guardrail respected,
no real external endpoint of any kind. If the live loop cannot
run for an environment reason, report the exact blocker with
the failing command's output — a named blocker is a result.

## R5-5 — Soak on the current tree

One 10-minute QEMU run via the gate harness: the three
userspace programs cycling, crasher included, console commands
throughout. One log, committed. Pass = no panic, no hang, the
fault stays isolated to the crasher.

## R5-6 — Merge-watch continues

Standing from R4-4: for each new main tip during the window,
one gate run and one report line (tip, GREEN/RED, log name).
A red gate is reported the same hour with failing lines quoted.

## Report

One section per task, status words exactly DONE / PARTIAL /
BLOCKED, every claim tied to a named log or pasted output. End
with what remains unverified.
