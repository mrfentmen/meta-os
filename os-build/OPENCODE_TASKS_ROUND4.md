# OpenCode tasks — Round 4 (the 72-hour window)

From Pax, 2026-11-01 ~20:30 EST. Boss order: this is the 72-hour
all-in window to the Wed Nov 4, 9:00 PM ET deadline, and everything
substantive lands in the next 24 hours. Your Mac proof task
(OPENCODE_MAC_PROOF.md, amended tonight) comes FIRST and is still
open. These four tasks follow it, in this order. Work on branch
`opencode/round4`. Report file: OPENCODE_ROUND4_REPORT.md on that
branch. Standing rules hold: no source edits outside a task's scope;
compile or boot errors are reported verbatim and you stop on them;
never read or print the API key (if a task ever needs it, it is
line 1 only of ~/Desktop/hackathon key.txt).

## R4-1 — gate.sh, landed and green from a clean checkout

Deliver `os-build/gate.sh`: one command that pins the nightly
toolchain (PATH fix from OPENCODE_MAC_PROOF.md step 2), builds the
userspace per program at its own base, builds the kernel, boots
QEMU headless, types `help` and `status` through
`os-build/tools/drive.py`, and asserts the proof lines (alive,
K4 summary, HELLO FROM USERSPACE, exit code 0, task killed,
shell answers, STATUS line) with a hard FAIL on any
`loader refused` line. Buffy's Appendix B in os-build/PAX_12H.md
is the proven draft; adapt it, do not reinvent it. Proof: run it
from a fresh clone of main and paste the full output into the
report. Green from clean checkout is the only pass.

## R4-2 — The userspace build fix, as a branch

Encode the per-program build in the repo's build path (the pipeline
script that builds userspace), so a normal build produces binaries
at the right bases with no hand steps. Do NOT land the standalone
`.cargo/config.toml` patch by itself (it links every program at
crasher's base; Pax ruling in os-build/PAX_12H_RESPONSE.md). Do not
touch the loader's refusal path. Proof: gate.sh green with your
branch checked out, log named in the report.

## R4-3 — The demo boot log (K7)

Produce `os-build/logs/K7-boot.txt`: a full typed session through
drive.py against the best merged tree available — boot, the three
userspace programs, `help`, `status`, and every shell command the
tree supports by then (Rowan's R-lane adds prompt, backspace,
`mem`, `ps`, `read_key` during the window; re-run this task after
his merge lands). Every line in the log must be real output. If a
command is not in the tree yet, the report names it as missing;
the log never fakes it.

## R4-4 — Merge-watch for the 24-hour push

While the window runs, Pax merges crew branches to main
continuously. For each merge Pax announces on the report branch
(or that you observe on main), re-run gate.sh against the new main
tip and append one line to the report: tip hash, GATE GREEN or
GATE RED, log file name. A red gate is reported the same hour with
the failing lines quoted verbatim. This task is what makes every
merge in the push proven instead of claimed.

## Report

OPENCODE_ROUND4_REPORT.md: one section per task, status words
exactly DONE / PARTIAL / BLOCKED, every claim tied to a log file
name or a command output pasted in full. End with what remains
unverified.
