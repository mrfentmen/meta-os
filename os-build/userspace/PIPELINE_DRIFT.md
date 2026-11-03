# Two userspace pipelines — measured agreement and one real gap

Written 2026-11-02 after `origin/main` cherry-picked the loader fix as
`os-build/userspace/build_userspace.py` + `LOADER_FIX.md`, alongside the
`build.sh` + `bases.txt` pipeline that produced the K6 boot proof.

## The two scripts

| | `build.sh` | `build_userspace.py` |
|---|---|---|
| bins | every bin in `bases.txt` (36) | `PROGRAMS` table (the four in `BINS`) |
| base source | `bases.txt` | hardcoded table |
| linker | committed `link.ld` with `DEFINED(__base)`, passed as `--defsym=__base=` | generated `link-<bin>.ld` from `link-base.ld` |
| verifies | `verify_bases.py`: real ELF headers, all images disjoint | first LOAD == base, entry inside image, pairwise ranges |
| toolchain | pins `RUSTC` to a toolchain that has `core` | plain `cargo` from PATH |

Both write into the same `os-build/userspace/user/target/x86_64-unknown-none/`
directory, which `kernel/build.rs` stages from. Whichever ran last supplies the
ELF for a given bin.

## What the gate measured

`os-build/userspace/compare_builders.py`:

```
program                build.sh   build_userspace.py  agree
hello        0x0000600000000000   0x0000600000000000  yes
sleeper      0x0000610000000000   0x0000610000000000  yes
crasher      0x0000620000000000   0x0000620000000000  yes
readkey      0x0000630000000000   0x0000630000000000  yes

coverage: build.sh 36 slots; build_userspace.py 4 programs
```

So the shared bases agree, both templates carry the substitution their script
expects, and no slot is duplicated. That is the drift class this gate closes: a
change to one table without the other now fails before a build.

## The gap the gate found

`build_userspace.py` is **not buildable on this machine**:

```
$ python3 os-build/userspace/build_userspace.py hello
...
error: could not compile `user` (lib)
cargo rustc failed for hello (exit 101)

$ rustc --version
rustc 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew)
```

Homebrew's rustc has no `core` for `x86_64-unknown-none`, so the crate fails
with E0463. `build.sh` exists partly because of this exact trap: it probes the
toolchain, pins `RUSTC` and `PATH`, and falls back to the rustup toolchain that
does carry `core` (see `BASES.md`). `LOADER_FIX.md` already says the script was
"UNCOMPILED on this VM (no cargo)"; running it here shows the stronger fact —
it is uncompiled even where a cargo exists, because it is the wrong one.

The gate reports this as a **NOTE**, not a failure, because it does not use the
script and a boot gate should not go red over an unused path. Pass
`--require-python-buildable` on a machine where that pipeline is expected to
work, and it becomes a hard failure.

## What this does not claim

- I did not modify `build_userspace.py`. It is Rowan's file and the toolchain
  pin is their decision, not mine.
- Static agreement is not byte equality. Both scripts write to one target
  directory, so a byte diff would require running them into separate
  `CARGO_TARGET_DIR`s; each already verifies its own ELF headers instead.
- The K6 boot proof came from `build.sh` (log: `os-build/logs/K6-feature-gate.txt`),
  not from the Python pipeline.

## Recommendation for Pax

Pick one authoritative pipeline before K2 lands, or make the Python one pin
`RUSTC` the way `build.sh` does. Two scripts that can each silently overwrite
the other's ELF are a merge hazard even when their tables agree today.
