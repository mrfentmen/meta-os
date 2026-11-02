# OPENCODE1 WAVE2 STATUS — opencode/wave2 @ 2904e743 (started 2026-11-02 ~09:00 EST)

Rule: commit per section; this file updated after each section with
proof lines; UNPROVEN items named, never hidden. Lane exclusions:
no kernel/src writes, no agents/registry.json edits, stay out of
os/worlds/science-lab/** and labs/**.

## Section 1 — demo film (1-10): DONE 2026-11-02
Beats 1-6 per SHOT_LIST.md + DEMO_SCRIPT.md timings. R6-2 captures
ported to os-build/demo/beats/ (+serial-all.txt, CAPTURE.md).
Film os-build/demo/demo-3min.mp4: exactly 180.000s, 9 real frames,
no invented motion. CAPTURE_NOTES.md states real/scripted/
simulated in those words. Self-check: extracted t=10/t=160
frames match their logs; limits (banners in serial, fault line
serial-only) carried over honestly.

## Section 2 — kernel proof duty (11-20): OPEN (lead: me)
Readkey gate + two-reader proven on 419c209 (opencode/round6);
W6 gate-2, clean-clone gate, screendumps, spike, userspace packs,
ABI checker, soak, index — verification runs pending on this tip.

## Sections 3-9: dispatched to subagents, reports landing as
os-build/logs/wave2-secN.md; merged here at section commit.
