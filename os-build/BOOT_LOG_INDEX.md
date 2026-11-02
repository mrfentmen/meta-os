# Boot-log index (Bond lane 3, kept current 2026-11-02)

This is the index of every file in `os-build/logs/`, built from the
directory itself. It exists so a claim can name a log without anyone
guessing which file is current.

Two rules for this index:

- A line count is the count this run read; it is not a claim about
  content quality.
- **Byte sizes are deliberately not hand-typed.** They rot the moment
  a log is regenerated. Run `wc -c os-build/logs/*` and compare; the
  provenance column is what this table is for.

Milestone words below are the file's name and first marker, not an
endorsement: several logs were re-run on newer trees, so a file named
`K1` can carry a `META OS 0.1 (K6)` banner.

## Build provenance (only what the log states)

A build id is listed only when the log or its own file name states one.
Nothing is inferred from a milestone name: a file called `K6` is not a
claim about which commit produced it.

| Log | Build named by the artifact | Note |
|---|---|---|
| `GATE-boot-main4702e5c.txt` | `main` @ `4702e5c` | the sha is in the file name and the gate transcript |
| `gate-run-main4702e5c.txt` | `main` @ `4702e5c` | full gate transcript for the same build |
| `gate-run-r5-1.txt` | R5 tree (no sha in the file) | the log names the run, not a commit |
| `K6-repro-main-2026-11-01.txt` | `main`, 2026-11-01 (no sha in the log) | the date is in the file name; the log carries no commit id |
| every other log | not stated | no commit id appears in the file, so none is claimed here |

## Milestone logs

| File | Lines | First kernel marker | What it proves / notes |
|---|---:|---|---|
| `K1-boot.txt` | 54 | `META OS 0.1 (K6)` then `META OS KERNEL - alive (K1)` | K1 alive line on a later tree; also reaches K4/K6 lines, so it is not a K1-only capture |
| `K1-boot-run1.txt` | 11 | `META OS KERNEL - alive (K1)` | K1 alive, run 1 of 3; SeaBIOS prefix only before it |
| `K1-boot-run2.txt` | 11 | `META OS KERNEL - alive (K1)` | K1 alive, run 2 of 3 |
| `K1-boot-run3.txt` | 11 | `META OS KERNEL - alive (K1)` | K1 alive, run 3 of 3 |
| `K2-boot.txt` | 14 | `META OS - milestone K2` (line 11) | K2 banner + alive line; also carries `META OS KERNEL - panic` at line 13, so this capture includes a panic |
| `K2-panic-drill.txt` | 14 | `META OS - milestone K2` (line 11) | K2 panic drill: banner, alive line, `META OS KERNEL - panic` |
| `K3-boot.txt` | 59 | `META OS KERNEL - alive (K1)` | K3 timer line (`K3 timer: 10 ticks after 407902 spins`), then K4 memory, K6 userspace and a typed `STATUS` |
| `K3-fault.txt` | 1,514 | `META OS KERNEL - alive (K1)` | K3 page-fault drill at `0xdeadbeef`; repeated exception lines show the old return-after-fault behaviour |
| `K3-break.txt` | 26 | `META OS KERNEL - alive (K1)` | K3 `int3`/breakpoint drill capture |
| `K3-doublefault.txt` | 34,270 | `META OS KERNEL - alive (K1)` | Pre-fix double-fault loop (one repeated line). **Not current behaviour** — the handler now halts after one line (`kernel/src/interrupts.rs:445-461`) |
| `K4-boot.txt` | 111 | `META OS KERNEL - alive (K1)` | K4 memory bring-up (`mem summary: K4 up`) plus 58 seconds of `uptime` lines |
| `K4-guard.txt` | 4,199 | `META OS KERNEL - alive (K1)` | Guard-test capture: repeated page faults at the probe address `0x700000000000` |
| `K5-boot.txt` | 56 | `META OS - milestone K3` (line 11) | K5 scheduler capture: `C sleeping 200 ticks`, `uptime` tick lines. **No K5 banner exists** — the banner string is the old K3 milestone |
| `K6-boot.txt` | 88 | `META OS KERNEL - alive (K1)` | K6 ring-3 run: `HELLO FROM USERSPACE`, `user exit code 0`, uptime lines |
| `K6-debug.txt` | 73 | `META OS KERNEL - alive (K1)` | K6 debug capture: memory up + uptime; no userspace marker in the first 73 lines |
| `K6-repro-main-2026-11-01.txt` | 103 | `META OS - milestone K3` (line 11) | Fresh K6 repro on `main` with the linker-flag fix; typed `STATUS tasks=7 ticks=805 heap_free_kb=31` at line 101 |
| `K7-boot.txt` | 74 | `META OS 0.1 (K6)` (line 1) | K7 demo session log (typed `STATUS`, `uptime`); **no K7 banner** — see the K7 note below |
| `K9-panic-detail.txt` | 5 | `META OS KERNEL - alive (K1)` | Panic-detail capture: alive line, then `META OS KERNEL - panic` |
| `K16-doublefault-fixed.txt` | 29 | `META OS KERNEL - alive (K1)` | Post-fix double-fault shape: timer line + memory up, no 34k-line loop — the current handler's behaviour |

## R5 and merge logs

| File | Lines | First marker | What it proves / notes |
|---|---:|---|---|
| `R5-soak.txt` | 70 | `META OS KERNEL - alive (K1)` | Readkey/soak run; STATUS at lines 57 and 60 |
| `R5-soak-final.txt` | 70 | `META OS KERNEL - alive (K1)` | Final soak capture; same STATUS shape |
| `R5-readkey.txt` | 85 | `META OS KERNEL - alive (K1)` | `user readkey: ... entry 0x630000000010`, `readkey: polling syscall 5`, `readkey: empty` — syscall 5 observed live at R5 |
| `MERGED-boot.txt` | 0 | — | **EMPTY FILE.** Zero content; it proves nothing. Fill or delete it |
| `MERGED-boot-2.txt` | 60 | `META OS 0.1 (K6)` | Merge capture with the full K6 set: hello entry, `HELLO FROM USERSPACE`, user page-fault `task killed` (line 45), `user bad syscall 99 refused` (line 52), `STATUS tasks=7` (line 60) |
| `GATE-boot-main4702e5c.txt` | 59 | `META OS KERNEL - alive (K1)` | Gate boot capture for main `4702e5c`; STATUS at line 59 |
| `gate-run-main4702e5c.txt` | 350 | `== toolchain ==` | Full gate transcript for main `4702e5c`: toolchain, userspace, kernel, boot, assert stages |
| `gate-run-r5-1.txt` | 350 | `== toolchain ==` | Full gate transcript for the R5 run |

## Pipeline, verify, shell and soak captures

| File | Lines | First marker | What it proves / notes |
|---|---:|---|---|
| `pipeline-boot.txt` | 73 | `META OS KERNEL - alive (K1)` | Pipeline boot capture; K6 userspace + uptime |
| `pipeline-run1.txt` | 33 | `== userspace ==` | Pipeline run: userspace + kernel build, then boot/check lines (`PASS: K2 banner` at line 7) |
| `verify-drill.txt` | 34 | `== userspace ==` | Verify drill: build stages and a `PASS: K2 banner` line |
| `O-shell.txt` | 139 | `META OS KERNEL - alive (K1)` | Shell session capture (uptime/STATUS) |
| `O-shell2.txt` | 307 | `META OS KERNEL - alive (K1)` | Longer shell session capture |
| `soak.txt` | 3,717 | SeaBIOS banner | Long soak capture; not summarised here beyond its size |
| `flakes.txt` | 3 | timestamp line | Flake record: timestamp + `pipeline: pass=14 fail=1` |
| `reboot-loop.txt` | 10 | `boot 1 alive=1` | Reboot loop: three boots, each `alive=1` |
| `install-tools.txt` | 23 | `install-tools: present: qemu` | Tool availability check (qemu/jq/ripgrep, ...) |

## Screenshots (not logs)

These are PNG captures; they are evidence of a screen, not serial
text, and must not be quoted as log lines:

`K2-boot.png`, `K2-console.png`, `K2-panic.png`, `K2-shell.png`,
`O-shell.png`, `pipeline-screen.png`.

## Subdirectory

`os-build/logs/R5-imperium/` holds four R5 Imperial artifacts:
`receipt.txt`, `incident.json`, `drill.log`, `package-sent.json`.
They are not boot logs and are indexed as a group.

## The K7 note (a real disagreement)

`os-build/gates.md:20` says **"K7: NO LOG"**. That is wrong about
existence: `os-build/logs/K7-boot.txt` exists (74 lines) and is used
as the shell-alignment target by `os-build/layer1/K7_ALIGN.md` and
`SCOREBOARD.md`.

What is true is narrower: **no K7 milestone banner exists**. The
file's first line is `META OS 0.1 (K6)`, and the gate's own K5 rule
already warns that tick output is not a banner. So the correct
statement is "no K7 banner", not "no K7 log". The gate line should be
corrected by its owner; this index does not edit it.

## What is missing

- No K7 banner log, as above.
- No K8 log of any kind.
- No boot log in this directory is from the framebuffer path; the
  face image has its own capture (`face-boot1.txt`, a Debian boot,
  834 lines) and that is not a Meta OS kernel boot.
- `face-boot1.txt` is listed here because it lives in this directory,
  but it proves the carrier image boots Debian, not the K-series.

## How to refresh this index

1. `ls os-build/logs` (the directory is the source, not this table).
2. For each new file, record what its own first marker line says. Do
   not copy a milestone from the file name.
3. Run `wc -c os-build/logs/*` if sizes are wanted; do not paste them
   back into this table.
