# OS-125: the baton pass (Milo, 2026-10-27)

OS-125's acceptance, proven on fixtures: a worker is
killed mid-job; the watchman passes the baton and the
job completes with no repeated work -- the record shows
the deposited progress, zero duplicated file changes,
and a continuation prompt that names what remains
instead of restating the whole job. In-window the
continuation is proven same-program; the cross-program
pass (for example Muse to Freebuff, possible because
both are pre-installed in the image) is the named
stretch line -- run before freeze if the drivers allow,
honestly reported either way.

The baton (intel/baton.py) is the OS-095 ladder's
reassign half, made whole. The ladder's baton_for was a
minimal snapshot copy (title, progress timestamp,
files); compose_baton is the full continuation the
acceptance demands: goal from the goal field or the
spec's Goal line, deposited progress notes, completed
vs remaining files (files minus completed, in order),
remaining steps (the remaining list, else steps minus
completed steps), and acceptance checks (list form, else
the jobs.py accept string split on lines). Nothing is
invented: a missing goal reads as not stated, a job with
no deposited progress says so plainly, and a missing
remaining list reads as not stated rather than guessed.
The module composes only and never moves a claim: the
overseer moves it, worked mechanically by the watchman
(Pax OS-118), and the drill's simulated overseer move
is harness, not a live claim. It has no push path, so
Dale is contacted at no rung of this pass.

The drill (intel/drills/baton_pass.py, transcript
intel/evals/baton_pass.log) runs five phases, all PASS:

- full-pass: worker pax killed mid-job 7 after depositing
  two progress notes on a.txt; the baton names the goal,
  both notes, a.txt as already changed, b.txt and c.txt
  as still to touch, both remaining steps, and both
  acceptance checks; a.txt never appears under files
  still to touch; the simulated next worker hana writes
  only b.txt and c.txt, so the written set meets the
  completed set at nothing and the finished record
  carries all three files done.
- no-progress: a job with no notes and no completed
  files yields an honest prompt (no progress deposited,
  no completed-file record), every file still to touch,
  and the accept string parsed to its two checks.
- malformed: non-records, id-less records, and missing
  jobs yield nothing, no crash; comma-separated files
  and newline-separated accept strings parse to the same
  lists as the list forms; a spec Goal line is read.
- idempotent and immutable: a second pass tick journals
  nothing new, composing leaves the job record unchanged,
  and the brief line names job, both workers, and the
  remaining file count (2).
- no-dale: the pass record carries no push or
  announcement field, and the baton module imports no
  push path.

Pinning tests: tests/test_intel_baton_pass.py (14
tests: full composition, remaining-files derivation,
remaining-steps derivation, acceptance parsing, goal
from field and from spec, no-progress honesty, malformed
records, pass tick and dedupe, brief lines, immutability,
no push path, drill pass, eval note, no em dash).

NOT proven here: a live worker actually killed and
resumed, a real overseer claim move on a booted test
image (no test image in repo), the watchman's
mechanical execution of the pass (Pax OS-118), or the
cross-program pass (two agent programs, not run here).
The plan/META_OS.md spec line is Pax's to add: shared
files are integrator-only under the 2026-10-27 folders
rule, so this batch touches lane paths only.
