# Meta OS kernel (layer 0, Rust)

Status: **BUILT and BOOTED — K1, K4, K5 and K6 proven in QEMU; K2 and K3 not proven yet.**
The build recipe, the toolchain, the artifact hash and the line-by-line evidence are in
`BUILD_LOG.md`; the milestone matrix is `os-build/KERNEL_STATUS.md`; the captured serial log is
`os-build/logs/K1-boot.txt`.

This README used to say UNCOMPILED. That stopped being true on 2026-11-02, so the sentence is
replaced rather than annotated.

## Build and boot (on this Mac)

The one thing that is easy to get wrong: `cargo` in the shell is Homebrew's, and it has no
`core` for `x86_64-unknown-none`. Pin the toolchain, including for the cargo processes
`bootimage` spawns:

```sh
cd kernel
export RUSTC="$(rustup which --toolchain nightly rustc)"
export PATH="$(dirname "$RUSTC"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly
rustup component add rust-src llvm-tools-preview --toolchain nightly
cargo bootimage
```

Or run the wrapper, which does the same and then checks the log:

```sh
os-build/layer1/build_kernel.sh
```

## Boot it

```sh
qemu-system-x86_64 \
  -drive format=raw,file=target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin \
  -serial file:../os-build/logs/K1-boot.txt -display none -m 256M -no-reboot
```

Watch for `META OS KERNEL - alive (K1)`. That line, in a serial log from this binary, is the K1
proof — and it is now in the repo.

## What is proven, and what is not

- **Proven by the committed log:** K1 alive, the K4 memory/paging/heap summary, K5 task
  rotation with sleep, K6 userspace ELF load, a syscall refusal, and a page fault that kills
  the offending task.
- **Not proven:** K2 (the VGA console draws to a screen this boot did not capture) and K3's
  timer/keyboard lines (the timer is clearly firing — sleep works — but no tick or key line is
  in the log). Do not cite them as done.

Kernel evidence is still only a build plus a boot log. A green service suite or a passing npm
run says nothing about this crate.
