# Meta OS scoreboard — rewritten 2026-11-02 against artifacts

The previous version said L1 was WRITTEN and no boot log existed. That stopped being true on
2026-11-02, so the entries are replaced rather than annotated: a scoreboard that has to be
read alongside a correction is not a scoreboard.

Status words: **PROVEN** (a committed artifact shows the behaviour), **PARTIAL** (some clauses
evidenced, the missing one named), **HOST** (really runs, but not on our kernel),
**WRITTEN** (code exists, unproven), **NOT STARTED**.

| Layer | Status | Evidence |
|---|---|---|
| L1 Boot | **PROVEN** | `os-build/logs/K1-boot.txt` line 2, `META OS KERNEL - alive (K1)`. Recipe and artifact hash in `kernel/BUILD_LOG.md`. |
| L2 Kernel core | **PROVEN** | Same log: 15-region memory map, 127199 frames, paging probe, heap stress 10k, A/B/C rotation, 200-tick sleep/wake, ring-3 ELF load, `exit 0`, refused syscall, fault isolating the crasher. |
| L3 Drivers | **PROVEN** | VGA text console: `os-build/logs/K2-boot.png` (196 of 2000 cells carrying glyphs). Timer and keyboard: `K3-boot.txt` (`K3 timer: 10 ticks`, `K3 keyboard: first scancode 0x1f`, typed `status` answered). |
| L4 System services (Goose) | **HOST** | 33 Goose programs compile to C and run as host processes, 1253 checks, 0 fails (`os-build/layer1/SERVICE_RUNS.md`). Not booted: five syscalls are refused on purpose by the host shim. **This is the K6 gap.** |
| L5 Agent runtime (Lobster) | **HOST** | Node runtime, watchman, baton and registry with their tests (`tests/agents-*.test.mjs`). Host-side only. |
| L6 Shell and apps | **PARTIAL** | The kernel's own console shell runs real commands against real state (`status`, `help`, `uptime`, `mem`, `ps`, `clear`) — proven by the typed `status` in `K3-boot.txt` and the `ps` output in `K7-boot.txt`. The Lobster shell and the graphical home surface are spec-only. |
| L7 Programs | **HOST** | Imperium, Officina, Scientia, Musica, Custos run on the host. None boots on the kernel. `os-build/ROOT_MANIFEST.md` draws the line. |

## Corrections this rewrite makes to the old scoreboard

1. L1 was "WRITTEN, NOT BOOT-PROVEN" and claimed no K1 boot log existed anywhere. There are
   now three K1 logs (plus five older run files) and five milestone logs.
2. L2/L3 were "merged, unwired, nothing booted". Both are wired in `main.rs` and proven.
3. L4 was "DESIGNED, NOT BUILT" with no service source. The service corpus exists and runs on
   the host; the status that matters is HOST, not DESIGNED, and the gap is the kernel port.
4. L7 was "NOT STARTED". The programs exist and run; they are simply not on the kernel yet.

## What is still not true anywhere in this table

- No Goose service has a process on the kernel. Until one does, K6 is PARTIAL and layer 4 is
  HOST, whatever else is green.
- No disk, no persistence, no NIC: a reboot loses everything and the kernel cannot reach a
  network (`os-build/QEMU_LIMITS.md`).
- No real hardware boot. Every proof above is QEMU 11.1.3.
