# MT-04 in full detail — Officina loop, one full cycle (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 22:28 EST. This is a fixture/spec, not a
run. No Officina cycle has been run under MT-04, no harness output has
been produced under MT-04, and nothing below is a pass. Firing waits on
BOTH: (1) Del tops up Meta API billing (HTTP 402 during Pax's live hunt
#3), and (2) Del picks a key route (Route A: key placed on Milo's VM;
Route B: Milo specs, Pax executes the live run and posts the receipt,
Milo verdicts it). Pax directed 2026-11-02 ~22:27 EST that MT-04 detail
comes next as PREP ONLY, $0, same terms as MT-03, no live-key call, and
that live runs stay held until Del picks a key route AND the 402 is
topped up. That direction stands after the d835b59a decoupling
amendment (frozen contracts, no lane waits on another), which changes
the audit lane, not this MT chain. Spend cap $10 total for the whole
directive, guardrail-tracked; cost for MT-04 is TBD at fire time from
the published Spark rates, never invented here. Nothing dials a real
service from this prep, ever.

## What the check is

One full Officina cycle, per os-build/MILO_TEST_SLICE.md and
os-build/MILO_TEST_PREP.md: the faber loop runs one cycle against its
harness. On origin/main the concrete pieces are:

- The workshop loop: `os/worlds/officina/runtime/design_loop.py` —
  post one job per sampled variant, claim each job, score it with the
  heatsink simulator, complete it (feasible) or fail it (constraint
  violation, score still recorded), keep the feasible jobs with the
  lowest thermal resistance, then the stage-1 acceptance gate: the
  best design only counts as workshop-proven after an independent
  re-score under held-out conditions, clearing the stage-1 bar
  (R <= 2.0 degC/W) at design conditions AND held out, and staying
  feasible held out. The loop is offline: no model calls anywhere,
  the simulator is code, the loop only counts what the simulator
  returns. A seeded replay is exact (`run_loop` with the same seed
  gives the same jobs and score curve).
- The build-order seam: `os/worlds/officina/runtime/faber.py` —
  `run_order(order, stages)`. The material is checked before any stage
  runs: an unknown material is a refused order, not a stage failure,
  and the caller's stage functions must not be called at all. Known
  materials on main: aluminium, copper, steel.
- The harness: `tests/officina/` — run from the repo root with
  `python3 -m unittest discover -s tests/officina -v`, offline and
  $0, no model calls, no network, no bus. The loop-record shape is
  pinned by `tests/officina/test_officina_loop_record.py` against
  the real run files in `os/worlds/officina/runs/` (for example
  `forced-airflow-run-001.json` and `overnight-run-001.json`), never
  a hand-built copy.

One MT-04 cycle therefore means: one seeded design-loop run carried
through post -> claim -> score -> complete/fail -> held-out re-score
-> gate verdict, with the faber build-order check on the resulting
order, and the `tests/officina/` harness run alongside it. A cycle
that skips the held-out re-score, or that trusts a stored score
instead of recomputing it, does not satisfy MT-04.

## The green-cycle distinction — read this before firing

The slice's "known `green cycle` failure" does NOT belong to the
Officina loop on main, and this prep does not pretend otherwise. On
origin/main the `green cycle` scenario is the OS loop harness:
`os/os/loop-tests/metaos-loop.test.sh` run against `bin/metaos-loop`
with a stub agent (no real OpenCode, no network), where scenario 1 is
"green cycle commits, closes the task, tags a checkpoint, logs
committed", and the standing record is 11 of 12 pass with `green
cycle` failing (README.md, `os-build/bond-evidence/logs/os-loop.log`,
`os-build/logs/OC1B-readme-loop.txt` all say so). No `green` hit
exists in `os/worlds/officina/` or `tests/officina/` on main.

So MT-04's firing record carries TWO legs, kept separate, neither
conflated with the other:

- Leg A (Officina cycle): the design-loop run plus faber order
  check plus `tests/officina/` harness output, as above.
- Leg B (green-cycle report, as-is): one run of
  `bash os/os/loop-tests/metaos-loop.test.sh` (stub agent, no
  network), with its `green cycle` line copied verbatim into the
  record — pass or fail, exactly as it came out, never worked
  around, never smoothed over.

Question for Pax (not a blocker on this prep): confirm Leg B
belongs in the MT-04 record, or whether the green-cycle item is a
separate OS-loop item that should be filed outside MT-04. This prep
keeps it in the record, labelled as the OS loop harness, so nothing
is lost either way.

## Pass rules

MT-04 passes cleanly only when all of these hold on the fired record:

1. The cycle record exists and is findable from
   MILO_TEST_STATUS.md, landed on main by Pax (Route B) or by Milo
   (Route A), named so the check is in the filename.
2. The harness output exists alongside it: the full
   `tests/officina/` run, with every test's pass/fail shown, none
   hidden. A run that reports only the passing tests is incomplete.
3. Every design job in the cycle record carries its status, its
   score, and — for every failure — its failure reason. A failure
   without a score, or without a reason, fails the record shape.
4. The held-out re-score is present, recomputed from the parameters
   (never a trusted stored score), and the gate verdict follows the
   stage-1 bar: R <= 2.0 degC/W at design conditions AND held out,
   feasible held out. A design that clears only at design
   conditions is not workshop-proven.
5. The faber order check is present: the order's material is named,
   and if it is unknown, the record shows a refused order with no
   stage run — never a stage failure, never a silently skipped stage.
6. Leg B's green-cycle line is present verbatim. If green cycle
   still fails, that failure is reported as-is in the record and the
   MT-04 outcome is `partial`, not a clean pass and not a hidden
   fail: the Officina cycle is proven, the known failure is still
   present and named. A clean `pass` needs both legs clean.
7. Spend for the record is stated in actual dollars, and the running
   total against the $10 cap is updated in MILO_TEST_STATUS.md at
   fire time. A record with no spend line is incomplete. (The
   Officina loop and its harness are offline code, so the expected
   spend is $0; that expectation is confirmed at fire time, not
   claimed as a result here.)
8. A failure anywhere else in the cycle is recorded as a failure
   with its cause named, never answered with fabricated data, never
   relabelled as a success, never dropped from the record.

An honest cycle in which no design clears the bar is a legitimate
record, not a pass: the outcome is `fail` (or `partial` if the run
stopped early, for example at a budget stop, with the record saying
where it stopped and what never ran). A run with a missing record,
a missing harness output, a hidden failure, or a fabricated score
is not a pass.

## Run record shape — one cycle record plus harness output

One record, landed on main by Pax (Route B) or by Milo (Route A),
for example os-build/MILO_TEST_MT04_RECORD.md plus the harness
output file (exact filenames are set at fire time; what matters is
that both exist and are findable from MILO_TEST_STATUS.md). Each
record contains, verbatim field names where the loop already uses
them:

- `check`: `"MT-04"`.
- `main_tip`: the origin/main commit the run was fired from.
- `route`: `"A"` or `"B"`, plus who executed the live steps and who
  issued the verdict (Route B: Pax executed, Milo verdicts from the
  receipt; Route A: Milo executed and verdicts).
- `spend_usd`: actual spend for this record; running total against
  the $10 cap is updated in MILO_TEST_STATUS.md at fire time.
- `seed`: the seed used for the design-loop run, so the replay can
  be checked exact.
- `jobs`: every design job in the cycle, each with `job_id`,
  `params`, `status`, `score_r_th_c_per_w`, and `failure_reason`
  (null only for non-failures) — the shape
  `test_officina_loop_record.py` pins.
- `gate`: the held-out re-score and the workshop-proven verdict
  against the R <= 2.0 degC/W bar, at design conditions and held
  out.
- `faber`: the order, its material, and either the stage results
  or the refused-order record (unknown material, no stage ran).
- `harness`: the full `tests/officina/` output, pass and fail alike.
- `green_cycle`: Leg B's verbatim line from
  `metaos-loop.test.sh` — `ok` or `FAIL - green cycle` — plus the
  harness's own summary counts (for example the standing 11 of 12).
- `outcome`: `"pass"` | `"fail"` | `"partial"` — clean pass only
  when every rule above holds, including a clean green-cycle line;
  green-cycle failure alone gives `partial` with the failure named.
- `failures`: every failure named, none hidden.

## Firing steps, by route (same steps, different hands)

Route B (the route that works once credits exist, no key movement):
Pax runs the single Officina cycle plus the faber order check plus
the `tests/officina/` harness plus the `metaos-loop.test.sh` green
line, posts the cycle record plus the harness output, and Milo
verdicts them against the pass rules above, in his own words, on
room 1 and in MILO_TEST_STATUS.md.

Route A (only after Del places the key on Milo's VM): Milo runs the
same steps himself, inside the cap, posts the records, and verdicts
them the same way. (Note: the Officina loop, its harness, and the
OS loop harness are all offline code with no model calls, so at fire
time Pax may confirm MT-04 needs no key at all; until Pax says so,
this prep follows the same hold as MT-03 and fires nothing.)

Either route: if the 402 is still present at fire time, the run does
not start; MT-04 stays BLOCKED and the attempt (not a result) is
noted in MILO_TEST_STATUS.md. If the cap is hit mid-cycle, the cycle
stops, the record is marked partial, and the tally is posted to
room 1. No excluded bus file is touched (bus-tools/* and
tests/test_bus_admin_e2e.py stay out of every step), and no frozen
file is edited: syscalls.rs stays frozen, kernel/src stays Rowan's
pen.

## What this prep does NOT claim

- No MT-04 run has happened. No Officina cycle has been run under
  MT-04, no `tests/officina/` harness output exists yet from MT-04,
  and no `metaos-loop.test.sh` green-cycle line has been produced
  under MT-04.
- No faber order has been placed under MT-04, and no material has
  been checked under MT-04.
- The 11-of-12 / green-cycle-fails numbers above are the standing
  record on main (README.md and the bond-evidence / OC1B logs), not
  a fresh MT-04 measurement. A fresh measurement happens at fire
  time and may differ; the fresh line is what the record carries.
- Nothing here is a pass, and the green-cycle distinction above is
  a question to Pax, not a verdict: if Pax rules Leg B out of
  MT-04, the MT-04 record drops Leg B and the green-cycle item is
  filed wherever Pax says, with this file corrected to match.
