# Milo tasks — Round 4 (the 72-hour window)

From Pax, 2026-11-01 ~20:30 EST. Boss order: 72-hour all-in
window, everything substantive in the next 24 hours. Your
12-hour lane (M-1 to M-5 in os-build/PAX_12H.md) stands and is
the base of this set. Branch: `milo/os-gate`. You gate Rowan
and Hana; Pax gates you; Pax merges.

## ML4-1 — Scoreboard v5 (already ordered, now dated)

The corrections from os-build/PAX_12H_RESPONSE.md: kernel
compiles and boots on the Mac (Buffy's repro log named), L2/L3
updated, framebuffer scored DEAD not pending, dead lines 1,060,
L4 split honestly (small merged services set vs Buffy's 95-file
corpus at TYPECHECK-FAILS), Buffy mid-run not standing by.
No PROVEN row without a named log. Land it early in the window;
v5 is what the claim audit (ML4-4) reads.

## ML4-2 — gates.md

`os-build/gates.md`: the boot-log gate (the exact grep line that
proves each milestone, runnable against os-build/logs/) and the
per-merge checklist, 10 lines at most: what runs, in order, and
what "no" looks like. Pax must be able to run it unaided.

## ML4-3 — Gate-1 for the whole push

Verdict on every branch that asks in the window: rowan/kernel,
hana/os-shell, buffy/layer1-goose-services when she signals,
opencode/round4, and the Imperium auto-dispatch branch. Each
verdict posts in room 1 with the evidence named (log file, test
counts). A RED verdict quotes the failing lines. Nobody's branch
is green on its own say-so, including this lane's.

## ML4-4 — Claim audit at H+24

`os-build/CLAIM_AUDIT.md`: take the adopted claim sentence apart
clause by clause (boots on x86_64 in QEMU / drops to ring 3 /
three userspace programs / fault isolated to one task / shell
reports real state / one-command reproduction) and mark each
VERIFIED with the log or file on main that proves it, or OPEN
with the missing piece named. This is the document the demo and
the submission stand on.

## ML4-5 — Submission checklist draft

`os-build/SUBMISSION_CHECKLIST.md`: draft the hackathon
submission checklist from the event rules (repo public and
fresh, Meta model use named, 3-minute demo video, library
attributions for anything not built in the window, one project
only). Draft only — Pax and the boss work it into the final
submission; flag anything you cannot verify from the repo.

## Rules

Reject any report line that claims a milestone without a log
file name — that is the whole job (M-5). Status words exactly
VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED. Hard
freeze at H+9 of the 12-hour clock (05:12 EST) applies to
feature work; gates and the audit continue past it.
