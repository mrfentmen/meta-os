# OC2P KF-02 plan — gate.sh → 0.11-stack evidence mapping (PREP ONLY, no execution)

- Date: 2026-11-03 UTC. Branch: `opencode2/landwalls`.
- Sources read in full: `os-build/gate.sh` (verified identical on `main` via
  `git show main:os-build/gate.sh` — diff empty), `os-build/logs/OC2P-kf01-corrected/VERDICT.md`,
  `serial.log`, `serial2.log`, `OC2P-kf01-boot.txt`, `OC2P-kf01-image.txt`.
- Stack proven by KF-01: `rowan/bootloader-spike @717e7ffb` (bootloader 0.11.17 + RK-008 rewrite).
- Status: BOOTS PAUSED by boss order until demo target ready. No QEMU/cargo/pip/network
  executed for this prep. Nothing committed.

## 1. Every assertion gate.sh makes

`os-build/gate.sh` lines (R4-1, 58 lines total):

- L39 boot-loop break (not a `check`, but a gate): `grep -aq "sleeper: bad call refused" "$LOG"`
  — boot is not considered complete until this K6 bad-syscall-99 line appears (480 s deadline).
- L48 `check()` helper: `grep -aq "<pattern>" "$LOG"`, prints `ok` or `FAIL`, sets `fail=1`.
- L49 `check "META OS KERNEL - alive"   "K1 alive"`
- L50 `check "mem summary: K4 up"       "K4 memory"`
- L51 `check "HELLO FROM USERSPACE"     "K6 ring 3"`
- L52 `check "user exit code 0"         "K6 clean exit"`
- L53 `check "task killed"              "K6 fault isolation"`
- L54 `check "user readkey: entry"      "readkey spawned (R5-2 follow-up)"`
- L55 `check "commands: status help"    "shell answered"`
- L56 `check "STATUS tasks="            "status reported live state"`
- L57 negative: `if grep -aq "loader refused" "$LOG"; then FAIL userspace refused; fail=1; fi`
- (Non-serial steps: toolchain versions, userspace 4-bin build, `cargo bootimage`,
  QEMU headless boot, `drive.py --monitor help status`. No other greps.)

## 2. Per-assertion mapping vs OC2P-kf01 0.11 evidence

Line numbers below are `serial2.log` (evidence boot WITH drive.py attach, 2087 lines, 50902 B).
`serial.log` (first boot, no drive.py, 2081 lines) matches except where noted.

| # | gate check (pattern) | verdict | exact serial quote / gap reason |
|---|---|---|---|
| 0 | boot-break `sleeper: bad call refused` (L39) | PRESENT | `L98: sleeper: bad call refused` (preceded by `L97: user bad syscall 99 refused`). Also in serial.log L99. K6 bad-syscall-99 refusal path works. |
| 1 | `META OS KERNEL - alive` (K1) | PRESENT | `L25: META OS KERNEL - alive (K1)`. serial.log L25 identical. |
| 2 | `mem summary: K4 up` (K4) | PRESENT | `L44: mem summary: K4 up`. serial.log L44 identical. |
| 3 | `HELLO FROM USERSPACE` (K6 ring 3) | PRESENT | `L52: HELLO FROM USERSPACE`. serial.log L52 identical. |
| 4 | `user exit code 0` (K6 clean exit) | PRESENT (x3) | `L53, L99, L2081: user exit code 0` (hello + sleeper + readkey-done). serial.log also x3. |
| 5 | `task killed` (K6 fault isolation) | PRESENT | `L63: INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed` (crasher null-read isolated, boot continues). serial.log L63 identical. |
| 6 | `user readkey: entry` (R5-2) | PRESENT | `L70: user readkey: entry 0x630000000010 head [48, 83, ec, 38, 48, bf, 53, 44, 01, 00, 00, 63, 00, 00, 48, b8]`. serial.log L70 identical. |
| 7 | `commands: status help` (shell) | PRESENT in serial2, MISSING in serial.log BY DESIGN | `L2084: commands: status help uptime mem ps` — appears only after drive.py types `help` (serial2 tail: `help` L2083 → commands L2084). serial.log count 0: no drive attach on that boot, so absence is expected, not a gap. |
| 8 | `STATUS tasks=` (live state) | PRESENT in serial2, MISSING in serial.log BY DESIGN | `L2087: STATUS tasks=8 ticks=5507 heap_free_kb=255` (after typed `status` L2085 → `tasks 8 ticks 5507 heap_free 255K` L2086). serial.log count 0, same reason as #7. Note: `ticks=`/`heap_free_kb=` vary per boot — grep the `STATUS tasks=` prefix only. |
| 9 | NEGATIVE `loader refused` must be ABSENT | PASS (absent) | count 0 in both serial.log and serial2.log. Also 0 `panicked`/`PANIC`/`triple fault` (see boot.txt grep block). |

## 3. Mappability summary

- **10/10 gate serial assertions already evidenced** in the drive-attached 0.11 boot
  (`serial2.log`): 8 positive `check`s + negative `loader refused` absence + L39 boot-break trigger.
- **8/10 in the pre-drive boot** (`serial.log`): everything except the two interactive lines
  (#7, #8), which require the drive.py typing step — expected, documented, not a content gap.
- **0 MISSING**: no gate pattern lacks a verbatim 0.11 serial quote. No seeded-RNG or
  missing-userspace-program gap applies — all four userspace bins (hello/sleeper/crasher/readkey
  at 0x600000000000–0x630000000000) are in the serial stream.
- Known automation gap (not a content gap): gate.sh verbatim CANNOT run the 0.11 stack —
  its `(cd kernel && cargo bootimage)` step fails by design on 0.11
  (`Bootloader dependency not found`, exit 1, per build log L85–391) and its QEMU line points at
  `kernel/target/.../bootimage-metaos-kernel.bin`, which 0.11 never produces (KF-01 used host
  imgtool `BiosBoot::new` → `/tmp/oc2p-kf01/metaos-bios.img`). The runbook therefore documents
  the KF-01-variant recipe, not gate.sh verbatim. Execution day must not "fix" this by editing
  `kernel/` (Rowan's pen).

## 4. What execution day still must prove (KF-02 gate, Pax's call pending)

1. Triple-boot stability: same 10-row checklist GREEN on 3 consecutive fresh boots
   (single BOOT ≠ KF-02; OC2B precedent: OC2B-034 triple boot + alive lines).
2. `gate.sh`-equivalent GREEN under the 0.11 recipe (or an updated gate.sh if Pax/Rowan name one).
3. Fresh screendump set + `STATUS`/`ps` drive exchange per boot (runbook §5–6).
