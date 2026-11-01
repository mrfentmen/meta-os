# Alpine — the small musl base, and why it boots fast

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-107).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

A distribution built on musl libc and BusyBox, designed for small images and
fast startup. The base image is a few megabytes, boot to a shell is seconds,
and it is the default base for a great many containers.

## The model, mechanically

- **musl instead of glibc.** A small, clean, MIT licensed C library. Static
  linking is normal and cheap, so a binary carries its own libc.
- **BusyBox** provides hundreds of commands as one binary with many names,
  which is most of why the base is tiny.
- **OpenRC** instead of systemd: dependency ordered init scripts, shell based,
  no daemon binary managing everything.
- Everything is compiled against musl, so anything prebuilt for glibc does not
  run without a compatibility layer.

## What it does better

1. **Boot time.** Less to load, fewer daemons, less to wait for.
2. **Image size.** A complete base is smaller than one of our test fixtures.
3. **Simplicity of the init model.** OpenRC's shell scripts are readable in a
   way that systemd units are not.
4. **Static linking is normal**, so a single file can be a working program.

## What it costs

1. **Prebuilt glibc binaries do not run.** This is the whole cost, and it is
   not theoretical for us. See the finding below.
2. **musl is not glibc.** Different `malloc`, different locale handling, and
   some software needs patching. C++ code with `std::filesystem` and locale
   use is where it usually bites.
3. **Smaller package set**, and fewer people have hit your bug.
4. **BusyBox applets are not the full tools.** `grep` without the flags you
   expected is a bad afternoon.

## A finding that matters more than the distro

**Alpine cannot be our carrier for the Goose layer.** The Goose prebuilt Linux
compiler requires **glibc 2.35 or later** (its own release notes, checked
2026-11-01, see `../ecosystem-watch.md`). Alpine has no glibc at all, so the
prebuilt binary does not start, and building the compiler from source against
musl is a C++ toolchain port, not an install step.

Debian 12 ships glibc 2.36 and satisfies it. So the boss's choice of Debian as
carrier (KERNEL_SPEC rule 1) is also the choice that keeps Layer 1 installable.
That is worth writing down before somebody proposes a slim Alpine image for the
crew VMs to save disk.

## One borrowable idea

**Small, static and single file is a feature, not a compromise.**

Our K6 target is "the Goose services layer gets its first process". The
temptation is a services layer that arrives with a runtime, a package tree and
a dynamic linker path problem. Alpine's lesson is that a self contained binary
with its own libraries is easier to prove and easier to boot than a
conventionally packaged tree, and our service supervisor (OS-157) should be
built as one static-ish binary with an explicit, short dependency list, so that
"the first process" is one thing to debug.

## License position

- **The idea (small static binaries, simple init):** free to take.
- **musl: MIT.** Permissive, and genuinely interesting to us: a permissive C
  library is a licensing argument for musl-adjacent choices in userland later.
- **BusyBox: GPL-2.0.** Do not copy an applet's source. Its behavior is fine to
  match, its code is not.
- **apk-tools: GPL-2.0.** Same.
- **Verdict: idea only. Never a carrier here.**

## Verdict for Meta OS

Do not use Alpine anywhere near this build: it cannot run Goose's prebuilt
compiler, and porting the compiler to musl is a project, not a prerequisite.
Take the single-static-binary lesson into the services layer.
