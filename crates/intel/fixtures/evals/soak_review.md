# OS-074 eval: seven-day soak journal review, review half only (Milo)

OS-074 acceptance: the full crew plus all drivers run
unattended on Meta OS for 7 days, and the watchdog
journal is reviewed end to end: every silent failure
in the log has an alert or a filed bug, and zero
unexplained gaps remain.

## What was built

- `intel/soak_review.py`: pure review of a fixture
  journal. A silent failure is covered when at least
  one alert or one filed bug names its id. Covers
  naming a failure that never appears are orphans:
  reported, never counted. Duplicate covers still
  count as one coverage. Malformed entries are
  skipped, never a crash. A failure without a usable
  day 1 to 7 still counts and is listed undated, so
  the report never pretends to know its day. Days
  present and days missing are reported separately
  from the verdict, so a partial journal is visible
  as partial instead of silently passing as a full
  week. Brief lines name the gaps and the verdict.
  Inputs are never mutated, and the module has no
  push path.
- `intel/drills/soak_review.py`: 20 checks, all PASS.
- Pinning tests: `tests/test_intel_soak_review.py`
  (13 tests).

## What the drill proves

- A clean 7-day fixture journal reads clean with zero
  gaps: 3 failures, 3 covered, all 7 days present.
- Bug coverage counts; alert plus bug are both listed
  for one failure; a duplicate alert still counts as
  one coverage.
- Removing the one bug for a failure makes that
  failure the one unexplained gap, verdict gaps, with
  2 of 3 still covered.
- A partial journal (days 1, 3, 5 only) names its
  missing days 2, 4, 6, 7.
- Orphan covers are reported (2) and never counted.
- Malformed entries are skipped (3), never a crash;
  an undated failure is listed and is still a gap
  when uncovered.
- An empty journal is clean with zero failures and
  all 7 days missing; a non-list journal reads as
  empty, never a crash.
- Inputs are never mutated, the report carries no
  push and no announcement field, and the module
  imports no push module.

## What this does NOT claim

- The seven-day soak itself. No booted Meta OS image
  runs in this repo, the crew does not run on Meta OS
  here, and seven days have not elapsed on any such
  image. OS-074 stays OPEN: this run lands only the
  review tool its acceptance will use, on fixtures.
- A real soak report. No live watchdog journal was
  reviewed here; the journals are fixtures written
  for the drill.
- Any live crew, driver, or machine behavior, any bus
  post, and any Dale contact. The review is decision
  only and has no push path by design.
