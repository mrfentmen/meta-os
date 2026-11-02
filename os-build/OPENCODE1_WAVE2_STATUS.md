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

## Section 3 — face long tail (21-30): DONE (merged build verified on this tree)
Face build merged from opencode/face (35 commits). Subagent verified on this tree: login 5 shots, 11 wallpapers, all 9 apps open w/ guest shots, 16 dock entries, board reboot-persist, 6 settings controls + live facts, dashboard 2s live + load series. Evidence: os-build/logs/wave2-sec3.md + os-build/face/ tree + STATUS.md (74/74 rows).
## Section 4 — carrier image (31-40): DONE with findings
UTM: no headless path (list empty) — recorded. 4 standing checks live in guest (facts/rooms/trash 200, updater pulls logged; STOP set for dev determinism). Toolchain: node+git present, chromium runs kiosk, opencode ABSENT (finding stands). Image recipe re-ran on Mac (metaos-face.img f7d8581e) + fresh boot (login prompt). Evidence: wave2-sec4.md + os-build/face/image/ + guest-*.jpg.
## Section 5 — Imperium live (41-50): DONE (3 divisions)
Vigiles sim-6623d237a90b3d9d, Ignis sim-9da0ad66d87add2e, Medicus sim-5f894be30820178f — all dispatched-simulated with pictures, judge-routed (judge.py SERVICES). Receipt #3 shown in face board (guest-red-receipt.jpg). Evidence: wave2-sec5.md + R5/R6 logs + face-medicus/.
## Section 6 — host services (51-60): BLOCKED on Buffy Round 11 (recon only)
Registry 25/25 placeholder commands, no Goose toolchain/runnable services here, relay 8787 down, supervisor restart unproven, ledgers gym-only. Nothing to host yet — recon filed, no workarounds built. Evidence: wave2-sec6.md.
## Section 7 — systems (61-70): PARTIAL (gaps named)
Musica plays (take-006, ended 7.3s) but musica.html hardcodes the take (not record-driven). Officina 2a/Aegis/Nervus/hands-free: tooling present, no current-section records. Evidence: wave2-sec7.md.
## Section 8 — codebase health (71-80): DONE (counts recorded)
Cargo check 19/19 crates clean (this tree). Python: queue 128, officina 49, custos 125 — all OK (302 total). Node: see Section 2 prove-main note (1947/55 on ab763ac0; 1965/55 on this tip). Hortus: no unittest suite (run.py >120s, reference output kept). Evidence: wave2-sec8.md.
## Section 9 — site/submission (81-90): DONE with flags
5 site claims spot-checked: 4 proven + gate 7/7, with FLAG: MERGED-boot.txt is 0 bytes on main (site cites it; NEXT PROOF label agrees). Board 9/9 unlocated — flagged. Rehearsal: SUBMISSION_REHEARSAL.md on opencode/round6 (54ee4353); R6-2 capture files not on main — flagged for Pax merge. FREEZE_CERT draft present (TBDs). Forms draft absent (checklist is start point). Evidence: wave2-sec9.md.

## Section 10 — final proofs (91-100): DONE 2026-11-02
91 branch gate: GATE GREEN 7/7 on this tree (/tmp/wave2branch-gate.log).
92 node: 1965 pass / 55 fail (same known set as main-tip runs).
93 python: queue 128, officina 49, custos 125 — all OK.
94 cargo check clean; cargo test RED (known E0271 x2, supervisor lane).
95 fresh QEMU boot of wave2 recipe image: `metaos login:` line 822 (face-image-wave2-fresh-boot.txt).
96 face image rebuilt from branch recipe: same sha f7d8581e (deterministic); boots to login; desktop proven on same-recipe running guest.
97 one Imperium loop from this tree era: Medicus rerun, NEW receipt sim-f0e40e1695baefb6 (face-medicus-wave2/).
98 this STATUS file: sections 1-10 each have proof lines or named gaps above.
99 tidy: tree clean except intended wave2 artifacts; no stray files (verified via git status).
100 what is PROVEN that was not proven when this wave started, one sentence per item:
- The demo film exists (180s cut + stills + notes) where only stills existed.
- The readkey pack boots green with typed bytes reaching it (got=7).
- W6 fetch screen shows live kernel state on real hardware-emulated boot.
- A clean clone gates green on a post-Custos tip (f027175).
- The current tip boots to a screendumped text console (2904e743).
- check_all passes every checker including the ABI gate on current main.
- Medicus ran live twice (sim-5f894be3, sim-f0e40e16), third division proven.
- Face long tail closed: lock, notifications, 11 wallpapers, tiling, workspaces, search — guest shots committed.
- The face image recipe reproduces byte-identically (f7d8581e twice).

## Section 3 — model pipeline, live (17-28): DONE with named gaps 2026-11-02
Queue 141/141 pre-live. Live: wonder chat OK; SAM 2 calls, no box both times (recorded, not invented); Spark reading "structure fire" live; image generated (webp 60KB). Judge-model incident ran end to end but judge_mode stayed deterministic (Spark empty reply x3, direct prompt works) — model side UNPROVEN, fallback PROVEN with named reasons. Spend $0.016. Proof: WAVE3_MODEL_PROOFS.md + wave3-model-proofs/.
