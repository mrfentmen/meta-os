# CAPTURE_NOTES.md — 3:00 demo cut (Wave 2 Section 1, tasks 8-10)

Film: os-build/demo/demo-3min.mp4 (180.000s, 10fps, 1280x720).
Frames: os-build/demo/frames/ (9 PNGs). Cut list:
os-build/demo/cut.txt (+join.txt, seg_*.mp4 intermediates).

## What is real

Beats 1-5 are verbatim QEMU screendumps from the R6-2 capture
session (merge 28e99285, GATE GREEN): boot text, loader lines,
hello/sleeper/crasher, fault window, typed status/mem/ps answers.
Each frame is a real captured screen; holds are static (no
invented motion), durations follow DEMO_SCRIPT.md timings
(25/25/30/15+10/12+11+12/40).

## What is scripted

Nothing in beats 1-5 is staged: no scripted assessor, no
generated input beyond the typed shell commands (status, mem,
ps), which the serial log backs verbatim.

## What is simulated

Beat 6 (0:40 receipt card) is rendered text quoting the
committed log os-build/logs/R5-imperium/receipt.txt
(receipt_id sim-6623d237a90b3d9d, simulated=true). The card
says SIMULATED on its face. The Imperium reading behind that
receipt was staged (scripted assessor + generated JPEG); the
receipt itself is the real endpoint record.

## Self-check (task 10)

Watched end to end via extracted frames (t=10 boot text OK,
t=160 receipt card OK; middle beats are the verified R6-2
dumps). No frame shows anything the logs do not back. The two
known honest limits ride along from R6-2: early banners live
in the serial log (scrolled off the 25-line VGA), and the
fault line itself is serial-only.
