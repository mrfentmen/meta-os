# NixOS — the declarative model

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-105).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

A Linux distribution where the entire machine is described by a declarative
configuration file (`/etc/nixos/configuration.nix`), built by the Nix package
manager into immutable store paths, and activated as a whole. You do not edit
system files; you declare the state you want and the system is rebuilt to
match it.

## The model, mechanically

- Every package lives at `/nix/store/<hash>-<name>`, content addressed. Two
  versions coexist without conflict because the path itself carries identity.
- Changing `configuration.nix` and running `nixos-rebuild switch` builds a new
  *generation*, a boot menu entry. Rolling back is picking the previous
  generation at boot, and it is instant because nothing was overwritten.
- Because builds are pure (no network during the build, declared inputs only),
  the same declaration reproduces the same output elsewhere.

## What it does better

1. **Rollback as a first class operation.** A bad update is a boot menu choice,
   not a rescue USB. Nothing in Debian-land is close to this.
2. **The configuration is the documentation.** The machine's state is a text
   file in a repo, diffable and reviewable, which is exactly how an agent wants
   to hold a system.
3. **No configuration drift.** Nothing mutates outside the store, so "it works
   on my machine" is not a category of bug.
4. **Upgrades are atomic at the system level**, not per package.

## What it costs

1. **The learning curve is the product.** Nix the language is a lazy functional
   language, and knowing Linux does not help you read a derivation.
2. **Discipline everywhere.** Anything that writes outside the store breaks the
   model, and a lot of real software wants to.
3. **Debugging is harder.** When a build fails you are debugging a sandboxed
   pure build, and error messages arrive far from the cause.
4. **Disk usage** grows with generations unless you garbage collect.
5. **It is a whole second operating system to learn** while we are building a
   kernel. That is the real cost for this project.

## One borrowable idea

**The declaration is the system, and the previous state is always bootable.**

For an agent first OS this is not a packaging nicety, it is the safety story.
An agent that can rewrite its own machine needs a machine state it can name,
diff and return to. "Agent changed its home and services" should produce a new
addressable generation with the old one still bootable, and that maps directly
onto OS-124's deterministic records and OS-127's sandboxing between agents.

Concretely for us, at the service layer, not the kernel: the Goose supervisor
(OS-157) should describe services as declared state rather than as started
processes, and every activation writes a record that names the previous
generation. We do not need a content addressed store to get the rollback
property; we need the supervisor to never mutate in place.

## License position

- **The idea (declarative system state, generations, rollback):** free to take.
  It is a design pattern, not code.
- **Nix itself: LGPL-2.1-or-later.** Library level copyleft. We would not link
  it, and we will not read it as a source for our own implementation.
- **nixpkgs: MIT.** Permissive, which is why the *packaging data* model is
  safely borrowable.
- **Verdict: idea only. Do not adopt NixOS as a carrier or build system.** The
  carrier is Debian by the boss's order (KERNEL_SPEC rule 1), and adding Nix to
  a kernel build is a second system to debug while the first one does not boot.

## Verdict for Meta OS

Take the generation and rollback idea into the services layer design. Do not
take the toolchain. There is a version of this that matters more than the
distro: **the boot proof culture**. NixOS generations are addressable, and our
K milestones should be too, with each proven state recoverable.
