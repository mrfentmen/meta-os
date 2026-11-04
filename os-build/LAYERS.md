# Meta OS — the seven layers and who owns each (index)

> Judge-first index (2026-11-04, Lane H, R5). The OS is layers 1–6 only:
> Rust kernel (1–3) + Goose services (4) + Lobster runtime/shell (5–6).
> The image is a carrier: Xubuntu 24.04.5 base (5,211,408,384 bytes) plus
> 17,968 KiB payload theme+face (~0.35%) — it boots the carrier's Linux
> kernel, not ours (`os-build/LAYERS_TRUTH.md:A7-A8`,
> `os-build/iso/kernel/WHY_NOT_BOOTING.md`, GRUB entry DISABLED).
> Programs (layer 7) run on the host/carrier, never on our kernel
> (`os-build/KERNEL_SPEC.md:41-43`). Our kernel boots only its own disk
> image in QEMU (`kernel/logs/E-boot-vnc.txt:26` alive,
> `os-build/logs/K1-boot.txt:2` alive, `kernel/logs/E-framebuffer.png`
> 1280x720). Status words below are exact: DESIGNED / WRITTEN / COMPILED
> (build log path required) / VERIFIED (QEMU/process log path required) /
> NOT BUILT / BLOCKED. A claim without a path is deleted.

The boss's model, renumbered to SEVEN layers on his word 2026-11-01
~09:02 (the first cut drew three). Meta OS is an actual operating
system with its own kernel; the programs run ON it and are not the
OS. The Debian image is a development carrier only. Milestones
K1–K6 in KERNEL_SPEC.md are build steps, not layers.

| Layer | What it is | Who owns it | Their document |
|---|---|---|---|
| 1 — Boot | Bootloader hands the machine to the kernel | Rowan + OpenCode | `ROWAN_LAYER0_TASKS.md`, `OPENCODE_OS_BUILD.md` |
| 2 — Kernel core | Rust, ours, no_std: memory, scheduling, interrupts | Rowan writes, OpenCode compiles + QEMU-proves on the Mac | same |
| 3 — Drivers | Rust modules in `kernel/`: framebuffer console, keyboard, timer | Rowan | same |
| 4 — System services | Goose services on the kernel: supervision, updater, networking | Pax shapes + writes, Buffy worklist + services | `os-build/layer1/K6_SERVICE_SHAPE.md`, `BUFFY_LAYER1_TASKS.md` |
| 5 — Agent runtime | Lobster: agent processes, identity, lifecycle, capabilities, audit | Milo | `MILO_LAYER2_TASKS.md` |
| 6 — Shell and apps | Lobster: the home surface and app side, real OS state only | Hana | `HANA_LAYER2_TASKS.md` |
| 7 — Programs | Imperium, Custos, Musica, Scientia, Officina — applications on the OS | program lanes (not an OS layer team) | repo worlds under `os/worlds/` |

File names, task IDs (B-L1-*, ML-L2-*, RW-L0-*), branch names, and
folder paths (`os-build/layer1/`, `os-build/layer2/`) keep the old
digits as stable identifiers from the 3-layer draft. Only the layer
numbers in prose changed.

Rules that bind every layer: NO MOCKS (KERNEL_SPEC rule 6). All
merges to main go through Pax personally. Milo is gate-1 for every
branch. Kernel claims count only with a Mac QEMU boot log. Status
words are used exactly: DESIGNED / WRITTEN / COMPILED / VERIFIED /
NOT BUILT / BLOCKED, with the blocker named.

State at this writing (2026-11-04, Lane H update to Lane A truth audit
`os-build/LAYERS_TRUTH.md`, plus lanes B–G deltas; the 2026-11-01 paragraph
below is kept as dated history, do not use its K/L4 claims):

| Layer | What exists | Status | Evidence path | What is missing |
|---|---|---|---|---|
| 1 — Boot | `bootloader` dep pin + `kernel/build.rs`; hands machine to kernel in QEMU | VERIFIED | `os-build/logs/K1-boot.txt:2` (`META OS KERNEL - alive (K1)`); R5: bootloader `0.11.17` (`kernel/BUILD_LOG.md:144`) + `os-build/rk007/disk.img` BiosBoot path (`kernel/logs/E-boot-vnc.txt:4-23`) | Bare-metal boot; UEFI/GOP path (target only) |
| 2 — Kernel core | `kernel/src/main.rs`, `memory.rs`, `mem.rs`, `sched.rs`, `tasks.rs`, `traps.rs`, `gdt.rs`, `user.rs`, `interrupts.rs` | VERIFIED | `os-build/logs/K1-boot.txt:19-25` (K4), `:26-28` + `:54` (K5), `:33-34` + `:51` + `:53` (K6 behavior) | Goose-service load (K6 last clause, `os-build/KERNEL_SPEC.md:96-100` open) |
| 3 — Drivers | `kernel/src/vga.rs` (`VGA_PHYS_ADDR 0xB8000`), `framebuffer.rs`, `icons.rs`, `logo_frames.rs`; R5 adds `kernel/src/pci.rs` (read-only scan) + demand paging + `readkey` | VERIFIED (VGA text + R5 1280x720 Bgr framebuffer under bootloader 0.11) | `os-build/logs/K2-boot.png` + `K2-shell.png`; `os-build/logs/K3-boot.txt:3` (timer), `:39` (scancode), `:54` (STATUS); R5: `kernel/logs/E-boot-vnc.txt:24` (`KF-03 framebuffer: 1280x720`), `kernel/logs/E-framebuffer.png`, `:118-125` (6 PCI devices incl. IDE 8086:7010), `:175-180` (demand `page mapped, retry` + containment), `:811-817` (kernel IPC self-test, NOT ring-3 gate) | Graphics modesetting of its own, PCI/storage/net/USB drivers, mouse/ACPI (`kernel/BUILD_LOG.md:219-239`; Lane A A3 pre-pci.rs, now read-only scan only; no `cap_query`, no sector read) |
| 4 — System services (Goose) | 183 `.goose` (88 in `services/tests/`); R5: 22 services COMPILED + 18 libs COMPILED, 3 NOT BUILT | COMPILED (22+18) / NOT BUILT (3: `registry`, `devmgr`, `sockets` README-only) | `services/BUILD_MATRIX.md:7-32` (per-service `BUILD_LOG.txt` + blocker) + `services/common/BUILD_LOG.txt` (libs); toolchain `/opt/homebrew/bin/goose` | Any `.elf` loaded by kernel; K-ipc shape OPEN; MANIFEST row 16 `sockets`→`socket` edit owed to manifest owner |
| 5 — Agent runtime (Lobster) | 11 top-level `.lobster` demos + `lobster/runtime/rt_*.lobster` contracts; host-interpreter workflow only | WRITTEN (host-only, max) | `lobster/RUNTIME_CONTRACT.md` + `lobster/run-tests.sh` (9/9 green); `lobster/roundtrip.log:1-3`, `lobster/host.log:1-4` (host text, not kernel) | Kernel mediation (no gate in `kernel/src/user.rs` table 0-6, no serial-log proof) |
| 6 — Shell and apps (Lobster) | Demos only (`lobster/homes/*/note.txt`, `bus-send`/`bus-recv` pattern); no home-surface program on kernel | NOT BUILT | `ls lobster/homes lobster/*.lobster` (demos, not a shell); layer-6 spec-only until real OS state exists | Shell binary, app side, any OS state beyond host files |
| 7 — Programs | `server/*.mjs`, `agents/*.mjs`, `relay/relay.mjs`, `server/queue/*.py`; run on host + Debian carrier, never on our kernel | VERIFIED (host) / NOT BUILT (on OS) | `os-build/face/provision.sh:232-303` (carrier runs python3 services); `os-build/image-status-2026-11-02.md:1-40` | Any program as kernel-loaded ELF; any program calling `kernel/src/user.rs` table 0-6 |

Dated history (2026-11-01 ~09:05, superseded 2026-11-02 QEMU proofs — keep,
do not cite as current): Layer 2's K1 crate was UNCOMPILED, K2–K6 BLOCKED,
Layer 4 shape DESIGNED / first services NOT BUILT, Layer 6 spec-only.
See `os-build/LAYERS_TRUTH.md:A12` for the stale-claim list.
K6 is PARTIALLY PROVEN (all behavior lines present, Goose clause open —
`os-build/KERNEL_SPEC.md:94-100`, `os-build/KERNEL_STATUS.md:47-49`).
Nothing from layers 1–6 reaches the image: no `goose`/`lobster`/`crates`/
`cargo`/`kernel` bytes ship except the Ubuntu base's own `lib/modules`
transplant (`os-build/LAYERS_TRUTH.md:A7`); payload is theme + face only
(A8: 0.353%). `sh os-build/tools/verify_tree.sh` → MISSING (rc=127,
BLOCKED per `os-build/LAYERS_TRUTH.md:A10`); `sh
os-build/identity/deubuntu-gate.sh .` → PASS (rc=0, 2026-11-04).
