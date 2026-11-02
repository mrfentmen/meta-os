# OC1B-k3 gate pack (OC1B-103..124) — measured 2026-11-02, OpenCode 1
# Tree: origin/rowan/kernel-k3-build @ 7bb7207524d831811ce54bc5fcde7b43c2b4bed2
# Image sha256: 16c72550b91f274d37abeb92902079a8ca6f8f4a0481375318ace785eb993e07
# (kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin,
#  13749760 bytes, built Mac-lane cargo 1.101.0-nightly + qemu 11.1.3)
# Build pipeline (Rowan §4 note): hello 0x600000000000, sleeper 0x610000000000,
# crasher 0x620000000000, readkey 0x630000000000, demand 0x640000000000, then
# kernel bootimage. Full commands in OC1B-k3-build.log.

## OC1B-103 build: PASS (bootimage produced, see hash above).

## OC1B-104 boots
- Boot 1 serial: OC1B-k3-gatepack-serial.txt (50025 bytes, 2084 lines).
- Boot 2 serial: OC1B-k3-gatepack2-serial.txt (50025 bytes — same length).

## OC1B-105 demand leg part 1 — first fault on promised region: QUOTED
- Boot 1 line 58: `demand: touching promised page`
- Boot 1 line 59: `INT user page-fault addr 0x0000700000000000 err 0x0000000000000005: task killed`
- The fault IS on the promised page (0x0000_7000_0000_0000 = DEMAND_PAGE).
  BUT err = 0x5 = P=1 (present) + read + user: a PROTECTION fault, not the
  non-present (P=0, err-0x4-class) fault design §3 condition 1 requires.

## OC1B-106 demand leg part 2 — map/zero-fill line: ABSENT (FAILED)
- `grep -c "demand-fault\|page mapped"` over boot 1 serial = 0.
- No `INT user demand-fault addr ...: page mapped, retry` line exists.
  try_demand_map did not map; the fault fell through to the unchanged
  `INT user page-fault ...: task killed` line.

## OC1B-107 demand leg part 3 — resumed completion: ABSENT (FAILED)
- No demand exit line; no zero-fill/writeback prints. Demand died at first touch.

## OC1B-108 zero-fill check line: ABSENT (FAILED, same cause).

## OC1B-109 crasher containment — kill line: QUOTED (PASS)
- Boot 1 line 46: `INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed`
  (crasher's deliberate null read: P=0, read, user — the classic wild fault.)

## OC1B-110 containment part 2 — survivor after kill: QUOTED (PASS)
- Boot 1 line 49: `sleeper: yielded and back` (first sleeper line after line 46).
  The machine kept working. VGA frame (oc1b-k3-shell.png) further shows
  `sleeper: after sleep` and `sleeper: bad call refused` on screen.

## OC1B-111 outside-region negative part 1: UNPROVEN
- Demand was killed ON its promised page (line 59) before reaching its
  out-of-region touch. No outside-region fault line exists in either boot.

## OC1B-112 outside-region negative part 2: UNPROVEN (same reason).

## OC1B-113 no silent map for negative leg: PASS (vacuously, counted)
- Demand map lines in boot 1 serial: 0. Nothing was mapped for anyone.

## OC1B-114 panic grep: PASS
- `grep -c panic` = 0 on boot 1 serial. (Count measured, quoted here.)

## OC1B-115 shell after all three legs: PARTIAL
- status: QUOTED from serial line 2072: `STATUS tasks=9 ticks=6435 heap_free_kb=223`
  (boot 2: `STATUS tasks=9 ticks=6705 heap_free_kb=223` — ticks moved, live state).
- mem + ps: typed via real keyboard path (drive.py sendkey) in boot 2; answers
  visible on VGA, quoted from oc1b-k3-shell.png (viewed 2026-11-02):
  `mem frames_free 125802 frames_total 125887 heap_free 223K heap_total 512K`
  and 9 `ps` rows (ids 1–9; id 9 Exited = demand; console id 7 Running).
  Serial carries boot-time mem lines (21–26) plus the driven STATUS above.

## OC1B-116 mapper-root basis (observed, per build-note §2 + serial):
- Basis: ONE shared mapper root (mem::MAPPER); no per-task roots exist —
  enter_userspace never loads a per-task CR3 (Rowan build-note §2 correction).
  Isolation therefore rests on the per-task promised-region check, not roots.
- Observed on this boot: the check did not grant for the promised page (the
  class-1 P=0 test fails first: the page faults PRESENT/supervisor, err 0x5),
  and the wild null access was killed (err 0x4). Veterans: crasher contained;
  demand not serviced. Hypotheses for Rowan (not causes): something already
  maps 0x7000… as supervisor-only; or the loader/region-record path miskeys.
  Kernel code not touched — investigation is Rowan's.

## OC1B-117 gate.sh on K3 tree: GREEN (measured)
- Ran unmodified os-build/gate.sh in /tmp/oc500-k3 (detached @ 7bb72075):
  all 8 check lines ok (K1 alive, K4 memory, K6 ring 3, K6 clean exit, K6 fault
  isolation, readkey spawned, shell answered, status reported) + `GATE GREEN`.
  Full output: OC1B-k3-gate.log. (Spec says 7/7; the gate prints 8 ok lines —
  all 8 ok, quoted from the log. The demand ELF came from this lane's §4
  pipeline build immediately before; gate.sh itself builds the 4 base bins.)

## OC1B-118 second boot reproduce: SAME per leg
- Boot 2 serial byte-identical in length (50025) with the same leg lines:
  demand touch + kill err 0x5 (lines 58–59), crasher kill err 0x4 (line 46),
  STATUS answered (line 2072, ticks 6705 vs 6435 — live).
  Verdict per leg: demand SAME (failed), containment SAME (proven), negative
  SAME (unproven). Reproduction confirms the failure is deterministic, not a flake.

## OC1B-119 demand loop (10 faults): NOT RUN
- Reason: demand dies on its FIRST touch (err 0x5 kill); no resume exists to loop.
  A loop file would prove nothing. Named gap, not a skipped line.

## OC1B-120 K3 30-min soak: NOT RUN
- Reason: the demand leg FAILED — soaking a failed leg cannot gate anything.
  Named gap. (Machine-time note: two full K3 boots + gate run consumed instead.)

## OC1B-121 readkey on K3 tree: PARTIAL
- Spawned + polling PROVEN: `user readkey: entry` (line 53), `readkey: polling
  syscall 5`, and completion `readkey done got=0 empties=200000` (line 2067).
- Typed-byte received (got>0) UNPROVEN in these boots: no byte was typed into
  readkey's window (drive typed into the shell). Named gap within the task.

## OC1B-122 anti-loop guards: UNPROVEN
- No task faulting repeatedly on the same promised address was observed (demand
  faulted exactly once, then died). The build exposes no such case in these
  boots. Named UNPROVEN per the task's own fallback.

## OC1B-123 K3 gate-pack verdict for Pax
- Demand leg: FAILED (promised touch killed err 0x5; zero map lines; deterministic).
- Crasher containment leg: PROVEN (kill line 46 + survivor line 49 + VGA).
- Outside-region negative leg: UNPROVEN (demand died before its negative touch).
- Panic: 0 in both boots. Shell: answers status/mem/ps after the legs (VGA + serial).
- Merge recommendation the evidence supports: DO NOT MERGE 7bb72075 on this
  pack. Rowan to investigate why the promised page faults PRESENT/supervisor
  (err 0x5) at first touch instead of non-present. Re-gate after the fix.

## OC1B-124 tree sha + image hash
- Tree: origin/rowan/kernel-k3-build @ 7bb7207524d831811ce54bc5fcde7b43c2b4bed2.
- Image: sha256 16c72550b91f274d37abeb92902079a8ca6f8f4a0481375318ace785eb993e07,
  13749760 bytes. Both serials came from boots of THIS image (built 2026-11-02
  ~11:08 UTC in /tmp/oc500-k3, detached at the tree sha above).
