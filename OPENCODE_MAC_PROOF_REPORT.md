# OPENCODE MAC PROOF REPORT — merged tree proven on the Mac

Boss order 2026-11-01 (via Pax): compile + QEMU-boot the merged
kernel tree. No new features, no fixes, no 8 PM test work.

## 1. Tip hash

`96277b6` — "Add OPENCODE_MAC_PROOF.md" (origin/main at pull time).
Worktree: fresh `/tmp/mac-proof` at detached HEAD 96277b6. The
B21 checkout was never touched.

## 2. Toolchain (per os-build/OPENCODE_K1_RUN.md)

- `rustc +nightly --version`: `rustc 1.101.0-nightly (f9ceb4a4d 2026-10-31)`
- nightly targets installed: `aarch64-apple-darwin`, `x86_64-unknown-none`
  (the target was missing and was added per the run sheet)
- nightly components installed: `llvm-tools`, `rust-src`
  (both were missing and were added per the run sheet)
- `bootimage --version`: `bootimage 0.10.5`
- `qemu-system-x86_64 --version`: `QEMU emulator version 11.1.3`

## 3. Userspace build (bins: hello, sleeper, crasher)

Command (task step 3, verbatim): from os-build/userspace/user,
`cargo build --target x86_64-unknown-none --bins` → exit 0, all
three ELFs produced and valid (ELF 64-bit LSB executable,
statically linked).

Follow-through (no source edits — repo's own documented flow):
the plain build links at the default base 0x200000, which
collides with the kernel's own mappings, so a first boot
correctly logged `user hello loader refused: address in use`
(x3). The repo's own pipeline (os-build/boot-test.sh lines 24-30)
builds each bin with its link script at a distinct high base, so
I ran exactly those commands (sed link-base.ld per bin +
RUSTFLAGS link-arg, touch, cargo build --bin): hello entry
0x600000000000, sleeper 0x610000000010, crasher 0x620000000140.
Kernel image rebuilt after to stage them. Recorded because step
3 as literally written is insufficient on its own; the working
flow already lived in the repo's script.

## 4. Kernel build

Command (task step 4, verbatim): from kernel/,
`cargo +nightly bootimage` → `Created bootimage for
metaos-kernel at .../target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin`,
8,505,344 bytes. Only warning: a future-incompat notice about
core (not an error). kernel/.cargo/config.toml untouched,
Cargo.lock untouched, bootloader stays 0.9.35 (build log shows
`bootloader v0.9.35`).

## 5-6. Three boots, verdicts vs os-build/expected/K-all.txt

Each boot: the step-5 QEMU command with the step-4 image path,
`-serial file:merged-boot-N.txt -display none -m 512M`, killed
after the full userspace sequence printed. K-all.txt holds:
alive (K1), milestone K3, mem summary, C awake, HELLO, sleeper:
after sleep, user exit code 0.

Boot 1 (`merged-boot-1.txt`): alive 1, milestone 1, mem summary
1, C awake 1, HELLO 1, after sleep 1, user exit code 2, bad-call
refused 1, task killed 1, panic 0 → PASS every line.
Boot 2 (`merged-boot-2.txt`): identical counts → PASS every line.
Boot 3 (`merged-boot-3.txt`): identical counts → PASS every line.

Best full log saved as os-build/logs/MERGED-boot.txt (boot 3,
5982 bytes).

## 7. Musica on the Mac

pretty_midi for /usr/bin/python3: already present, version
0.2.11.post0 (no install needed). From repo root:
`node --test tests/musica-export.test.mjs
tests/musica-products.test.mjs` → tests 4, pass 4, fail 0.

## Final line

MERGED TREE PROVEN.
