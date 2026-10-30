# OS-106: the measured A/B run + image-defect attribution (Milo, 2026-10-27)

OS-106's acceptance, proven on fixtures: one A/B result
in hand for the demo's one comparison (bare launch vs
mind image), the same jobs under both versions, times
and acceptance outcomes recorded, and at least one
observed stall correctly attributed as an image defect
with the journal evidence named.

## The comparison

Fixed suite of four small jobs, run under two fixture
image versions. Bare launch: no skills, no
instructions, thin brief. Mind-v1: skills git-review
and brief-read, instruction "verify acceptance before
closing", full brief. Module `intel/abrun.py`, drill
`intel/drills/ab_run.py` (6/6 phases PASS).

| job | bare: seconds, outcome | mind-v1: seconds, outcome |
| --- | --- | --- |
| job-a (review the patch) | 420, fail | 120, pass |
| job-b (summarize repo state) | 300, fail | 90, pass |
| job-c (worker dies mid-job) | 200, fail | 200, fail |
| job-d (tidy the notes) | 180, pass | 60, pass |
| total | 1100, 1 pass | 470, 3 pass |

Mind-v1 is faster in total (470 vs 1100 seconds) and
passes more jobs (3 vs 1). Job-c fails under both
versions with the same worker fate, which is the
control the attribution discipline needs: a dead
worker under a complete image is a worker failure,
not an image defect.

## Defects found, with journal evidence

- job-a under bare: image-defect missing-skill.
  Evidence: journal line "worker stalled: needs skill
  git-review to review the patch". The bare launch
  carries no skills, so the stall is the image's
  fault, not the worker's. Mind-v1 carries git-review
  and passes the same job.
- job-b under bare: image-defect thin-brief.
  Evidence: journal line "worker stalled: no repo
  context in the brief". The bare brief is thin; the
  mind-v1 brief is full and the job passes.
- job-c under both versions: worker-failure, cause
  "worker died", evidence "worker process died
  mid-job". Zero defects attributed for job-c under
  either version.
- Attribution discipline, proven in the drill: a
  stall naming a skill the image carries is no defect;
  a stall naming an instruction the image does not
  carry is no defect; a stall naming a carried bad
  instruction ("skip acceptance checks") is a
  bad-instruction defect; a stall naming neither an
  image layer nor a worker cause is unattributed,
  never guessed.

## Revision note (proposal only)

From the two comparison defects, `revision_note`
proposes: add skill git-review to the skills layer,
and thicken the environment brief layer for job-b's
shape of work. Nothing auto-applies; the revision
loop tooling is Pax OS-109, which has not landed.

## NOT proven here

- The real OS-105 harness (Buffy) has not landed, so
  this run is the OS-105 shape on fixtures, not an
  execution of that harness. When it lands, this
  comparison should be re-run through it.
- No live agent ran under either version, no booted
  test image exists in this repo, and no live worker
  was killed and resumed.
- The board view of this result (Rowan OS-107) is
  not part of this task; the result here is a table
  and a drill log, not a board screen.
- The numbers are fixture seconds, not wall-clock
  measurements of real runs; the comparison proves
  the recording and attribution machinery, not that
  mind-v1 is faster in production.
