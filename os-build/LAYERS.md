# Meta OS — the seven layers and who owns each (index)

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

State at this writing (2026-11-01 ~09:05): Layer 2's K1 crate is on
main, UNCOMPILED — the Mac boot proof is still outstanding, and R5
wiring of the Layer 3 drivers is BLOCKED on it plus the missing
`kernel/Cargo.lock`. The Layer 3 framebuffer + interrupts modules
are merged unwired (6c29370b), gate-1 green, not a boot verdict.
Layer 4's shape is DESIGNED; its first services are NOT BUILT.
Layer 6 is spec-only until real OS state exists. The cybersecurity
and IT program (Layer 7 class) stays PARKED until the OS is done and
the boss defines it — nobody starts it.
