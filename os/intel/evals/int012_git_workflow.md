# INT-012: git workflow reconciliation (2026-10-27, PAX)

## Task

INT-012: reconcile the git workflow conflict. The plan said the repo
README wants feature branches plus overseer merge while the crew rule
elsewhere is push straight to main, and GOV-003 was to decide. The task
is to follow Dale's recorded decision exactly and note it in every lane
file.

## The ruling (verbatim from plan/MASTER_PLAN.md, GOV-003)

Ruled by Del 2026-10-24, superseding the either/or: make a NEW repo and
merge muse-relay into the new repo; work from the new repo, with the
relay as the base and Meta OS built on top of it there.

## Repo facts checked before editing

- Remote origin is https://github.com/Mrfentmen/meta-os.git, branch main.
- Local HEAD at edit time was bfa1a70 (PAX DSP-010), the remote tip,
  verified through the GitHub connector list_commits call.
- The repo README states it merges muse-relay as the base layer, which
  matches the ruling.
- Every batch in this repo's history landed as a commit on main. That
  main-landing practice is stated in the lane notes as crew practice,
  not as part of the GOV-003 ruling text, so the two are not conflated.

## What changed

- plan/lanes/BUFFY.md, DALE.md, HANA.md, MILO.md, PAX.md, ROWAN.md:
  the Repo line now names ~/workspace/repos/meta-os and
  Mrfentmen/meta-os; the Git workflow line now carries the ruled note
  with the ruling date, the new repo, the base layer, and the
  main-landing practice; the New code line now names the meta-os repo.
- plan/MASTER_PLAN.md: the "Hard rules" bullet that called the conflict
  parked for Dale now records it resolved, with the INT-012 date.
- intel/notes/milo-reuse-audit.md: dependency item 4 now records the
  ruling instead of "stays local and unpushed".

## Deliberately unchanged, and why

- README-MUSE-RELAY.md line 337 ("do the work on a feature branch"):
  that is the inherited relay base's own worker job flow (a mos worker
  doing job work on a branch), not this repo's crew workflow. Changing
  it would rewrite base product behavior docs, so it stays, and the
  lane notes now say explicitly that it does not override the ruling.
- The INT-012 and GOV-003 task definitions themselves: task text is
  history, not status, so it stays as written.
- No code changed, so no behavior changed. The only new code is the
  pinning test file.

## Verification

- Baseline suite at tip bfa1a70: 1240 tests, 1 failure, the known
  environmental test_live_matches_vendored (external skill path absent
  from the sandbox, listed in hackathon/known-failures.txt).
- After this batch: 1247 tests (1240 baseline plus 7 new), same single
  known failure, no new failure.
- The new doc carries no em dash, so the check.sh new-doc dash scan
  stays green. This doc is new, so it is scanned; the lane files are
  pre-existing and grandfathered, but the edited lines carry no em
  dash either.

## Not proven here

- Nothing about bus posting, Spark access, or dashboard deploys: this
  batch touches plan and note files only.
- Whether any other lane member has read the updated lane files: the
  files are in the repo, the read is theirs to do.
