# Clean-clone build proof — 2026-11-02

Question: does `main` build and boot from nothing but the committed tree?

Every kernel build before this ran in the working tree, with staged userspace ELFs, populated
`target/` directories and whatever local state had accumulated. A fresh machine has none of
that, and the failure looks like a code error when it is not.

## How it was tested

`os-build/layer1/clean_clone_check.sh` clones `HEAD` with `git clone --shared` into a temp
directory — committed files only, no ignored files, no working-tree changes — then, inside
the clone:

1. `cargo build --target x86_64-unknown-none --bins` in `os-build/userspace/user` (all seven bins),
2. `cargo bootimage` in `kernel/`,
3. boots the resulting image in QEMU and requires `META OS KERNEL - alive (K1)`.

## Result

```
clean_clone_check: cloning HEAD into /var/folders/.../T/tmp.JpGPvftwaP/clone
clean_clone_check: userspace bins
clean_clone_check: kernel image
clean_clone_check: boot
clean_clone_check: PASS — clone built and booted (44 serial lines)
```

**PASS.** The committed tree alone is enough: no staged ELF, no ignored file, no local
configuration. The 44 serial lines are fewer than the 55 in `K1-boot.txt` because this run
stops 8 s after boot and does not type a command — the milestone lines (alive, memory map,
heap, A/B/C) are present.

## What this does not prove

- No node suite and no Goose corpus: they need tooling this script does not install, and
  their absence is not a build failure.
- The toolchain is this machine's nightly. The script checks that one exists and uses it;
  it does not pin a version beyond what `kerneL/BUILD_LOG.md` records.
- The clone is local (`--shared`), so it proves file completeness, not network cloning.
