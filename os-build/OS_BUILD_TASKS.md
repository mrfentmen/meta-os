# OS BUILD — crew lanes (boss's order 2026-11-01)

The pivot: Meta OS is a real operating system now, ours, layered.
Rust kernel, Goose services, Lobster agent layer. KERNEL_SPEC.md is
the law. The OpenCode giant list is OPENCODE_OS_BUILD.md (240 tasks,
Mac side). These are the SANDBOX crew lanes. The boss wants this
churning while he sleeps: post at every stage boundary on room 1.

## Standing rules for every lane

- Wire MCPs and docs tooling for your language before deep work:
  Rust via the rustdocs MCP pattern, Goose and Lobster via their
  docs and whatever MCP exists. Smoke call or it is not wired.
  Write what you wired into your lane's notes file.
- Everything you write for the kernel or layers is UNCOMPILED until
  the Mac build says otherwise. Say so on every report.
- Branches: in repo, named per lane below. Gate 1 rotation stands:
  Milo gates Rowan and Hana, Pax gates Milo, and Pax gates all
  kernel merges personally until K2 lands.
- The cybersecurity program is PARKED. Nobody starts it.

## Rowan — kernel code lane (branch rowan/kernel)

- R1: Read kernel/src/main.rs (K1 skeleton). Port nothing; review
  it like an enemy: every assumption listed in kernel/REVIEW.md.
- R2: Write the K2 framebuffer module as a separate file in
  kernel/src/, against the bootloader version in the lockfile,
  not wired into main.rs yet.
- R3: Write the K3 interrupt module (IDT, handlers with their
  real print behavior — no stubs), separate file, not wired in.
- R4: Keep a running list of Mac build questions for OpenCode in
  kernel/MAC_QUESTIONS.md (exact API points, not vibes).
- R5: When OpenCode's os-build branch shows a K1 boot log, rebase
  your modules onto the proven tree and wire ONE in per commit.

## Milo — verification and gate lane (branch milo/os-gate)

- M1: Own the milestone gate: for each K milestone, the exact boot
  log lines that prove it, written in os-build/gates.md (mirror of
  what OpenCode's expected/ files should contain).
- M2: License watch: read OPENCODE_OS_BUILD.md Section P; build
  the checklist the gate will actually run on every OS merge.
- M3: Audit the Debian research coming from OpenCode's Section G
  against second sources as it lands; flag single source claims.
- M4: Gate 1 duty for Rowan's kernel branch and Hana's shell
  branch, same standard as Custos: suites plus the boot log rule.
- M5: Keep the honest scoreboard in os-build/gates.md: per
  milestone, PROVEN (log file named), WRITTEN (uncompiled), or
  NOT STARTED. Update it at every gate.

## Hana — shell and experience lane (branch hana/os-shell)

- H1: Design the boot experience for BOTH citizens: the user's
  console (Section O of the OpenCode file is the reference) and
  the agent's structured view. Spec in os-build/shell-spec.md.
- H2: The banner and status formats as data: exact strings and
  fields, so kernel and services emit the same facts.
- H3: The OS home surface gets built ONLY when it reads real OS
  state. No mock, no clickable fake, no placeholder screen: until
  real state exists to show, the surface does not exist. When it
  is built, every value on it traces to a real source.
- H4: The first minute walkthroughs (user and agent) drafted from
  the spec, every unbuilt step marked NOT BUILT.
- H5: Musica and the other programs stay warm, not hot: no new
  program features until the OS passes K2, per the boss's
  sequencing (OS first, programs after).

## Buffy — research and tools lane (starts when the boss starts her)

- B1: The tools manifest research: for every category in Section J
  of the OpenCode file, the 5 best candidate tools with licenses.
- B2: Other distros notes (Section H mirror): one system per file,
  borrowable idea and license position.
- B3: Goose and Lobster ecosystem watch: new docs, MCPs, or
  toolchains found, filed with links and dates.

## Pax — coordination

- Spec keeper (KERNEL_SPEC.md), merges, the bus, the boss's
  report. Kernel merges gated personally until K2 is proven.
- After the OS: the programs resume (Imperium, Scientia, Musica,
  Officina, Custos), then the parked cybersecurity program when
  the boss says. Not before.

## LAYER ASSIGNMENTS — boss order 2026-11-01 ~08:18 (parallel by layer)

The boss's word: every worker takes a layer so all layers move at once.
Nobody stops working. Nobody starts building out the Debian yet — it
stays the dev carrier. MCP servers for Goose and Lobster are being
built by the boss himself and will be sent to the crew, with more MCP
servers to connect after that. Until they land, work from the
languages' public source and docs (aardappel on GitHub, Apache-2.0).

- **Layers 1–3 — boot, Rust kernel core, drivers (`kernel/`): Rowan
  + OpenCode.** (Renumbered to the 7-layer model 2026-11-01 ~09:02 on
  the boss's word; `os-build/LAYERS.md` is the index.)
  Rowan writes kernel code: the R2/R3 modules (K2 framebuffer console,
  K3 interrupts/timer/keyboard) unwired with real behavior, and keeps
  the enemy review going. OpenCode on the boss's Mac is the compile
  and proof lane: it resolves Cargo.lock, builds K1, and produces the
  QEMU serial boot log — the only proof that counts. Kernel merges
  still come through Pax.
- **Layer 4 — Goose system services: Pax + Buffy.**
  Pax designs and writes the first Goose services (the K6 service
  shape: what a service process is, how it starts, how it talks to
  the kernel) from the Goose language source. Buffy turns her tools
  manifest and ecosystem watch into the Layer 4 worklist: which
  services exist first, in what order, built from what.
- **Layers 5–6 — Lobster agent runtime + shell/apps: Milo + Hana.**
  Hana builds the app and shell side (Layer 6): the OS home surface
  reads real state only (no mocks, per spec rule 6), the shell spec
  H1/H2 lands here. Milo builds the agent side (Layer 5): how a
  Lobster agent process is defined, started, and supervised — and
  keeps gate-1 plus the honest scoreboard across all seven layers.

Cross-layer rules unchanged: OS first, programs after; NO MOCKS;
testing spend is allocated by priority, never split evenly across
everything (boss, 2026-11-01); the cybersecurity program stays parked
until the OS is done and the boss says so.
