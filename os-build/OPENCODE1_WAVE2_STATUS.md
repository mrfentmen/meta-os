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

## Section 2 — kernel proof duty (11-20): DONE 2026-11-02
11 readkey gate + 12 two-reader: evidence on opencode/round6 (gate GREEN 419c209, got=7).
13 W6 gate-2 boot 9de854d: GATE GREEN here (logs W6-gate-*, fetch screen shot W6-fetch-screen.jpg).
14 clean-clone gate f027175: GATE GREEN (PROOF-f027175.md + boot).
15 current-tip screendump 2904e743: WAVE2-boot-tip.jpg + serial.
16 bootloader spike: executed on opencode/round7 (both routes fail, evidence committed).
17 userspace packs: quitter unwired finding + hog/talker/listener absent (findings note on round6).
18 ABI checker: check_all PASS (all checkers incl abi_check).
19 2h soak: RUNNING on merge-tip3 image (/tmp/soak-serial.txt), verdict pending.
20 proof index: os-build/logs/WAVE2_PROOF_INDEX.md.
Readkey gate + two-reader proven on 419c209 (opencode/round6);
W6 gate-2, clean-clone gate, screendumps, spike, userspace packs,
ABI checker, soak, index — verification runs pending on this tip.

## Sections 3-9: dispatched to subagents, reports landing as
os-build/logs/wave2-secN.md; merged here at section commit.
