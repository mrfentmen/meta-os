# §3 Kernel-face Mac gates II — KF-02..KF-10 verdicts (measured 2026-11-02, OpenCode 1)

Grounded in os-build/KERNEL_FACE_BUILD_ORDER.md (KF-02..KF-10) and
os-build/KERNEL_FACE_TASKS.md §B–§C. Standing rule applied: three
screendumps per milestone step is the evidence shape for steps that RUN;
no step below runs, so each records BLOCKED with the missing piece named.

## Precondition measurement (commands run, not asserted)
- origin/rowan/kernel-face-spike @ 695a3fc0: `git diff <mb>..tip -- kernel/`
  EMPTY (0 files). Doc/context only. Pin 0.9 unchanged.
- origin/rowan/kernel-face-spike-2 @ 0a82f58c ("nothing wired"): kernel/ diff EMPTY.
- kernel/src/main.rs on opencode/500-s2: only mentions of "framebuffer" are
  the doc comment "No pixel framebuffer exists under bootloader 0.9.35".
  Nothing constructs a Framebuffer at boot; no fb: serial line exists.
- No origin ref carries KF-03 wiring / KF-04 pixel console / KF-05 graphics
  boot / KF-06 ribbon / KF-07 animation / KF-08 fallback flag / KF-09 window
  primitives / KF-10 shell-in-window code. Rowan has not landed any of it.

## Per-task verdicts
- OC1B-051 (KF-02 gate on upgraded stack): BLOCKED — no upgraded stack
  exists (KF-01 landed no candidate). Deciding file: this file.
- OC1B-052 (KF-03 wiring boot): BLOCKED — missing Rowan KF-03 wiring branch.
- OC1B-053 (framebuffer geometry): BLOCKED — same missing branch; no fb: line.
- OC1B-054 (KF-03 first draw): BLOCKED — same; no capture taken (nothing to capture).
- OC1B-055 (red fill): BLOCKED — Rowan fill-test branch (KERNEL_FACE_TASKS A4) missing.
- OC1B-056 (blue fill): BLOCKED — same.
- OC1B-057 (KF-04 pixel text): BLOCKED — missing Rowan KF-04 pixel-console branch.
- OC1B-058 (pixel vs VGA legibility): BLOCKED — same; no screendumps to compare.
- OC1B-059 (pixel scroll): BLOCKED — same.
- OC1B-060 (KF-05 3-screendump set): BLOCKED — missing Rowan KF-05 branch.
- OC1B-061 (text-phase claims before graphics): BLOCKED — same.
- OC1B-062 (KF-06 ribbon): BLOCKED — missing Rowan KF-06 boot-screen branch.
- OC1B-063 (ribbon vs js/logo-background.js): BLOCKED — same; no comparison possible.
- OC1B-064 (KF-07 two phases): BLOCKED — missing Rowan KF-07 animation branch.
- OC1B-065 (keypress exit): BLOCKED — same.
- OC1B-066 (KF-08 fallback boot): BLOCKED — missing Rowan KF-08 fallback branch/flag.
- OC1B-067 (shell answers on fallback): BLOCKED — same.
- OC1B-068 (KF-09 window frame): BLOCKED — missing Rowan KF-09 primitives branch.
- OC1B-069 (KF-10 status in window): BLOCKED — missing Rowan KF-10 branch.
- OC1B-070 (KF-10 mem in window): BLOCKED — same.
- OC1B-071 (KF-10 ps in window): BLOCKED — same.
- OC1B-072 (window vs serial cross-check): BLOCKED — same; no number sets exist.
- OC1B-073 (gate GREEN on KF-10 tree): BLOCKED — same; no KF-10 tree to gate.
- OC1B-074 (panic counts across §3 boots): NOT RUN — zero §3 boots exist, so
  the per-boot count table is empty (0 boots, 0 panics observed, 0 asserted).
- OC1B-075 (§3 verdict block + commit): verdict block = this file; commit sha
  recorded in os-build/logs/OC1B-s2-STATUS-SNIPPET.md on push.

No face/web work was done. No kernel code was written. kernel/src/syscalls.rs
untouched (no branch gated in §3; nothing to diff — stated, not quoted, with
the §2/§5/§6 empty diffs on record in OC1B-kf01-decision.md, OC1B-k3-tree.txt,
OC1B-k4-tree.txt).
