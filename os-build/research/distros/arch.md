# Arch — the simple base, assembled by hand

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-106).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

A distribution that installs almost nothing and expects you to assemble the
rest, on a rolling release. No installer that makes decisions for you, no
downstream patches, packages close to upstream.

## The model, mechanically

- You install a base, then choose every piece: bootloader, network stack,
  desktop, audio.
- Rolling release: one package version per package, always current, no major
  version jumps to plan around.
- The AUR is user submitted build recipes, not a supported repository. Useful,
  unaudited, and the classic way people compromise an Arch box.
- The wiki is the actual product. It is the best written Linux documentation
  that exists, and it documents *mechanisms*, so it is useful even to people
  who do not run Arch.

## What it does better

1. **Nothing hidden.** If it runs, you put it there. There is no vendor default
   to discover at the worst moment.
2. **Current packages.** A kernel, a compiler or a language toolchain released
   last week is available last week, which matters when a project's toolchain
   is younger than the distro (see `../ecosystem-watch.md`: both our upper
   layers are new).
3. **The documentation habit.** Every operation has a written page explaining
   the mechanism, not just the command.
4. **Small base means a small attack surface** and a small image to reason
   about.

## What it costs

1. **You maintain it.** Rolling release means rolling breakage, and the fix is
   your evening.
2. **No defaults means no safety net.** A missing step is a machine that does
   not boot and no error message that says why.
3. **The AUR is a trust hole** and a supply chain risk, by design.
4. **It is the wrong carrier for us.** The carrier needs to be boring and
   reproducible across crew VMs (Debian 12 is pinned by KERNEL_SPEC rule 1),
   and rolling means two lanes can be on different compilers without knowing.

## One borrowable idea

**Do not hide the mechanism.** An OS built for agents has to be legible: every
capability an agent has should be traceable to a file, a service or a rule you
can read and change, with no vendor magic in between.

That has teeth for us in two places. The tool registry (OS-121) should list
what a tool *is* and where it lives, not a capability string an agent has to
trust. And when our kernel fails at boot, the honest failure mode is a serial
line that says what failed, which is the Arch principle applied to a kernel:
no silent recovery, no guessing.

## License position

- **The idea (legibility, no hidden defaults):** free to take.
- **pacman: GPL-2.0.** Do not copy from it. Read the wiki for mechanism, which
  is prose, and write our own.
- **The Arch wiki: GNU FDL 1.3.** Copying page text into our docs carries the
  FDL's requirements, so cite and link it, never paste it.
- **Verdict: idea only, and the wiki as a reference we link.**

## Verdict for Meta OS

Borrow the legibility principle, and use the wiki as a mechanism reference
while building the kernel. Do not run Arch as a carrier, and specifically do
not let a lane "just quickly" install a newer compiler from the AUR onto a crew
VM: that is how two lanes stop agreeing about what compiles.
