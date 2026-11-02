# Buffy — FINISH TONIGHT (the complete list)

From Pax, 2026-11-01 ~23:45 EST. Boss order: finish tonight.
There has been confusion about task lists, so this one is the
whole job in one place. It SUPERSEDES the remainder of
BUFFY_TASKS_ROUND4.md and BUFFY_TASKS_ROUND5.md: everything
still owed from both is folded in here. Nothing outside this
list is owed tonight, and NO new services get built tonight —
tonight is finish, prove, and document what exists.

**The finish line: the H+9 freeze, 2026-11-02 05:12 EST.**
After it: gate fixes and the report only.

Same branch: `buffy/layer1-goose-services`. Milo gates
checkpoints, Pax merges in slices. Status words stay
measured; every claim names its transcript or command.

## A — Land what is already built (do this first)

Your branch already carries Round 4 and Round 5 work (the
corpus running, defects fixed, demo facts measured, the
BF5-01 deviation note at the tip). Before anything new:

- A1. Checkpoint commit + a written state post, item by item
  against BF4 and BF5 ids: DONE (with its evidence named),
  PARTIAL (what is missing), NOT STARTED. This post settles
  the "never got it / already did it" question in writing.
- A2. The BF5-01 deviation, closed properly: the rehearsal
  ran in the host runtime, not a Lobster host. Either run it
  in the Lobster host for real and commit that transcript,
  or the final report states the deviation plainly and why.
  No silent rewording of what ran where.
- A3. Whole-corpus final numbers, measured once, tonight:
  `goose check` over the full corpus with
  `services/root.goose` in place — pass count and error
  count; then one table of every service with its measured
  status word (RUNS / TYPECHECKS / honestly neither).

## B — Finish the layer

- B1. The failure matrix, complete: for each service, its
  failure modes listed and each one exercised natively (bad
  config, missing dependency, quota hit, corrupt input),
  with outcomes. One table.
- B2. Supervisor under load: 10 services, mixed crashes,
  restart policy firing, quotas enforced — one transcript
  with the counts. (If already committed on the branch,
  A1 names it and this item is done.)
- B3. The shell service driving the real demo commands end
  to end natively, transcript aligned line by line with the
  kernel's K7 session log (OpenCode's refreshed log lands
  tonight; align against the newest one on main).
- B4. The syscall/ABI map regenerated after read_key
  (syscall 5) landed: any service whose ABI class changed
  gets re-mapped and re-checked. State the final counts.
- B5. Integration packs for the first 3 services in your
  load order: entry point, exact ABI needs against the
  frozen table, host shim used today, and the smallest
  kernel-side change that would load each one. Ready for
  the boss's syscalls wire-or-delete ruling either way.

## C — The record (what the submission stands on)

- C1. SERVICES_FINAL.md: the state of the layer for the
  submission record. Measured words, dated tonight, no
  claim without a transcript or a command behind it.
- C2. The freeze audit at H+9: the corpus state in one page
  — counts by status word, what is RUNS, what is
  TYPECHECKS, what is honestly neither.
- C3. DEMO_FACTS, final: every number the demo will say
  about the services layer, measured tonight, each with the
  command or transcript it came from.
- C4. One page: what the services layer needs from the
  kernel in the week AFTER the hackathon, in dependency
  order. Planning only; no new code implied.

## Reporting

Post each group as it closes (A-state post first, before
new work). Milo gate-1 on each checkpoint; Pax merges
slices as they gate green. If you finish early, post DONE
and stand by — do not invent new scope.
