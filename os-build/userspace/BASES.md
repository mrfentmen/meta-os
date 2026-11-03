# Userspace link bases — one address per program (fixed 2026-11-02)

## The bug that was killing three of four programs

`kernel/src/user.rs` maps every program at the address it was linked for and
refuses a page already mapped: `return Err("address in use")`. That is correct
behaviour. The bug was in the userspace build:

- `user/link.ld` hardcoded `. = 0x620000000000` (crasher's base).
- `user/.cargo/config.toml` carried `relocation-model=static`, `code-model=large`,
  `-no-pie` — and **no `-Tlink.ld` at all**. So no program used the script.
- A plain `cargo build --bins` therefore linked every program at the same
  default base, and the loader refused the second, third and fourth with
  `address in use` — exactly what `os-build/logs/RK-007-serial.txt` shows.

The old workaround was `sed`-ing a base into a scratch `link-base.ld` inside
`boot-test.sh`. That is not a build pipeline: nothing else used it, and a
plain cargo build still produced four colliding images.

## The fix (build pipeline, per Pax's ruling)

| file | role |
|---|---|
| `user/link.ld` | `. = DEFINED(__base) ? __base : 0x0000620000000000` — base comes from the caller, with crasher's historic value only as a fallback |
| `bases.txt` | one explicit slot per program, 0x0100_0000_0000 apart; the four historic bases (0x6000/0x6100/0x6200/0x6300) are unchanged so old logs still match |
| `build.sh` | one cargo invocation per program with `-C link-arg=-T…link.ld -C link-arg=--defsym=__base=0x…`; picks a toolchain that actually has `core` for `x86_64-unknown-none` |
| `verify_bases.py` | reads the real ELF headers (entry + PT_LOAD ranges) and fails on overlap, wrong base, or an entry outside its own image |

The toolchain detail matters on this Mac: Homebrew's `rustc` shadows rustup and
has no `core` for the bare-metal target, and `rustup run stable cargo` alone
still resolves `rustc` from PATH. `build.sh` pins both `cargo` and `RUSTC` to
the rustup toolchain and says which one it chose.

## Measured proof

```
$ PROFILE=debug os-build/userspace/build.sh hello sleeper crasher readkey
bin                       entry                                image segs
hello            0x600000000000 0x600000000000-0x600000001000    2
sleeper          0x610000000a40 0x610000000000-0x610000002000    3
crasher          0x6200000000e0 0x620000000000-0x620000001000    4
readkey          0x630000000a40 0x630000000000-0x630000002000    3
4 program(s): disjoint, at their manifest bases, entries inside images
```

Kernel built from the same tree and booted (QEMU 11.1.3, 25 s serial capture),
log committed as `os-build/logs/K6-bases-fixed.txt`:

- `user hello: entry 0x600000000000` → `HELLO FROM USERSPACE` → `user exit code 0`
- `user sleeper: entry 0x610000000a40` → `sleeper: sleeping 5 ticks` → `sleeper: woke, sleep returned 0`
- `user crasher: entry 0x6200000000e0` → `crasher: about to read zero` → page fault, `task killed` (only that task)
- `user readkey: entry 0x630000000a40` → loaded; no refusal
- **`loader refused` count: 0** (it was 4 of 4 before)

`K3 timer` and `mem summary: K4 up` are in the same log, so the boot is not a
narrow one-off.

## What this unlocks and what is still missing

Unlocked: adding a program is now a line in `bases.txt` plus its source. No sed,
no per-run hacks.

Still missing, stated so nobody assumes this fixed more than it did:

- **Wiring**: `kernel/build.rs`'s `BINS` list is Rowan's file. `quitter`
  (`0x6400…`), `badcall`, `writer` and `hog` are built and have bases reserved,
  but the kernel embeds only hello/sleeper/crasher/readkey until that list grows.
- **Program count cap**: `user.rs` has four user stack slots (`take_ustack`
  refuses a fifth). More programs need kernel work, not a base.
- **No new syscalls**: 6-15 remain reserved by the F1 ruling. Every program here
  still runs on exit/write/sleep/pid/yield/read_key only.
