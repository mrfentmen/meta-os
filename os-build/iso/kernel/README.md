# Lane F — our kernel beside the ISO (OPENCODE R5, branch agent-r5)

## F1. Artifact reference (binary NOT committed — by `.gitignore` rule)

The 17 MB ELF is a build output. `.gitignore` forbids `kernel/target/`,
`*.bin`, `*.elf`; copying it under `os-build/iso/kernel/` would bloat the
repo against that rule, so this lane records checksum + path + commit + size
(HARD RULE: prefer reference). Machine-readable sums: `ARTIFACT.sha256`.

| item | value (measured 2026-11-04, this Mac) |
|---|---|
| kernel ELF | `kernel/target/x86_64-unknown-none/debug/metaos-kernel` |
| size | 17588736 bytes (`wc -c`; `du` = 17M) |
| sha256 | `ae18cf4f6474c06cdbbb62a6137d460afec84b1cf0ba152167592634a52d6151` |
| built from | HEAD `f6827930e439c5b1e44895937ebf8477a8829dfd` (`git rev-parse HEAD`); kernel sources at same commit (`git log --oneline -1 -- kernel/src/` = `f6827930 Lane E: kernel milestone`) |
| from Lane E log | `kernel/BUILD_LOG.md:168-177` records `17588736 bytes` — MATCHES, no discrepancy adopted |
| disk image (recipe output) | `os-build/rk007/disk.img`, 20415488 bytes, sha256 `5f37c47523870196adaf29c944d4ccba9e86ddc5ec36be748d9033db855c43e4` — built, uncommitted build output per `kernel/BUILD_LOG.md:173` |
| bootloader pin | `0.11.17` (`kernel/BUILD_LOG.md:144`, `kernel/Cargo.lock`) |
| QEMU evidence | `kernel/logs/E-boot-vnc.txt` (`META OS KERNEL - alive (K1)` :26, `KF-03 framebuffer … (screen live)` :24, `STATUS tasks=9 …` :809), `kernel/logs/E-framebuffer.png` (1280x720) |

Verify: `shasum -a 256 kernel/target/x86_64-unknown-none/debug/metaos-kernel`
must print the sha above; `wc -c` must print 17588736. If either differs, it
is a different build — do not treat E's logs as its proof.

## F11. How to rebuild / select / revert / what is proven

Rebuild (Linux or Mac with nightly rust, from repo root):

```sh
export RUSTC="$(rustup which --toolchain nightly rustc)"
export PATH="$(dirname "$RUSTC"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly RUSTC_BOOTSTRAP=1
python3 os-build/userspace/build_userspace.py   # 5 bins, first-LOAD == base verified
sh os-build/rk007/build.sh                      # kernel ELF + 0.11.17 BiosBoot disk.img
```

Full recipe: `kernel/BUILD_LOG.md:147-166`; wrapper details: `os-build/rk007/build.sh`.

Select (only after the lead's two-green-boots call, F14): rebuild the ISO in
the Linux container with `METAOS_KERNEL=1` in the environment (patch:
`../grub/README.md` §F3), boot, pick `MetaOS kernel (experimental)`.

Revert: rebuild with the env var unset (default) — `grub.cfg` is then
byte-identical to today's; or delete `os-build/iso/grub/` + `os-build/iso/kernel/`
and the tree carries zero bytes of this lane.

Proven (by Lane E, not this lane): K1 alive, K2 framebuffer screendump,
K3 timer/keyboard/typed-`status`, K4 mem summary, K5 sleep/wake, K6
userspace exit + fault kill — quotes in `kernel/BUILD_LOG.md:179-189`
against `kernel/logs/E-boot-vnc.txt`. Known gap carried forward: no `user
bad syscall 99 refused` line in E's log (`sleeper.rs` no longer issues
syscall 99; refusal arm byte-identical, drill lives in unspawned
`badcall.rs` — `kernel/BUILD_LOG.md:190-194`).

## F6 pointer

Why this kernel cannot boot from the live-ISO chain today, and why the GRUB
entry ships DISABLED: `WHY_NOT_BOOTING.md` (this directory).
