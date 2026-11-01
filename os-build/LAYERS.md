# Meta OS — who owns which layer (index, 2026-11-01)

The boss's order 2026-11-01 (~08:18): the OS build goes parallel by
layer, and everyone works from their own layer document. This page is
the index. Meta OS is an actual operating system with its own kernel;
the programs (Imperium, Custos, Musica, Scientia, Officina) run ON it
and are not the OS. The Debian image is a development carrier only.

| Layer | What it is | Who | Their document |
|---|---|---|---|
| 0 | Kernel (Rust) | Rowan writes, OpenCode compiles + QEMU-proves on the Mac | `ROWAN_LAYER0_TASKS.md`, `OPENCODE_OS_BUILD.md` |
| 1 | System services (Goose) | Pax shapes + writes, Buffy worklist + services | `os-build/layer1/K6_SERVICE_SHAPE.md`, `BUFFY_LAYER1_TASKS.md` |
| 2 | Agents + apps (Lobster) | Hana shell + apps, Milo agent process model + gate-1 + scoreboard | `HANA_LAYER2_TASKS.md`, `MILO_LAYER2_TASKS.md` |

Rules that bind every layer: NO MOCKS (KERNEL_SPEC rule 6). All
merges to main go through Pax personally. Milo is gate-1 for every
branch. Kernel claims count only with a Mac QEMU boot log. Status
words are used exactly: DESIGNED / WRITTEN / COMPILED / VERIFIED /
NOT BUILT / BLOCKED, with the blocker named.

State at this writing (2026-11-01 ~09:00): K1 kernel crate on main,
UNCOMPILED — the Mac boot proof is still outstanding. K2 framebuffer
and K3 interrupts merged unwired (6c29370b), gate-1 green, not a boot
verdict. Layer 1 shape DESIGNED (this folder); first services NOT
BUILT. Layer 2 shell spec-only until real OS state exists. The
cybersecurity/IT program stays PARKED until the OS is done and the
boss defines it — it is not a layer and nobody starts it.
