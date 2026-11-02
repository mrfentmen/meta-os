# ROWAN — OS BUILD-OUT (boss order 2026-11-02 02:22 EST)

Your lane: the bare-metal core, L1–L3. The claim sentence is the
spec; the kill list stands (no framebuffer, graphics, networking,
SMP, persistence, package manager, installer). Freeze 05:12 —
tonight's items are A; B–F are the build-out queue in order.
Every kernel task: code + boot log or it does not count.

## A. Tonight (from ROWAN_FINAL_PUSH — unchanged, first)
A1 Readkey merge pack hand-combined onto current main.
A2 Typed-bytes race fix written, ready to boot-test.
A3 Screendumps ride the Mac boot (banner, shell, attract).

## B. Keyboard and console depth
B1 Caps lock state + LED-agnostic indicator line in status.
B2 Shifted symbol map complete vs the scancode table; test log.
B3 Key repeat: hold-to-repeat with sane rate; boot proof.
B4 Console scrollback: page-up review of earlier lines; proof.
B5 Console line editing: left/right/home/end within the line.
B6 Long input: line longer than the screen wraps, never corrupts.
B7 readkey drain semantics: burst of keys delivered in order.
B8 Two-reader rule after the race fix: console vs readkey proof.
B9 Keyboard absent case: boot without a keyboard, no hang.
B10 Scancode fuzz: random byte storm, console survives; log.

## C. Scheduler and tasks
C1 Task table full (8/8) stress: spawn to the cap, refuse clean.
C2 Exit-path audit: every exit route re-tests TSS.rsp0 refresh.
C3 Sleeper fairness: wake order under contention; log.
C4 Yielder starvation check: busy task cannot starve console.
C5 Crasher variants: divide-by-zero, bad memory, bad syscall —
   each isolated, each logged, console answers after each.
C6 Priority question: document whether fixed priority is needed
   for the claim — recommendation only, no silent change.
C7 Uptime accuracy: ticks vs wall clock over a 10-min soak.
C8 ps truthfulness: every field vs the task struct, audited.
C9 mem truthfulness: frames_free vs the allocator's own count.
C10 status latency: keypress → answer ticks, measured.

## D. Memory
D1 Heap watermark reporting in mem (used/total, honest).
D2 Allocation failure path: graceful line, no red screen, proof.
D3 Per-task stack guard: overflow detected + named, not silent.
D4 Userspace load overlap check: two programs, adjacent bases.
D5 Fragmentation probe after spawn/exit cycles; numbers logged.

## E. Syscalls and userspace
E1 F1 table conformance test: 0–5 behave, 6–15 refused, logged.
E2 write syscall edge cases: empty, huge, bad pointer.
E3 sleep(0) and yield semantics pinned in spec + log.
E4 pid uniqueness across spawn/exit cycles.
E5 A fifth userspace program: `echo` (prints its args via write).
E6 A sixth: `spin` (bounded CPU burn, yields politely).
E7 Userspace README: how to write a program for Meta OS, with
   echo as the worked example (feeds the submission).
E8 syscalls.rs decision packet for the boss (wire vs delete,
   your recommendation on file — refresh against current main).

## F. Proof and soak
F1 60-minute soak with readkey enabled (post-fix), full log.
F2 Cold-boot ×10: ten boots, ten alive lines, zero panics table.
F3 Gate script additions: readkey asserts once unheld.
F4 Boot log pack: one folder per milestone state of main,
   indexed in os-build/logs/INDEX.md (with Milo on format).
F5 R5-reference README: confirm it still describes main truth.
