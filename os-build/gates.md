# Gates (ML4-2 / M-1, M-3)

Run from the repo root. Every grep line must print at least one
match; a silent grep is a NO. All lines verified against
`os-build/logs/` on main f496bdb, 2026-11-01 ~20:40 EST.

## Boot-log gate: the exact grep line proving each milestone

- K1: `grep 'META OS KERNEL - alive (K1)' os-build/logs/K1-boot.txt`
- K2: `grep 'META OS - milestone K2' os-build/logs/K2-boot.txt`
- K3: `grep 'META OS - milestone K3' os-build/logs/K3-boot.txt` and
  `grep 'INT exception page-fault' os-build/logs/K3-fault.txt`
- K4: `grep 'mem summary: K4 up' os-build/logs/K4-boot.txt`
- K5: `grep 'uptime .* ticks' os-build/logs/K5-boot.txt` — tick
  output only; NO K5 banner line exists in any log, so K5 has no
  banner proof and must not be quoted as if it had one.
- K6: `grep 'user hello: entry 0x600000000000' os-build/logs/K6-repro-main-2026-11-01.txt`
  and `grep 'HELLO FROM USERSPACE' os-build/logs/K6-repro-main-2026-11-01.txt`
  and `grep 'INT user page-fault' os-build/logs/K6-repro-main-2026-11-01.txt`
- K7: no K7 banner (K7-boot.txt exists, 74 lines). Banner ruling is K6, not K7. Any K7 claim without a
  new log file is rejected on sight.

## Per-merge checklist (Pax runs this unaided, in order)

1. Branch off current origin/main; never force-push, never merge to main (Pax merges).
2. Run the boot-log gate above; every line prints a match, or the merge stops.
3. Every claim names its log file; a claim without a log is rejected.
4. Test counts quoted from a run on this branch, never inherited from another branch.
5. No FROZEN lane touched: META OPUS, META MERCATUS, META NUMMUS, META ACTA, bus-tools/*, tests/test_bus_admin_e2e.py.
6. Status words only: VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED.
7. Dead code counted, not rounded: framebuffer 576 + syscalls 484 = 1,060 dead lines.
8. Verdict posted in room 1 with the log file named; a RED verdict quotes the failing lines.
9. Pax merges; this branch never merges itself.
