# MT-05 in full detail — Musica keeper, overnight pattern in miniature (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 22:48 EST. This is a fixture/spec, not a
run. No Musica keeper miniature has been run under MT-05, no ledger has
been written under MT-05, and nothing below is a pass. Firing waits on
BOTH: (1) Del tops up Meta API billing (HTTP 402 during Pax's live hunt
#3), and (2) Del picks a key route (Route A: key placed on Milo's VM;
Route B: Milo specs, Pax executes the live run and posts the receipt,
Milo verdicts it). Pax directed 2026-11-02 ~22:40 EST that MT-05 detail
comes next as PREP ONLY, $0, no live-key call, same terms as MT-03, and
that live runs stay held until Del picks a key route AND the 402 is
topped up. Pax also ruled at the same time that MT-04's Leg B stays a
separate verbatim leg in the MT-04 record; that ruling is recorded in
MILO_TEST_MT04.md's terms and does not change this file. Spend cap $10
total for the whole directive, guardrail-tracked; cost for MT-05 is TBD
at fire time from the published Spark rates, never invented here.
Nothing dials a real service from this prep, ever.

## What the check is

One Musica overnight pattern in miniature, per os-build/MILO_TEST_SLICE.md
and os-build/MILO_TEST_PREP.md: the keeper starts, ticks, and writes its
ledger on a short clock. On origin/main the concrete pieces are:

- The overnight pipeline: `os/worlds/musica/runtime/overnight.py` —
  `run_overnight(session_dir, brief_id, brief_file, takes, seed_base)`,
  stages in order: compose -> keeper pass -> variation pass -> catalogue
  (with `--no-copy` behaviour in the pipeline: the catalogue points at
  the reproducible take files, so a session does not bloat the repo
  with audio copies) -> rights check (enforced) -> board. It writes
  `overnight-report.json` in the session dir: takes, keepers, rejects,
  reject rate, and the catalogue delta (keepers this run added).
  Exit code 0 on a completed run, even with rejects: rejects are a
  normal outcome, not an error.
- The keeper bar: `os/worlds/musica/runtime/keepers.py` (HN-030) —
  `measure(path, params)` returns duration_s, rms_dbfs, silence_ratio,
  repetition; `keeper_verdict(m)` returns `keeper` only when length,
  loudness, silence, and repetition all pass, otherwise `reject` with
  every failed reason named (duration outside its range, loudness
  outside its dBFS range, silence ratio at or over its cap, repetition
  at or over its cap).
- The ledger: `os/worlds/musica/runtime/take_log.py` (HN-028) — every
  composition attempt is one line in `take_log.jsonl`: take_id
  (`take-001` style, unique within its session), session_id,
  timestamp (ISO-8601 with T separator and timezone), brief_id, prompt,
  seed (int >= 0; same seed + params renders byte-identical audio),
  params (tempo, key, mode, waveform, bars), duration_s, file, sha256
  (64 lowercase hex of the rendered file), verdict (`keeper` |
  `reject` | `pending`), reason (non-empty for keeper/reject),
  spark_assist (null, or `{status, prompt_sha256}` where status is
  `held` | `not_configured` | `sent` — never a fabricated model
  reply; in a sandbox with no key every attempt records
  `not_configured` and no call is sent), plus the keeper measurement
  when the keeper pass has run.
- The miniature's pinned shape: `tests/musica-overnight.test.mjs`
  (HN-040) runs the pipeline on a small session — `--takes 5`,
  `--brief-id chipsynth`, brief file
  `os/worlds/musica/briefs/chipsynth.md`, `--seed-base 11000` — and
  asserts the honest-count rules (see Pass rules). And
  `tests/musica-keepers.test.mjs` (HN-030) pins the bar itself: a real
  rendered take (tempo 132, key C, minor, square, 4 bars, seed 777)
  must pass, while a silent 8s take must fail loudness + silence, a
  truncated 1s take must fail duration, and one bar of tone repeated
  4x must fail repetition.

One MT-05 miniature therefore means: one `overnight.py` run at the
small-session size (`--takes 5`, chipsynth brief, seed-base 11000,
unless Pax directs a different seed-base at fire time), with the
keeper bar spot-checked against the same four cases the HN-030 test
pins, and the ledger + report + catalogue + board all present in the
session dir afterwards. A run that reports only the keepers, or that
drops a reject line from the ledger, does not satisfy MT-05.

## The "short clock" mapping — read this before firing

The slice says the keeper "starts, ticks, and writes its ledger on a
short clock". On origin/main there is no literal ticking keeper daemon
and no clock daemon in `os/worlds/musica/runtime/`; the overnight
pipeline is a single runnable job, not a daemon. So this prep maps the
words onto the code that actually exists, and names the mapping so
Pax can correct it:

- "starts" = the `overnight.py` run starting in a fresh session dir.
- "ticks" = one tick per take through the pipeline stages: compose ->
  keeper pass -> variation pass -> catalogue -> rights check -> board,
  with one `take_log.jsonl` line written per take.
- "short clock" = the miniature size: 5 takes instead of the default
  100, so the pattern completes in seconds rather than overnight.
- "ledger" = `take_log.jsonl` (one line per take, HN-028 schema) plus
  `overnight-report.json` (the counts) plus `catalogue.json` (the
  keepers this run added).

Question for Pax (not a blocker on this prep): confirm this miniature
mapping, or say whether MT-05 wants a literal ticking keeper daemon
that does not exist on main yet — in which case that daemon is a
build task outside this MT chain, and MT-05 stays with the miniature
above until Pax says otherwise. This prep keeps the miniature, so
nothing is lost either way.

## Pass rules

MT-05 passes cleanly only when all of these hold on the fired record:

1. The session record exists and is findable from
   MILO_TEST_STATUS.md, landed on main by Pax (Route B) or by Milo
   (Route A), named so the check is in the filename.
2. The overnight report exists in the session dir and its counts are
   honest: takes = 5 (or the fire-time takes value, stated in the
   record), keepers + rejects = takes, catalogue_delta = keepers,
   rights_violations = 0, reject_rate between 0 and 1 inclusive.
   A report whose counts do not add up is not a pass.
3. The ledger exists: every take in the report has exactly one
   `take_log.jsonl` line, each line validates against the HN-028
   schema (take_id shape, timestamp shape, sha256 shape, verdict in
   keeper/reject/pending, non-empty reason for keeper/reject), and
   no take is missing or duplicated. A ledger with a missing line is
   incomplete, not a pass.
4. The keeper bar spot-check is present: the same four HN-030 cases —
   real take passes; silent take rejects with loudness + silence
   named; truncated take rejects with duration named; single-bar
   loop rejects with repetition named. A bar check that skips a
   degenerate case is incomplete.
5. The catalogue and board exist in the session dir (`catalogue.json`
   and `board.html`), and the catalogue's track count equals the
   report's keepers. A catalogue that counts differently from the
   report fails the record shape.
6. Rights violations are 0. Any violation is named in the record and
   the outcome is `fail`, even if every other count is clean.
7. Rejects are normal: a run with rejects is not a failure for having
   rejects. The outcome is `fail` only when a rule above breaks, a
   stage errors, or a failure is hidden — never merely because a
   take was rejected.
8. Spend for the record is stated in actual dollars, and the running
   total against the $10 cap is updated in MILO_TEST_STATUS.md at
   fire time. A record with no spend line is incomplete. (The
   miniature renders offline with no model calls, so the expected
   spend is $0; that expectation is confirmed at fire time, not
   claimed as a result here. If spark assist is switched on for any
   take at fire time, its status must read `sent` with a real
   prompt_sha256, and its spend counts against the cap.)
9. A failure anywhere else in the run is recorded as a failure with
   its cause named, never answered with fabricated data, never
   relabelled as a success, never dropped from the record.

An honest miniature in which every take is rejected is a legitimate
record, not a pass: the outcome is `fail` only if a rule above
breaks; a run that completed cleanly with all rejects and honest
counts is reported as such, with the verdict saying exactly that
(the bar rejected everything, the pipeline itself ran clean). A run
with a missing report, a missing ledger line, a hidden failure, or a
fabricated count is not a pass.

## Run record shape — one session record plus ledger

One record, landed on main by Pax (Route B) or by Milo (Route A),
for example os-build/MILO_TEST_MT05_RECORD.md plus the session dir
contents (exact filenames are set at fire time; what matters is that
all of them exist and are findable from MILO_TEST_STATUS.md). Each
record contains:

- `check`: `"MT-05"`.
- `main_tip`: the origin/main commit the run was fired from.
- `route`: `"A"` or `"B"`, plus who executed the live steps and who
  issued the verdict (Route B: Pax executed, Milo verdicts from the
  receipt; Route A: Milo executed and verdicts).
- `spend_usd`: actual spend for this record; running total against
  the $10 cap is updated in MILO_TEST_STATUS.md at fire time.
- `session`: the session dir name, brief_id (`chipsynth` unless Pax
  directs otherwise at fire time), brief file, takes value, and
  seed-base used, so the run can be replayed exact (same seed +
  params renders byte-identical audio).
- `report`: the `overnight-report.json` counts verbatim — takes,
  keepers, rejects, keeper_rejects, clones, catalogue_tracks,
  catalogue_delta, rights_violations, reject_rate, elapsed_s.
- `ledger`: the `take_log.jsonl` lines (one per take, take_id,
  verdict, reason, sha256, measurement where the keeper pass ran),
  or the session dir path where the ledger lives, with the line
  count stated and matched against the report's takes.
- `keeper_bar`: the four HN-030 spot-check results, each with its
  verdict and its named reasons.
- `catalogue_board`: catalogue.json track count and board.html
  presence, matched against the report's keepers.
- `outcome`: `"pass"` | `"fail"` | `"partial"` — clean pass only
  when every rule above holds; a run that stopped early (for
  example at a budget stop) is `partial` with the record saying
  where it stopped and what never ran.
- `failures`: every failure named, none hidden.

## Firing steps, by route (same steps, different hands)

Route B (the route that works once credits exist, no key movement):
Pax runs the 5-take overnight miniature plus the four keeper-bar
spot-checks, posts the session record plus the report, ledger,
catalogue, and board, and Milo verdicts them against the pass rules
above, in his own words, on room 1 and in MILO_TEST_STATUS.md.

Route A (only after Del places the key on Milo's VM): Milo runs the
same steps himself, inside the cap, posts the records, and verdicts
them the same way. (Note: the miniature renders offline with no
model calls, so at fire time Pax may confirm MT-05 needs no key at
all; until Pax says so, this prep follows the same hold as MT-03 and
fires nothing.)

Either route: if the 402 is still present at fire time, the run does
not start; MT-05 stays BLOCKED and the attempt (not a result) is
noted in MILO_TEST_STATUS.md. If the cap is hit mid-run, the run
stops, the record is marked partial, and the tally is posted to
room 1. No excluded bus file is touched (bus-tools/* and
tests/test_bus_admin_e2e.py stay out of every step), and no frozen
file is edited: syscalls.rs stays frozen, kernel/src stays Rowan's
pen.

## What this prep does NOT claim

- No MT-05 run has happened. No overnight miniature has been run
  under MT-05, no `take_log.jsonl` ledger line exists yet from MT-05,
  and no `overnight-report.json` counts exist yet from MT-05.
- No keeper-bar spot-check has been run under MT-05; the four cases
  above are the HN-030 test's pinned cases on main, not fresh MT-05
  measurements. Fresh measurements happen at fire time and may
  differ; the fresh results are what the record carries.
- No ticking keeper daemon exists on main, and none is claimed here:
  the "short clock" mapping above is a mapping onto the overnight
  pipeline, flagged as a question to Pax, not a verdict.
- Nothing here is a pass, and the mapping question above is a
  question to Pax, not a verdict: if Pax rules the miniature mapping
  out, this file is corrected to match whatever Pax directs.
