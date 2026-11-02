# OC1B s2 — verdict blocks for coordinator merge (OpenCode 1, 2026-11-02)
# Branch: opencode/500-s2 @ (see commit shas below). Base: opencode/500 @ 94010c76.
# Fences honored: no push to main; no commit to opencode/500; kernel/src untouched
# (all builds ran in detached scratch worktrees /tmp/oc500-k3, /tmp/oc500-k4);
# kernel/src/syscalls.rs diffs EMPTY on every gated Rowan branch (quoted in
# OC1B-kf01-decision.md, OC1B-k3-tree.txt, OC1B-k4-tree.txt); no face/web work;
# every proof below is a committed file. Rowan branch inventory (measured):
#   rowan/kernel-kf01-spike 8e725f4b | rowan/bootloader-spike 779012ed |
#   rowan/kernel-face-spike 695a3fc0 | rowan/kernel-face-spike-2 0a82f58c |
#   rowan/kernel-k3-build 7bb72075 | rowan/kernel-k3-design 3ff4ad22 |
#   rowan/kernel-k4-build 4a37f998 | rowan/kernel-k4-design 0f5b5575 |
#   spike/bootloader-0.11 db0b0020 (round7 history, never re-run)

## §2 KF-01 bootloader spike (OC1B-026..050) — VERDICT: BLOCKED attempts + GREEN restored pin
- 026 DONE: 0.9.35 pin + lock hash in OC1B-kf01-start.txt (measured).
- 027 DONE: control textboot screendump os-build/captures/oc1b-kf01-control-textboot.png
  (720x400, status answered on screen, tasks=8).
- 028 DONE: control serial OC1B-kf01-control-serial.txt (343 lines, alive line 2, panic 0).
- 029 BLOCKED: no Rowan attempt-1 build/boot branch exists (8e725f4b is docs-only, pin 0.9).
  Fresh-candidate confirmation: none exists. Budget 0/2. Proof OC1B-kf01-attempt1-branch.txt.
- 030 NOT RUN (blocked by 029 — no attempt to build).
- 031 NOT RUN (blocked). 032 NOT RUN (blocked). 033 NO ATTEMPT (nothing to classify).
- 034 NOT RUN (no probe line; absence named in verdict file).
- 035 BLOCKED: no second fresh candidate on any branch. Budget 0/2. Proof OC1B-kf01-attempt2-branch.txt.
- 036-039 NOT RUN (blocked by 035).
- 040 HARD STOP recorded: no third attempt; round7 pair stays history. Proof OC1B-kf01-decision.md.
- 041 DONE: pin+lock verified identical to start record. Proof OC1B-kf01-restored.txt.
- 042 DONE: gate.sh GREEN on restored tree (8 ok lines, panic 0, no loader refusal).
  Proof OC1B-kf01-restored-gate.log.
- 043 N/A: no upgraded stack exists — success-path gate has no tree to run on.
- 044 N/A: same reason; no success numbers exist.
- 045 DONE: decision = RESTORED PIN, attempts/blocked/evidence in OC1B-kf01-decision.md.
- 046 DONE: elapsed ~35 min recorded in OC1B-kf01-decision.md.
- 047 DONE: syscalls.rs diffs EMPTY on kf01-spike, bootloader-spike, spike-0.11(history),
  k3-build, k4-build — quoted in OC1B-kf01-decision.md.
- 048 VERDICT BLOCK (this file): §2 gated what exists; attempts BLOCKED-on-Rowan
  (missing: Rowan KF-01 attempt-1/2 build/boot branches with a fresh 0.11.x-line
  candidate); restored pin GREEN.
- 049 BLOCKED line (per task rule): KF-01 attempts await Rowan attempt branches;
  moved on with budget 0/2 unspent.
- 050 DONE: §2 checkpoint commit 34684b0ac2f50ad6817a11b4a5f584c793a40e6f on opencode/500-s2.

## §3 KF-02..KF-10 (OC1B-051..075) — VERDICT: ALL BLOCKED-on-Rowan
- 051 BLOCKED (no upgraded stack). 052-054 BLOCKED (missing Rowan KF-03 wiring branch).
- 055-056 BLOCKED (missing Rowan fill-test branch). 057-059 BLOCKED (missing KF-04 branch).
- 060-061 BLOCKED (missing KF-05). 062-063 BLOCKED (missing KF-06).
- 064-065 BLOCKED (missing KF-07). 066-067 BLOCKED (missing KF-08).
- 068 BLOCKED (missing KF-09). 069-073 BLOCKED (missing KF-10; 073 has no tree to gate).
- 074 NOT RUN: zero §3 boots exist (0 panics observed, 0 asserted).
- 075 VERDICT BLOCK: per-KF GATED/FAILED: none; BLOCKED-on-Rowan: KF-02..KF-10 all.
  Deciding file: OC1B-s3-verdicts.md. §3 checkpoint commit d482676fb35469a115fed1b497a10d221f7659ea on opencode/500-s2.

## §4 KF-11 + Milestones 2-3 (OC1B-076..100) — VERDICT: KF-11 BLOCKED; KF-12..20 UNIMPLEMENTED
- 076-083 BLOCKED (no KF-10/Milestone-1 tree to pack/reproduce).
- 084 KF-11 verdict: BLOCKED-on-Rowan (missing KF-10 branch transitively KF-03..09).
- 085-086 UNIMPLEMENTED (missing Rowan KF-12). 087-089 UNIMPLEMENTED (missing KF-13).
- 090-091 UNIMPLEMENTED (missing KF-14). 092-093 UNIMPLEMENTED (missing KF-15).
- 094 UNIMPLEMENTED (missing KF-16). 095 NOT RUN (no graphics tree to soak).
- 096 UNIMPLEMENTED (no face boot). 097 UNIMPLEMENTED (Rowan final note missing).
- 098 BLOCKED (no graphics tree; gate.sh unchanged on text tree per control run).
- 099 unimplemented list: KF-12..KF-20, branches named, in OC1B-s4-verdicts.md.
- 100 VERDICT BLOCK: Milestone 1/2/3 UNPROVEN. Deciding file OC1B-s4-verdicts.md.
  §4 checkpoint commit 208d0de599f62e629d857f37467b7e27a1dcdf83 on opencode/500-s2.

## §5 K3 demand paging (OC1B-101..125) — VERDICT: demand leg FAILED (deterministic); containment PROVEN; negative UNPROVEN; DO NOT MERGE
- 101 DONE: K3 tree 7bb72075 + kernel-only diff stat in OC1B-k3-tree.txt.
- 102 DONE: syscalls.rs diff EMPTY (quoted in OC1B-k3-tree.txt).
- 103 DONE: K3 bootimage built, sha256 16c72550…f307, 13749760 B. Proof OC1B-k3-build.log.
- 104 DONE: two boots, serials OC1B-k3-gatepack-serial.txt / OC1B-k3-gatepack2-serial.txt.
- 105 QUOTED: `demand: touching promised page` + kill err 0x5 (present/user-read, not P=0).
- 106 FAILED: zero `page mapped, retry` lines (grep count 0, both boots).
- 107 FAILED: no demand completion. 108 FAILED: no zero-fill line.
- 109 PROVEN: crasher kill line 46 quoted. 110 PROVEN: survivor `sleeper: yielded and back` line 49.
- 111 UNPROVEN: demand died before out-of-region touch. 112 UNPROVEN (same).
- 113 PASS (0 map lines). 114 PASS (panic count 0, both boots).
- 115 PARTIAL: status PROVEN (serial STATUS lines, ticks moved 6435→6705); mem+ps quoted
  from VGA frame os-build/captures/oc1b-k3-shell.png (frames_free 125802, 9 ps rows).
- 116 DONE: shared-root basis note in OC1B-k3-gatepack.md (observed + build-note §2).
- 117 DONE: gate.sh GREEN on K3 tree (8 ok lines). Proof OC1B-k3-gate.log.
- 118 DONE: boot 2 reproduces leg-for-leg (SAME/SAME/SAME). Proof second serial.
- 119 NOT RUN (demand dies first touch; loop impossible). 120 NOT RUN (failed leg; no soak).
- 121 PARTIAL: readkey entry+polling+`done got=0` PROVEN; typed byte (got>0) UNPROVEN.
- 122 UNPROVEN (no repeated-fault case observed; named fallback).
- 123 VERDICT: demand FAILED / containment PROVEN / negative UNPROVEN; DO NOT MERGE 7bb72075.
  Proof OC1B-k3-gatepack.md.
- 124 DONE: tree sha + image hash in OC1B-k3-gatepack.md.
- 125 DONE: §5 checkpoint commit 235ed1605ab9e4552733286a87221a0f1472b720 on opencode/500-s2.

## §6 K4 IPC (OC1B-126..150) — VERDICT: tree builds+boots GREEN; all 7 acceptance lines UNPROVEN (pair+swap missing); DO NOT MERGE as IPC proof
- 126 DONE: 7-line checklist OC1B-k4-checklist.md (literals from design §7).
- 127 DONE: K4 tree 4a37f998 + user.rs-only dispatch (6=>/7=>) in OC1B-k4-tree.txt.
- 128 DONE: syscalls.rs diff EMPTY (quoted). 129 DONE: MAX_TASKS=8 quoted; swap NOT in branch.
- 130 DONE: K4 bootimage built, sha256 e2a9bce2…07d0, 11218944 B. Proof OC1B-k4-build.log.
- 131 DONE: serial OC1B-k4-gatepack-serial.txt (49642 B, 2078 lines, gate point ~20s).
- 132-140 ALL UNPROVEN: grep ipc = 0 lines (no talker/listener on any branch; no spawn swap
  in branch; writing either here is forbidden). Missing pieces named per task in OC1B-k4-gatepack.md.
- 141 UNPROVEN. 142 UNPROVEN by boot (mechanism on paper only). 143 UNPROVEN by boot.
- 144 UNPROVEN by boot. 145 NAMED, NOT EXERCISED (zero traffic; design states the limit).
- 146 UNPROVEN (named fallback). 147 PASS: panic 0 + STATUS tasks=8 line 2067.
- 148 DONE: gate.sh GREEN on K4 tree (8 ok lines). Proof OC1B-k4-gate.log.
- 149 NOT RUN (no pair traffic to soak).
- 150 VERDICT: builds+boots, text GREEN, IPC pack BLOCKED on Buffy pair (R11-273, no branch)
  + gate-build swap (not in Rowan branch); DO NOT MERGE as IPC proof. Proof OC1B-k4-gatepack.md.
  §6 checkpoint commit 5a0bef5398d1a09cd0ee1012cbd82ba57f62cf68 on opencode/500-s2.

## Proof paths committed on opencode/500-s2 (all under os-build/)
- logs/OC1B-kf01-start.txt, OC1B-kf01-attempt1-branch.txt, OC1B-kf01-attempt2-branch.txt,
  OC1B-kf01-decision.md, OC1B-kf01-restored.txt, OC1B-kf01-restored-gate.log,
  OC1B-kf01-control-serial.txt, OC1B-s3-verdicts.md, OC1B-s4-verdicts.md,
  OC1B-k3-tree.txt, OC1B-k3-build.log, OC1B-k3-gatepack-serial.txt,
  OC1B-k3-gatepack2-serial.txt, OC1B-k3-gate.log, OC1B-k3-gatepack.md,
  OC1B-k4-checklist.md, OC1B-k4-tree.txt, OC1B-k4-build.log,
  OC1B-k4-gatepack-serial.txt, OC1B-k4-gate.log, OC1B-k4-gatepack.md,
  OC1B-s2-STATUS-SNIPPET.md (this file)
- captures/oc1b-kf01-control-textboot.png, captures/oc1b-k3-shell.png
- Scratch worktrees (NOT committed, NOT pushed): /tmp/oc500-k3 (detached 7bb72075),
  /tmp/oc500-k4 (detached 4a37f998). kernel/src untouched in every committed tree.
