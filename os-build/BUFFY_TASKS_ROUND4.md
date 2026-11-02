# Buffy tasks — Round 4 (the 72-hour window)

From Pax, 2026-11-01 ~20:35 EST. Boss order, his words: "Give
Buffy a ton of tasks, they finished." Your Layer 4 lane and the
B-1 to B-6 closeout from os-build/PAX_12H.md are done or closing;
this is the next full load. Same branch:
`buffy/layer1-goose-services`. Milo gates checkpoints, Pax
merges in slices during the window — signal each checkpoint on
room 1, do not wait for the whole list to finish.

Status words stay yours and stay honest: DESIGNED / WRITTEN /
TYPECHECKS / RUNS (a named output) / DEAD. Every claim names its
evidence. Reports state wired/dead counts.

## Wave 1 — from typechecks to runs (BF4-01 to BF4-06)

- BF4-01: Run every service natively, one by one. A pass/fail
  table with the actual output (or the actual error) per service,
  committed as `os-build/layer1/SERVICE_RUNS.md`.
- BF4-02: Fix what the runs expose, in dependency order
  (`common.*` first). Each fix names the run that failed before
  and passes after.
- BF4-03: The supervisor story, proven natively: start, stop,
  restart-on-crash of two services under the supervisor, output
  committed.
- BF4-04: Log service end to end natively: write, rotate, read
  back, quota enforced — one transcript.
- BF4-05: Storage contract against the RAM backend: write/read/
  delete/list with the quota and retention rules firing, one
  transcript.
- BF4-06: The shell service natively: the builtins exercised
  against the real filesystem service, transcript committed.

## Wave 2 — bind the corpus to the frozen ABI (BF4-07 to BF4-12)

- BF4-07: `os-build/layer1/SERVICES_SYSCALL_MAP.md`: every
  service's syscall needs mapped against the F1 freeze (0 exit,
  1 write, 2 sleep, 3 pid, 4 yield, 5 read_key, 6-15 reserved).
  Three classes: runs on the proven ABI / needs a proposal /
  host-only forever.
- BF4-08: For the "needs a proposal" class: exact proposed
  numbers and signatures, as proposals only. The freeze holds;
  nothing is allocated tonight.
- BF4-09: F2 consistency: the services' status output shaped to
  the same `KEY value` fields the kernel shell prints. One
  status shape across the whole OS.
- BF4-10: The Lobster host binding: services callable from the
  Lobster agent host, one real round trip (agent calls a service,
  service answers), log committed.
- BF4-11: A machine-readable services manifest (name, entry,
  syscall class from BF4-07, status word) generated from the
  corpus, not hand-typed — plus the generator.
- BF4-12: `os-build/layer1/BOOT_PLAN.md`: the ordered plan for
  loading services into the kernel when a syscall surface is
  ruled (2026-11-02 decision). Pre-think tomorrow so nobody
  designs it under deadline.

## Wave 3 — hardening (BF4-13 to BF4-18)

- BF4-13: Malformed-input suite for the format/config/hash
  libraries: counts run, counts passed, failures named.
- BF4-14: Parser hardening round 2 on the shell's argument
  parser: quoting, escapes, empty input, overlong lines —
  behaviour specified first, then code.
- BF4-15: The network protocol pack exercised pairwise natively
  (ARP/ICMP/UDP/TCP state machines talking to each other, not to
  a wire): transcripts for each pair that runs.
- BF4-16: MOSFS01 filesystem edge cases: full disk, deep paths,
  name collisions, delete-while-open — behaviour specified,
  then proven.
- BF4-17: Quota and retention abuse cases across services:
  every limit in the corpus gets one test that tries to break it.
- BF4-18: A second full-corpus audit pass in the style of your
  round-2 gates: every status word in every doc you own
  re-measured against a command.

## Wave 4 — feed the demo and the record (BF4-19 to BF4-24)

- BF4-19: The measured fact sheet for the demo:
  `os-build/layer1/DEMO_FACTS.md` — boot time, wired/dead lines,
  service counts by status word, run counts. Every number
  sourced to a command or a log. Hana's demo script reads this.
- BF4-20: SERVICES_SCOPE.md refresh after Waves 1-2 (it moves:
  what runs natively now vs what waits on the kernel surface).
- BF4-21: BUFFY_REPORT.md and SIGNOFF.md final correction pass
  for the window: measured words only, dated.
- BF4-22: The tools you built, indexed: drive.py and any gate
  helpers, one `os-build/tools/README.md` saying what each does
  and the command that proves it works.
- BF4-23: Research note, one page: what a real Flock-style
  deployment of the services layer would need that this build
  does not have. Facts only, no pitch.
- BF4-24: Your 2026-11-02 list: the wire-or-delete input on the
  service side — which services you would load first and why,
  in load order.

## Rules

One writer per file; the corpus files are yours. Nothing lands
on main except through Milo's gate and Pax's merge. Hard freeze
at H+9 of the 12-hour clock (05:12 EST) applies to feature work;
audits, corrections, and reports continue past it.
