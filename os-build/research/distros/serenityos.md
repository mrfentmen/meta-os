# SerenityOS — a from scratch system built by a community, and what steady milestones look like

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-111).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

A from-scratch operating system started in 2018 by Andreas Kling, with its own
kernel, its own userland, its own browser engine, its own JavaScript engine and
its own image decoders. No Linux, no BSD, no borrowed userland. Built in the
open, one commit at a time, by a large volunteer community.

The detail that matters most to us: the project's browser engine (LibJS and
LibWeb) grew out of the OS and eventually became its own project, Ladybird,
because the browser needed to stand on its own. That is a real lesson about
composition, not a footnote.

## The model, mechanically

- **Nothing is a wrapper.** Every layer is written by the project, so there is
  no place where "the OS" ends and "somebody else's code" starts.
- **Small, frequent, reviewable commits**, with a culture of explaining the
  change in the commit message.
- **Public progress reporting.** The author's development videos and the
  project blog made each milestone visible and checkable, which recruited
  contributors far more effectively than a roadmap would have.
- **Style and aesthetics are part of the product**, deliberately 1990s, which
  gives the project a coherent identity and a reason for contributors to care.

## What it does better

1. **Milestone discipline at a scale that should not work.** A working browser
   engine from scratch, in a community project, by doing the next small thing.
2. **The codebase is legible.** Because nothing is a wrapper, a newcomer can
   read from the kernel to the app without hitting a foreign codebase wall.
3. **Progress is demonstrated, not claimed.** Screenshots, videos, posts.
4. **A strong identity attracts contributors**, which is the actual growth
   mechanism of an OS project.

## What it costs

1. **Enormous total effort**, sustained over years, by hundreds of people.
2. **Reinventing everything** means re-finding every bug the incumbents already
   fixed.
3. **Aesthetics-first choices** cost portability and compatibility.
4. **The community's pace is not a schedule.** Nobody can commit to Serenity's
   velocity, including Serenity.

## One borrowable idea

**Prove each step in public, and let the proof be the marketing.**

Our repo already has the mechanism: the boot log rule (KERNEL_SPEC rule 3) says
a milestone is not real until a QEMU log from our own binary shows it. Serenity
is the evidence that this is not just rigor, it is the growth engine. A project
that shows "K2: the kernel draws its own text, here is the log and the screen"
every few weeks attracts the people who can help with K3.

The composition lesson is the second one, and it is aimed at us: Ladybird left
the OS because a browser has its own users. Our programs (Imperium, Custos,
Officina, Scientia, Musica) are in exactly that position. KERNEL_SPEC already
draws the line ("programs are not the OS"). Serenity shows the healthy version
of that split: the OS gives the program a home, and the program is allowed to
have users who never think about the OS.

## License position

- **BSD-2-Clause** (verified 2026-11-01, `LICENSE` in the repo). Permissive, so
  the source is legally readable and borrowable.
- **Do not borrow it anyway.** KERNEL_SPEC rule 1: the kernel is ours, from
  zero. Serenity's value to us is the process, not the code.
- **Some bundled third party components are LGPL or GPL** (fonts, tools,
  libraries), so "Serenity is BSD" is not true of every directory. Assume
  nothing from a directory listing.
- **Verdict: process and idea only.**

## Verdict for Meta OS

Take the public proof habit. Every K milestone should land with its log and a
short human readable line about what it proves, in a file the boss can read
without reading code. Take the split lesson as confirmation of the layer
boundary we already have, not as a reason to change it.
