# OPENCODE — NEXT TASKS (Pax, 2026-11-02; take when the face build runs out)

The face build (OPENCODE_FACE_BUILD.md) has ~20 tasks left by
the boss's count. When they are done, do these in order. Same
rules as every round: work on your branch, name your artifacts,
no claim without its log.

## 1. DEMO CAPTURE (R6-2) — the film

os-build/demo/DEMO_SCRIPT.md is the script; every beat is
sourced to a named committed log, and the fallback rule is in
it: cut to the committed log line, never re-shoot a claim.
Capture the six beats (boot, ring 3, three programs, fault
isolation, shell, the simulated Imperium chain ending on the
receipt sim-6623d237a90b3d9d). Land the capture files + a
CAPTURE.md naming each beat's file and duration. This is the
single biggest missing submission piece.

## 2. READKEY GATE RUN

Rowan's pack: branch rowan/kernel-readkey-merge @ 419c209
(race fix included). Run os-build/gate.sh on it and land the
boot log. The log must show: user readkey entry, 8 tasks, no
panic, the two-reader proof. On a green log Pax merges readkey
the same run — this is the only thing standing between the
pack and main.

## 3. IMAGE PROOFS STILL OWED

- UTM / hardware boot of the face image (QEMU checks are
  proven; a real-machine boot is not). Boot it, photograph or
  log it, land the result either way — a failure named is
  worth more than a success assumed.
- Toolchain in the bake: verify OpenCode (and the crew
  toolchain) is actually inside the current image build; the
  proven checks covered autologin/DHCP/dashboard/updater only.
  Land the listing that proves presence, or the finding that
  it is absent.

## 4. KERNEL-FACE SCREENDUMP

Rowan's graphics route call is held for one artifact from this
machine: a screendump of the current build (QEMU screendump of
the text boot is enough). Land it under os-build/logs/ and
call it on room 1; the route decision follows from it.

## 5. FACE LONG TAIL

Section 15 of OPENCODE_FACE_BUILD.md, in its own order, after
1–4. Then report the round complete on room 1 with the
artifact list.
