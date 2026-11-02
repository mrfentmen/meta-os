# Buffy tasks — Round 5 (the 72-hour window)

From Pax, 2026-11-01 ~21:35 EST. Boss order: this list queues
behind BUFFY_TASKS_ROUND4.md automatically — when Round 4
closes, start here without waiting for a new assignment. Same
branch: `buffy/layer1-goose-services`. Milo gates checkpoints,
Pax merges in slices. Status words stay measured; every claim
names its evidence.

## Wave 1 — rehearse the boot (BF5-01 to BF5-05)

- BF5-01: Execute your own BOOT_PLAN (BF4-12) inside the Lobster
  host: services started in boot order against the host runtime.
  One transcript, failures named per service.
- BF5-02: The failure matrix: for each service, its failure
  modes listed and each one exercised natively (bad config,
  missing dependency, quota hit, corrupt input). Table with
  outcomes.
- BF5-03: Re-run the full corpus gates after Rowan's read_key
  landed: any service whose ABI class changed in
  SERVICES_SYSCALL_MAP gets re-mapped and re-checked.
- BF5-04: Supervisor under load natively: 10 services, mixed
  crashes, restart policy firing, quotas enforced. One
  transcript with the counts.
- BF5-05: The shell service driving the real demo commands end
  to end natively (the same words the kernel shell speaks):
  transcript aligned line by line with the kernel's K7 log.

## Wave 2 — the load package for 2026-11-02 (BF5-06 to BF5-10)

- BF5-06: For the first 3 services in your BF4-24 load order:
  an integration pack each — entry point, exact ABI needs
  against the frozen table, host shim used today, and the
  smallest kernel-side change that would load it. Ready for
  the boss's wire-or-delete ruling, whichever way it goes.
- BF5-07: A services freeze audit: at the H+9 freeze, the
  corpus state in one page — counts by status word, what is
  RUNS, what is TYPECHECKS, what is honestly neither.
- BF5-08: SERVICES_FINAL.md: the state of the layer for the
  submission record. Measured words, dated, no claim without
  a transcript or a command behind it.
- BF5-09: Cross-check DEMO_FACTS against Milo's claim audit
  when it lands: any number the two documents state
  differently gets reconciled in writing, yours or his.
- BF5-10: One page: what the services layer needs from the
  kernel in the week AFTER the hackathon, in dependency
  order. Planning only; no new code implied by the list.

## Wave 3 — demo and record support (BF5-11 to BF5-14)

- BF5-11: The services segment of the demo: a 30-second
  timed script (what is on screen, what is said) for Hana's
  DEMO_SCRIPT, using only services that RUN natively.
- BF5-12: Screenshot-grade transcripts: the three best native
  service runs re-captured clean, one file each, named for
  the demo and the README.
- BF5-13: README section for the services layer, submission
  grade: what it is, what runs, what does not, where the
  transcripts live. Draft on branch; Pax places it.
- BF5-14: Your closing report for the window: lanes, counts,
  what slipped and why, in the same honesty format as the
  12-hour letter. Address it the same way.

## Rules

One writer per file; the corpus is yours. Nothing reaches
main except through Milo's gate and Pax's merge. The H+9
freeze (05:12 EST) stops feature work; audits, transcripts,
and reports continue.
