# BUFFY 2 — THE LIGHT LANES (8GB machine; Pax, 2026-11-02)

The boss's question: Buffy 2 is on an 8GB laptop — how does
she pull real volume? Answer: the volume lives in text, tests,
and programs; the RAM-hungry work (full Rust workspace
builds, emulator runs against the 6 GiB image, model work)
stays off her machine. Her lanes:

## Yours

1. The Node and Python suites, extended: new test files for
   the surfaces, the queue, the agent layer — these run in
   hundreds of MB, not GB. A failing test found is a finding
   filed on room 1 with the repro.
2. The face apps' logic: the everyday apps (Notes, Calendar,
   Files, Calculator, Settings) as dependency-free HTML/JS —
   no build step, no toolchain weight — against Hana's
   surfaces contracts.
3. Kernel and OS records: the behaviour documentation read
   from the code (Buffy 1's section 4 pattern), the ABI
   spec's worked examples, the boot-log index kept current.
   Reading code costs no RAM and the records are real lines.
4. Parity reading: the Rust-port parity tests are text tests
   (they read sources and compare) — she runs those and the
   Goose typecheck, which is a compiler for a small language,
   not a workspace build.
5. The clean-clone gate, minus the cargo stages: the gate's
   clone, tree comparisons, doc checks, and suite runs.

## Not yours (they will swap an 8GB machine to a standstill)

- cargo build/check over the crates workspace (Buffy 1 and
  the Mac carry compiles).
- QEMU/UTM against the full face image.
- Anything holding a model.

## Machine rules

One heavy thing at a time; if a command must compile, it runs
alone with jobs limited (cargo -j1); browser closed while a
suite runs. If a lane here starts swapping, say so on room 1
— the lane moves, nobody grinds a machine to death quietly.
