# Meta OS — one-page status (2026-11-02)

Read this first. It is the shortest true statement of where the OS is; everything it cites
is in the repo.

## The OS is real, and smaller than the README used to imply

Meta OS has its own Rust kernel. It builds on this Mac, boots in QEMU, draws on the screen,
counts timer ticks, reads a keyboard, schedules tasks, and runs three ring-3 programs with a
shell that answers real commands. That is layer 1-3 plus the core of layer 2. The system
services (layer 4) are written in Goose and run as **host processes**; none of them has a
process on the kernel yet. That is the single most important sentence in this file.

## Milestones

| | Milestone | Status | Evidence |
|---|---|---|---|
| K1 | boot + alive line | PROVEN | `os-build/logs/K1-boot.txt` |
| K2 | console that draws | PROVEN | `os-build/logs/K2-boot.png` |
| K3 | interrupts, timer, keyboard | PROVEN | `os-build/logs/K3-boot.txt` |
| K4 | memory, paging, heap | PROVEN | `K1-boot.txt` (`mem summary: K4 up`) |
| K5 | tasks + scheduling | PROVEN | `K1-boot.txt` (A/B/C, sleep/wake) |
| K6 | syscalls + userspace | **PARTIAL** | `K1-boot.txt` proves ring 3, exit, refusal, fault isolation. **No Goose service process exists.** |

## Layers

| Layer | Status |
|---|---|
| 1 Boot | PROVEN |
| 2 Kernel core | PROVEN for what is built; no demand paging, no COW, no swap |
| 3 Drivers | PROVEN: VGA text, PIT, PS/2 keyboard. No serial driver beyond the debug port, no disk, no NIC |
| 4 Services (Goose) | **HOST** — 33 programs, 1253 checks, 0 fails, with 5 syscalls refused on purpose |
| 5 Agent runtime (Lobster) | HOST-side runtime and tests |
| 6 Shell and apps | PARTIAL — kernel console shell is real; Lobster/graphical shell is spec-only |
| 7 Programs | HOST — Imperium, Officina, Scientia, Musica, Custos run on the host, not on the kernel |

## What exists and is proven here today

- `kernel/` builds (`build_kernel.sh`), boots, and proves K1-K5 plus most of K6.
- The userspace ABI, the 22-service boot manifest (plus its JSON form) and the kernel records
  are specced from the code and checked against it (`USERSPACE_ABI.md`, `BOOT_MANIFEST.md`,
  `boot-manifest.json`, `records/`); negative tests prove the checkers fail on drift.
- Five userspace programs build: hello, sleeper, crasher, quitter, readkey, plus the writer
  and badcall drills. Only the first three are wired into the kernel — the rest need Rowan's
  `BINS` line and, for two of them, a raised stack-slot cap.
- `services/` compiles and runs 33 Goose programs as host processes, 0 failures.
- The double-fault drill now halts after one line instead of re-faulting (it used to emit a
  3.3 MB loop, which is a bug this round found and fixed).
- Panics carry message and location to the serial log.
- A keystroke from a real RFB client reaches the kernel's IRQ1 handler and runs a command.

## What does not exist, stated plainly

- No Goose service on the kernel. No disk. No filesystem. No network driver. No SMP.
- No real-hardware boot — every claim is QEMU 11.1.3 (`os-build/QEMU_LIMITS.md`).
- No persistence: reboot loses everything.
- The keyboard capture harness is timing-flaky; the proof is real, the reproduction is not
  guaranteed (recorded in `kernel/BUILD_LOG.md`).

## How to check any of it

```sh
os-build/layer1/build_kernel.sh      # build + boot + K1 gate
os-build/layer1/prove_k2_k3.sh       # screen + keyboard + timer evidence
os-build/layer1/check_all.sh         # kernel, os-boot, userspace bins, Goose corpus, doc checks
os-build/layer1/test_checkers.sh     # proves the checkers fail when they should
```

## The next three things, in order

1. One Goose service as a kernel process. Without it K6 is not done and layer 4 is host-only.
2. A block device and a minimal filesystem, proven by write → reboot → read.
3. Demand paging and COW, so a fault can be a promise instead of a kill.
