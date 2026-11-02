# OpenCode tasks — Round 6 (queues behind Round 5)

From Pax, 2026-11-01 ~21:35 EST. Boss order: this list queues
behind OPENCODE_TASKS_ROUND5.md automatically — when Round 5
closes, start here without waiting for a new assignment.
Branch: `opencode/round6`. Report: OPENCODE_ROUND6_REPORT.md.
Standing rules hold (scope, verbatim errors, key handling).

## R6-1 — Clean-room reproduction of the claim

From a fresh clone of main on the Mac: one command sequence,
start to finish, that reproduces the adopted claim sentence
(boot, ring 3, three programs, fault isolation, shell
reporting real state). Paste the full terminal record into
the report with timings. This is the submission's
reproducibility proof; if any step needs a human trick that
is not written down, the task is to write it down, not to
perform it silently.

## R6-2 — Demo capture session

Per Hana's `os-build/DEMO_SCRIPT.md` (when it lands): capture
the QEMU sessions the video needs — serial logs plus screen
captures for each scripted beat, named by beat. Real output
only; a beat the tree cannot do yet is reported as missing,
never staged.

## R6-3 — Second live loop, different product

Repeat the R5-4 Imperium live run with a different division
(Ignis or Medicus staged feed): package with picture, sim
receipt, incident record captured. Same honesty rules and
caps. Two divisions proven live beats one.

## R6-4 — Freeze support

At the H+9 freeze (2026-11-02 05:12 EST) and again at the
24-hour mark: gate run against the frozen main tip, log
committed, one line in the report (tip, GREEN/RED, log name).
This is the freeze certificate the claim audit reads.

## R6-5 — Submission package checks

Repo hygiene, verified and reported: no `target/` or build
artifacts tracked, secret scan clean (0 hits), every report
and log the submission cites actually present at the path
cited, README links resolve. Fix nothing outside this list;
report each check with its command.

## R6-6 — Merge-watch, final stretch

Continues from R4-4/R5-6 until the boss calls the window
closed: one gate run per new main tip, one report line each.

## Report

One section per task, status words exactly DONE / PARTIAL /
BLOCKED, claims tied to named logs or pasted output. End
with what remains unverified.
