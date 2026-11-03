# Booting MetaOS — on the 32GB MacBook, not here

The 8GB machine writes the code and never boots it. This page is the whole
procedure for the machine that does.

## 0. What you need

- the repo, on a branch that has both halves of the boot flow
- `rustup` with the `nightly` toolchain, `rust-src` and `llvm-tools-preview`
- `qemu-system-x86_64`
- `python3`

The two halves:

| Piece | Branch |
|---|---|
| the boot kit and the verdict tool | `bond/12h` (`iso/tools/`) |
| the 0.11 image builder | `bond/rk007` (`os-build/layer1/rk007-builder`) |

If both are merged into `main` by the time you read this, take `main` and
ignore `--builder` below.

## 1. Check the machine

```
iso/tools/boot_kit.sh --check
```

It prints one row per tool and exits 1 if anything is missing. Install what it
names; do not debug the build until this is clean:

```
rustup component add rust-src llvm-tools-preview --toolchain nightly
```

## 2. Build

```
iso/tools/boot_kit.sh --build --out /tmp \
  --builder ../metaos-rk007/os-build/layer1/rk007-builder
```

Four steps, stopping at the first failure:

1. userspace binaries — the kernel's `build.rs` embeds them, and it panics with
   the exact path it wanted if they are absent
2. kernel ELF — `cargo +nightly build --target x86_64-unknown-none`
3. image builder — `cargo +nightly build`
4. disk image — the builder turns the ELF into a raw BIOS image

Expected tail:

```
OK       userspace binaries         hello, sleeper, crasher
OK       kernel ELF                 7132152 bytes
OK       builder                    .../rk007-builder
OK       image                      /tmp/metaos-rk007.img (9929728 bytes)
```

These are the counts measured on 2026-11-03. They move with the kernel: the
image grew from 6,784,000 to 9,929,728 bytes when the user programs were
embedded. What matters is that all four
rows say OK and the image is non-zero.

## 3. Boot it

The kit prints the exact command. It is:

```
qemu-system-x86_64 -drive format=raw,file=/tmp/metaos-rk007.img \
  -serial file:/tmp/boot.txt -display none -no-reboot -m 512M
```

Give it ~20 seconds, then stop it. `-display none` is deliberate: the serial
log is the proof, not a window.

## 4. Judge it

```
python3 iso/tools/boot_log_verdict.py /tmp/boot.txt
```

Nine rows. Seven must be present, two must be absent:

| row | must be |
|---|---|
| banner, alive, memory, ring3, exit, fault, shell | present |
| panic, refused | absent |

`verdict: PASS` and exit 0 is the boot proof. Anything else names the row that
failed, which is the finding.

## 5. If it fails

- Keep `/tmp/boot.txt` exactly as it was written. Do not retype it.
- Do **not** edit `kernel/src` to make it pass. That is Rowan's lane and
  `syscalls.rs` is frozen.
- File the log and the verdict output on the branch you were running.
- A red verdict with a real log is worth more than a green one without.

## What is still not proved after a green boot

A green serial log proves the kernel booted, dropped to ring 3, ran a program,
isolated a fault and answered the shell. It does not prove Plymouth drew, that
Calamares installed, or that a dock icon opened. Those need the Xubuntu base
image and a second VM run; they are separate acceptance lines in
`os-build/METAOS_1.0_RELEASE_CHECKLIST.md`.
