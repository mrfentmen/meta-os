# os-build: how to build and prove Meta OS on a Mac (OS-199/227)

One command does everything: `sh os-build/boot-test.sh` from the
repo root. It builds the userspace programs, the kernel, the boot
image, boots each milestone in QEMU, captures every serial log
under `os-build/logs/`, greps the expected lines from
`os-build/expected/`, prints PASS/FAIL per milestone, and runs
the Goose suite at the end. Nightly shape: this file IS the
nightly — run the one command, read the one report
(`os-build/OS_BUILD_REPORT.md`).

Fresh machine order (prerequisites, OS-149): Xcode CLT, Homebrew,
`sh os-build/install-tools.sh`, rustup + target + components,
`cargo install bootimage`, Goose + Lobster toolchains (see
`os-build/research/goose.md`, `lobster.md`), MCP wiring
(`os-build/mcp/WIRING.md`).

Fresh-reader test (OS-227): this file was followed from a clean
clone on 2026-11-01 (see the Section Q report block for stumbles
fixed).
