# OC1B-k4 gate pack (OC1B-130..149) — measured 2026-11-02, OpenCode 1
# Tree: origin/rowan/kernel-k4-build @ 4a37f9987bba5a10efb3df7624a25eae8c38fc18
# Image sha256: e2a9bce2a82cf9a13ee35ac30abdb88b73f57142b8501b59127d0bf3d5c807d9
# (kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin,
#  11218944 bytes, built Mac-lane cargo 1.101.0-nightly + qemu 11.1.3)
# Build pipeline: hello 0x600000000000, sleeper 0x610000000000,
# crasher 0x620000000000, readkey 0x630000000000, then kernel bootimage.
# Full commands in OC1B-k4-build.log. No talker/listener bins exist anywhere
# (exhaustive origin scan: no talker.rs/listener.rs on any branch), so the
# K4 image boots the standard 4-program set. The gate-build swap (two demo
# slots for the pair) is NOT in Rowan's branch (build note says so) and doing
# it here would mean editing kernel/src/sched.rs — forbidden (no named request
# exists). The pair + swap are therefore BLOCKED pieces, named per task below.

## OC1B-130 build: PASS (bootimage produced, see hash above).

## OC1B-131 boot + serial: DONE
- Serial: OC1B-k4-gatepack-serial.txt (49642 bytes, 2078 lines).
- Gate point (`sleeper: bad call refused`) reached ~20s; shell driven
  (status/mem/ps typed via real keyboard path); QEMU stopped cleanly.

## OC1B-132..140 acceptance lines (checklist OC1B-k4-checklist.md): UNPROVEN
- `grep -c ipc` over the full serial = 0. No send line, no receive line, no
  refusal line exists because no program invoked syscalls 6/7 in this boot.
- OC1B-132 (send): UNPROVEN — missing Buffy talker (R11-273) + gate-build swap.
- OC1B-133 (receive): UNPROVEN — same missing pieces.
- OC1B-134 (payload equality): UNPROVEN — same.
- OC1B-135 (sender id): UNPROVEN — same. (Code fact, unbooted: sender is
  kernel-filled from current_id(), user.rs:164+; stated as code-inspected.)
- OC1B-136 (full box): UNPROVEN — same.
- OC1B-137 (dead destination): UNPROVEN — same.
- OC1B-138 (unmapped buffer): UNPROVEN — same.
- OC1B-139 (undersized buffer): UNPROVEN — same.
- OC1B-140 (empty receive): UNPROVEN — same.
- Each line above names the missing branch/piece: no origin branch carries the
  talker/listener pair; origin/rowan/kernel-k4-build carries no spawn swap.

## OC1B-141 non-blocking proof: UNPROVEN (no recv ever issued; nothing scheduled).

## OC1B-142 peer-discovery proof: UNPROVEN by boot.
- Mechanism on paper (design §6 as fixed by required change 1): peer ids are the
  gate build's fixed spawn-order ids published as named constants in the pair;
  each program learns only its own id via getpid. Not exercised — no pair.

## OC1B-143 mailbox clearing on exit: UNPROVEN by boot (no traffic to clear;
  code-inspected: exit_task clears the row's box, sched.rs).

## OC1B-144 mailbox clearing on KILL path: UNPROVEN by boot (same; code path
  named in build note §1.3: all removals funnel through exit_task).

## OC1B-145 squatting limitation: NAMED, NOT EXERCISED.
- Observed in this build: no task sent anything (zero ipc lines), so no slot
  was ever occupied. The limitation stands as the design states it (build note
  §1.2: no sender filtering in step 1, accepted knowingly). No live task was
  observed occupying the console's slot — because no IPC traffic exists at all.

## OC1B-146 copy semantics: UNPROVEN (named fallback — no sender-overwrite case;
  no pair to demonstrate it).

## OC1B-147 panic + shell: PASS (measured)
- `grep -c panic` = 0 over the K4 serial.
- Shell answered after the full run, serial line 2067:
  `STATUS tasks=8 ticks=5674 heap_free_kb=223`. Console alive throughout.

## OC1B-148 gate.sh on K4 tree: (run in /tmp/oc500-k4, result in OC1B-k4-gate.log)
- See OC1B-k4-gate.log for the verbatim GATE line. Text assertions listed there.

## OC1B-149 K4 20-min soak: NOT RUN
- Reason: zero acceptance legs proven (no pair, no swap) — looping
  talker/listener traffic is impossible, and soaking the idle pair-less tree
  would not gate anything. Named gap, not a skipped line.

## OC1B-150 verdict for Pax (one line per pinned line)
- send: UNPROVEN (no talker). receive: UNPROVEN (no listener).
- full box: UNPROVEN. dead destination: UNPROVEN. unmapped buffer: UNPROVEN.
- undersized buffer: UNPROVEN. empty receive: UNPROVEN.
- OVERALL: the K4 tree BUILDS (hash above), BOOTS, keeps all text claims GREEN
  with panic 0 — but the IPC acceptance pack is BLOCKED on (a) Buffy's
  talker/listener pair (R11-273, not on any branch) and (b) the gate-build
  spawn swap (not in Rowan's branch; editing it here is forbidden). Merge
  recommendation: DO NOT MERGE 4a37f998 as an IPC proof on this pack — it is a
  clean build+boot only. Re-gate when the pair + swap land on a Rowan branch.
- Tree sha: 4a37f9987bba5a10efb3df7624a25eae8c38fc18. Image sha256:
  e2a9bce2a82cf9a13ee35ac30abdb88b73f57142b8501b59127d0bf3d5c807d9.
  The serial came from a boot of THIS image (built 2026-11-02 ~11:16 UTC in
  /tmp/oc500-k4, detached at the tree sha above).
