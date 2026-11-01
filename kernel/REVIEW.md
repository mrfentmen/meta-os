# K1 skeleton review (R1) — enemy review, not a pass

Status: **UNCOMPILED, UNVERIFIED.** Reviewed 2026-11-01 from main
`1145d4b` (branch `rowan/kernel`, first kernel-lane commit). The reviewer
VM has no Rust toolchain (`cargo`/`rustc` not installed), so nothing
here was compiled, and no boot log exists. Per KERNEL_SPEC.md, K1 is
done only when a QEMU serial log from this binary shows the alive line.

Files reviewed: `kernel/src/main.rs`, `kernel/Cargo.toml`,
`kernel/.cargo/config.toml`, `kernel/README.md`, plus repo-root
`Cargo.toml` (workspace members) and `Cargo.lock` (bootloader search).

Docs tooling: **NOT wired on this VM.** No rustdocs MCP connector is
available here (connector search returns unrelated MCPs only), so this
review is source-only against the files themselves and KERNEL_SPEC.md.
No smoke call is claimed. The Mac/OpenCode side owns the rustdocs MCP
smoke test for the kernel lane.

## Verdict

The skeleton is small and readable, and its risks are concentrated, not
diffuse: (a) the bootloader dependency is unresolved until a Mac build
produces a lockfile, (b) the serial path can hang silently, and (c) the
proof string in the spec does not match the code. None of these needs a
redesign. The next step is a Mac build, not more uncompiled code: R2
must be written against the bootloader version that build resolves.

## Assumptions, each with its proof

### A1 — bootloader 0.9 API shape (HIGH for K1)
`main.rs` uses `bootloader::entry_point!(kernel_main)` and takes
`&'static mut bootloader::BootInfo`. `Cargo.toml` pins `bootloader`
`version = "0.9"` with feature `map_physical_memory`. Assumes a 0.9.x
resolution provides exactly that macro, that entry signature, and that
feature name. Nothing in the repo proves it: see A2. Proof: the Mac
build's resolved version + a QEMU boot reaching the alive line. If the
macro or signature differs, the fix is a version pin or a small
entry-point edit, recorded in the same commit as the error.

### A2 — "the lockfile" does not exist yet (HIGH, blocks R2 as worded)
OS_BUILD_TASKS.md R2 says to write K2 "against the bootloader version
in the lockfile". There is no `kernel/Cargo.lock` in the repo, and the
repo-root `Cargo.lock` contains no `bootloader` package at all (it
covers the service workspace only). `kernel/Cargo.toml` declares its
own empty `[workspace]`, so the kernel resolves dependencies separately
on first build. R2 cannot be executed verbatim until the first Mac
build commits a resolved `kernel/Cargo.lock` (or a pinned version).
That lockfile commit is a prerequisite, not an afterthought.

### A3 — COM1 exists and QEMU wires serial (HIGH for K1 proof)
The code assumes a 16550 UART at `0x3F8` and that QEMU delivers its
bytes to a captured log. There is no presence check: on absent hardware
`inb` returns `0xFF`, and `0xFF & 0x20 != 0`, so `serial_write_str`
would happily "transmit" into nothing. Proof: a QEMU invocation with
serial explicitly captured (e.g. serial to stdio/file), not a bare
`cargo run` whose serial destination is assumed. If the log is empty,
that proves nothing by itself — see A4.

### A4 — the serial path hangs silently on failure (HIGH for diagnosis)
`serial_write_str` busy-waits on the transmitter-holding-register-empty
bit with no timeout, no fallback, and no second output channel. If the
UART is absent, misconfigured, or its status bit never sets, the kernel
hangs before printing anything and leaves zero diagnostic output. A
hang and a crashed-before-print kernel look identical. Acceptable for
a K1 skeleton, but the first "it printed nothing" Mac result must be
triaged as serial-path failure first, not as a boot failure. A later
milestone should add a bounded wait or a fallback channel; K1 does not
need it yet.

### A5 — panic handler assumes serial is already initialised (MEDIUM)
The panic handler calls `serial_write_str` unconditionally and drops
the panic info (no file, line, or message is printed). A panic before
`serial_init()` in `kernel_main` — or inside `serial_init` itself —
prints at whatever the UART reset state happens to be, or hangs per A4.
Also, a panic inside the handler itself aborts (profiles set
`panic = "abort"`), so there is no second chance. For K1 this is
acceptable; for debugging the Mac build it means panic output is
near-useless until init order is guaranteed. Do not "fix" this by
printing panic info in this review commit — it changes code, and code
changes belong in a build-error-driven commit.

### A6 — `map_physical_memory` is enabled but never consumed (MEDIUM, K4)
`BootInfo` is taken as `_boot_info` and never read, so the physical
memory map the feature requests is never exercised at K1. K1 therefore
proves boot + serial only; it proves nothing about the memory map K4
will depend on. When K4 lands, its first test must be that the map
actually arrives and is sane, not that the feature flag is present.

### A7 — interrupt state at entry is bootloader-defined, not kernel-defined (MEDIUM, K3)
The code neither enables nor disables interrupts and never issues
`hlt`; the end state is an infinite `spin_loop`. "Halts cleanly" in
the spec therefore means "spins forever without crashing", not a halt
instruction, and the CPU spins at full speed under QEMU. K3 must
explicitly define the interrupt state it expects on entry instead of
inheriting whatever the bootloader left.

### A8 — the proof string disagrees between spec, README, and code (MEDIUM, gate-blocking)
Code and `kernel/README.md` print/expect `META OS KERNEL - alive (K1)`.
KERNEL_SPEC.md says the kernel "prints META OS KERNEL alive on the
serial port" — no dash, no `(K1)`. Milo's gate (M1: exact boot-log
lines) cannot be written until one string is canonical. Recommendation:
align the spec to the code string in a follow-up commit (the code
string is the more specific one), and do not change the code string in
this review commit. Until then, any "K1 proven" claim must quote the
exact line it matched.

### A9 — build requires nightly + bootimage + QEMU, README omits two of them (MEDIUM, Mac build)
`kernel/.cargo/config.toml` sets `[unstable] build-std`, which
requires a nightly Rust toolchain, and the runner is `bootimage`.
`kernel/README.md` lists `cargo install bootimage` but names no
toolchain pin and no QEMU install step, and gives no serial-capture
command for the proof log. The Mac build's first job is to record:
nightly toolchain used, resolved bootloader version (see A2), QEMU
invocation, and where the serial log was captured. Those four facts
are the seed of `kernel/MAC_QUESTIONS.md` (R4); they are questions
here, not answers.

### A10 — repo suites do not cover the kernel (LOW for K1, HIGH for false confidence)
The root workspace `Cargo.toml` members list 19 service crates and
does not include `kernel/`; `kernel/Cargo.toml` declares its own
workspace. So a green workspace cargo suite, npm suite, or Custos
Python suite says nothing about the kernel. This commit changes only
this markdown file, so no suite outcome changes by construction — but
no suite result may ever be cited as kernel evidence. Kernel evidence
is only: Mac build success + QEMU boot log.

### A11 — scope limits that are fine at K1 (LOW, recorded so K2 does not re-litigate)
No framebuffer/VGA fallback, no CPU feature checks, no heap, no
keyboard/timer, no tests in `kernel/`. Long mode and a usable stack
are bootloader-provided and assumed, not checked in code. The `\n`
in the alive line has no `\r`, so log-capture tooling must handle a
bare line feed. The `outb`/`inb` asm uses `nomem, nostack,
preserves_flags`, which matches port IO (no memory operands); this
was checked and is not a concern. Baud divisor 3 (38400) assumes the
standard UART clock; under QEMU the baud rate is virtual and the byte
stream is what matters, while on real hardware the divisor matters —
another reason the QEMU log is proof for K1 only, not for hardware.

## What was NOT changed, deliberately
No kernel code was touched. A review that silently edits the code it
reviews destroys the baseline the Mac build is supposed to test. Code
changes follow Mac build errors, one per commit, per KERNEL_SPEC.md.
