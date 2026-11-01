# Meta OS kernel (layer 0, Rust)

Status: **UNCOMPILED, UNVERIFIED.** Written in the sandbox, which
cannot build Rust. The first compile happens on the boss's Mac; the
first proof is a QEMU serial log, per KERNEL_SPEC.md at the repo root.

## Build and boot (on the Mac)

```
rustup target add x86_64-unknown-none
cargo install bootimage
cd kernel
cargo bootimage
cargo run
```

`cargo run` uses the bootimage runner: it builds the kernel, links it
behind the rust-osdev bootloader, and starts QEMU. Watch the serial
output for:

```
META OS KERNEL - alive (K1)
```

That line, in a QEMU serial log from this binary, is the K1 proof.
If the build errors, the errors are the next task: report them back
exactly, they get fixed in small commits, same as the service ports.
