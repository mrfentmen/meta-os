# BUFFY — OS + KERNEL LANE (boss order, 2026-11-02)

The boss put Buffy on the OS and kernel. These lanes are
chosen so her work lands beside Rowan's, not on top of it.

## The fence

- kernel/src/*.rs is ROWAN's write lane. Buffy does not edit
  those files. A change she believes the kernel needs goes on
  room 1 as a proposal to Rowan, with the reason.
- Buffy's ground: userspace programs, the OS services and
  their boot wiring, the userspace ABI spec and its tests.
- Merges: Pax, at checkpoints, from exact commits — and the
  standing gate holds: the B2.6 bridge fix (Round 9 blocker)
  goes green with evidence before Buffy's merges resume.
  Building is not blocked; merging is.

## 1. Userspace programs pack (L7)

The proven set is hello / sleeper / crasher. Grow it, one
program per proof:
- hog: allocates until the kernel says no — its boot-log line
  must show containment (the task dies or is refused, the
  shell still answers). The line format is specified BEFORE
  the program is written; the program is done when the log
  line matches the spec.
- talker + listener: two tasks exchanging through the
  kernel's existing means, or an honest record that the means
  does not exist yet (that record is a finding for Rowan's
  lane, not a workaround).
- quitter: exits nonzero — the shell's ps must show the exit
  state truthfully.
Each program: source under userspace/, its expected boot-log
lines written first, and a note of which claim it extends.

## 2. OS services boot wiring

Her 25 Goose services get a boot manifest: the order they
start, what each needs before it, what the system loses when
one is down. The manifest is a file the image lane consumes
(os-build/face/ reads it); Buffy does not rebuild the image.
Plus the failure table: for each service, the boot symptom
when it is missing — written from the service's own contract,
not invented.

## 3. The userspace ABI, specced from the code

kernel/src/user.rs holds the authoritative syscall dispatch
(syscalls.rs is FROZEN by ruling — do not touch it). Write
the ABI spec from what user.rs actually does: every call,
its arguments, its refusal behaviour (bad syscall 99 is the
proven example). Then tests that hold the spec to the code:
a call the spec names that the code does not refuse or serve
as written is a finding, filed on room 1 for Rowan.

## 4. Kernel-adjacent records

The kernel's own documentation brought current: memory.rs's
allocator behaviour, the task lifecycle in tasks.rs/sched.rs,
the fault path — read from the code, written as records in
os-build/, every claim tied to a file and line range. Where
the code and the older docs disagree, the code wins and the
disagreement is the finding.

## Order

1 (hog first — it extends the proven claim), 2, 3, 4.
Checkpoint per section on room 1.
