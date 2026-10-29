# Meta Ignis evaluation (Rowan's lane)

Scenario set, eval adapter, and runner for Meta Ignis
(FDNY-oriented fire and smoke hazard awareness), under the frozen
Meta Trio v2 contract (`../js/schema.js`, `FIRST_RESPONSE.md` section 4).

This mirrors the shape of Milo's Meta Sanitas harness
(`../sanitas/harness.mjs`) for the Ignis product, without touching
Milo's files: the same per-scenario record shape, the same metric
math (imported from the Sanitas harness, which is product-agnostic),
the same malformed-input containment. Product-specific evaluation
stays separate, per the trio lock (Rowan owns Meta Ignis).

## Files

- `scenarios.json` — 20 labeled scenarios with ground truth. Labels
  were authored in this file before any assessment source ran against
  them; the adapter reads it read-only and never mutates it. Covers
  all seven ignis categories: visible smoke, visible flame, no hazard
  visible, steam or fog, flame-like lighting, obscured or distant
  hazard, and indeterminate — plus confusable negatives: steam from a
  vent, morning fog, sunset glow on windows, orange neon, vehicle
  lights in rain.
- `adapter.mjs` — `validateIgnisScenarios` / `runIgnisEval` /
  `formatIgnisReport` / `assessViaModelAdapter` / `computeMetrics`
  (re-exported from the Sanitas harness). No dependencies, no network
  beyond what the server adapter itself gates.
- `baseline.mjs` — always-no-hazard baseline (`assessBaseline`).
  Predicts "no hazard visible" for every scene, fires no alert,
  performs no inspection. Mirrors `../sanitas/baseline.mjs`.
- `stub.mjs` — deterministic fixture source (`assessStub`). NOT a
  model: a table keyed by scenario_id, deliberately imperfect, with
  its misses documented in the file before any run. Mirrors
  `../sanitas/stub.mjs`.
- `run.mjs` — held-state runner. Prints the report for the wired
  source and says plainly that its numbers describe source
  availability, not model performance. With `--baseline`, runs the
  same scenario set against the baseline instead. With `--stub`,
  runs the same scenario set against the fixture stub, then the
  baseline, and prints the stub-vs-baseline comparison. With
  `--out <path>`, writes the run JSON; its source/generated labels
  are evidence-based (all-held refusal → held-state, any returned
  assessment → live-model), so a future live run is never mislabeled
  as held by a stale runner string.
- `report.mjs` — run-report renderer. Turns a `run.mjs --out` JSON
  file into the markdown format of the report trio, classifying the
  run by record evidence (all-held refusal → held-state, named
  fixture source → fixture, any returned assessment → live-model),
  never by its labels alone — so a live run renders as live even if
  it was produced by an older run.mjs. `--baseline <baseline-run.json>`
  adds the recall-and-category-accuracy verdict against the baseline, with signed deltas
  for both bar metrics.
  `--out` to a trio filename is refused: a live run belongs in its
  own `live-run-report.md`, never as an edit to the trio. With a baseline supplied, the
  comparison section renders signed recall and category-accuracy deltas (this run minus
  baseline, n/a when either side is n/a) alongside the beat-the-baseline verdict. It also
  renders a truth-vs-predicted category table and a
  confusable-negative breakdown (steam or fog / flame-like lighting
  predicted as an alert category), so alert-level metrics cannot hide
  systematic category swaps. A headline finding above the full table
  names the weakest truth category (lowest category-correct rate)
  and the most-confused truth -> predicted pair; when nothing was
  assessed it says so instead of naming a category, and ERROR counts
  as a failure, never as a confusion. It also names the slowest
  scenario by harness wall-clock latency, or says none was recorded
  when no record carries one, so the latency tail needs no scan of
  the per-scenario table. A per-category rate table right
  below the headline backs the weakest claim: one correct/total rate
  per truth category (unassessed records count as misses, matching
  category-accuracy semantics), with an assessed column so a
  held-state row of 0.000 reads as nothing assessed, not a measured
  zero — so the headline is checkable without counting the confusion
  matrix. The Misses section names each miss as truth -> predicted
  (ERROR with a no-assessment note for unassessed records), so a miss
  is diagnosable without cross-referencing the per-scenario table.
  A miss-pair counts table right after it aggregates those misses by
  truth -> predicted pair, most frequent first, so the dominant swap
  is visible without counting the Misses list; ERROR rows there are
  failures, not confusions. The per-scenario table carries each
  record's harness wall-clock latency (n/a when the record carries
  none), so a slow scenario is visible without the summary
  statistics, and flags a latency outlier (yes) when a scenario's
  latency is more than twice the run's median recorded latency;
  runs with fewer than two recorded latencies, or a median of zero,
  flag nothing rather than singling a scenario out on a zero baseline.
  An error-breakdown section splits the summary line's error total
  by exact message (most frequent first, ties alphabetical), so a
  run that fails in several different ways reads as a failure
  profile, not one lump; a run with no errored records says none.
  A latency distribution section expands the summary line's
  mean/median/max into min, quartiles and p90 over the recorded
  harness latencies, so the tail is visible without scanning the
  per-scenario table; a run with no recorded latency says so
  instead of inventing one. A latency-outliers section right after
  it names the scenarios the per-scenario table flags (latency
  more than twice the median recorded latency), each with its
  latency, the run median, and the threshold; a run with no outlier
  says none, and a run with no recorded latency says none was
  recorded. A latency-by-category section right after it breaks
  the recorded latencies down by ground-truth category (count,
  mean, median, max), so a slow category is visible without
  scanning the per-scenario table; a category with no recorded
  latency shows n/a, never a fabricated zero. A latency-by-outcome
  section right after it breaks the recorded latencies down by
  outcome — correct, miss, unassessed — so a slow failure mode is
  visible without scanning the per-scenario table; all three rows
  always render, so the totals sum to the sample size, and a group
  with no recorded latency shows n/a, never a fabricated zero. A latency-by-alert-outcome
  section right after it breaks the recorded latencies down by alert outcome — true positive,
  true negative, false positive, false negative — so a slow alert failure mode is visible
  without scanning the per-scenario table; all four rows always render, so the totals sum to
  the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.
  A latency-by-alert-correctness section right after it collapses those four outcomes into
  two — alert correct (true positives plus true negatives) versus alert error (false
  positives plus false negatives) — so whether alert failures as a whole run slower than
  alert successes is visible without adding the four rows above; both rows always render,
  so the totals sum to the sample size, and a group with no recorded latency shows n/a,
  never a fabricated zero. A latency-by-alert-expectation section right after it splits
  those same latencies by whether an alert was expected at all — alert expected (true
  positives plus false negatives) versus alert not expected (true negatives plus false
  positives) — so whether alert-bearing scenarios run slower than non-alert ones is visible
  without adding the four rows above; both rows always render, so the totals sum to the
  sample size, and a group with no recorded latency shows n/a, never a fabricated zero.
  A latency-by-alert-fired section right after it splits those same latencies by whether
  an alert fired at all — alert fired (true positives plus false positives) versus alert
  not fired (true negatives plus false negatives) — completing the three two-way collapses
  of the alert-outcome split, so whether alert-firing scenarios run slower than quiet ones
  is visible without adding the four rows above; both rows always render, so the totals sum to
  the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.
  A latency-by-assessed section right after it collapses the outcome split into two —
  assessed (a category was returned, right or wrong: correct plus miss) versus unassessed
  (no assessment was returned) — so whether scenarios that fail to produce an assessment
  run slower than ones that do is visible without adding the three outcome rows above; both
  rows always render, so the totals sum to the sample size, and a group with no recorded
  latency shows n/a, never a fabricated zero. A latency-by-category-correctness section
  right after it collapses the outcome split the other way — category correct (the exact
  match) versus category incorrect (a miss plus every unassessed record) — so whether
  scenarios that get the category wrong run slower than ones that get it right is visible
  without adding the three outcome rows above; both rows always render, so the totals sum
  to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.
  A latency-by-miss-status section right after it collapses the outcome split the third way —
  miss (an assessment was returned but differed from the ground truth) versus non-miss (the
  exact match plus every unassessed record) — completing the three two-way collapses of the
  outcome split with assessed and category correctness, so whether scenarios that return a wrong
  category run slower than ones that do not is visible without adding the three outcome rows
  above; both rows always render, so the totals sum to the sample size, and a group with no
  recorded latency shows n/a, never a fabricated zero. A latency-by-predicted-category section
  right after it is the predicted-side mirror of latency by category — one row per predicted
  category present, sorted alphabetically with ERROR last (matching the confusion table, where
  an unassessed record reads as ERROR), so a slow predicted category is visible without scanning
  the per-scenario table; a category with no recorded latency shows n/a, never a fabricated zero.
  A latency-by-error-status section right after it splits the recorded latencies by whether the
  record carries an error message at all — errored (including a record that also returned an
  assessment) versus no error — so whether failing scenarios run slower than clean ones is
  visible without scanning the per-scenario table; both rows always render, so the totals sum
  to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.
  A latency-by-error-message section right after it refines the errored row per distinct error
  message — most frequent first, ties alphabetical, matching the error-message breakdown's order —
  so whether one failure mode runs slower than another is visible without scanning the
  per-scenario table; its scenario totals sum to the error count, not the sample size, since
  records with no error message appear in neither row, and a message with no recorded latency
  shows n/a, never a fabricated zero; a run with no errored records says none.
  A latency-by-truth -> predicted-pair section right after it is the joint breakdown behind latency by
  category and latency by predicted category — one row per truth -> predicted pair present, sorted by truth
  then predicted with ERROR last (matching the confusion table, where an unassessed record reads as ERROR), so
  whether one particular swap runs slower than another is visible without scanning the per-scenario table; the
  diagonal correct pairs are included, so the totals sum to the sample size, and a pair with no recorded latency
  shows n/a, never a fabricated zero.
  A latency-by-confusable-negative-status section right after it splits the recorded latencies by
  confusable-negative status — confusable negative (steam or fog, flame-like lighting), other non-alert,
  alert (visible smoke, visible flame) — so whether the false-alarm-prone scenes as a class run slower
  than the scenes that should never fire is visible without scanning the per-scenario table; all three
  rows always render, so the totals sum to the sample size, and a group with no recorded latency
  shows n/a, never a fabricated zero.
  A latency-by-miss-pair section right after it splits the recorded latencies by miss pair —
  one row per truth -> predicted pair among the misses only, most frequent first (matching the
  miss-pair counts' ordering, with an unassessed record reading as ERROR), so whether the
  dominant swap runs slower than the other misses is visible without scanning the per-scenario
  table; the totals sum to the miss count, not the sample size, and a pair with no recorded latency
  shows n/a, never a fabricated zero; a run with no misses says none.
  A latency-by-miss-truth-category section right after it is the coarser misses-only marginal
  behind the miss-pair table — one row per ground-truth category among the misses only, most
  frequent first, then truth alphabetically — so whether one truth category's misses as a class
  run slower than another's is visible without scanning the per-scenario table; the totals sum
  to the miss count, not the sample size, and a category with no recorded latency shows n/a,
  never a fabricated zero; a run with no misses says none.
  A latency-by-miss-predicted-category section right after it is the predicted-side misses-only
  marginal behind the miss-pair table — one row per predicted category among the misses only, most
  frequent first, then predicted alphabetically with ERROR last (matching the miss-pair counts'
  ordering, with an unassessed record reading as ERROR) — so whether one predicted category's misses
  as a class run slower than another's is visible without scanning the per-scenario table; the totals
  sum to the miss count, not the sample size, and a category with no recorded latency shows n/a,
  never a fabricated zero; a run with no misses says none.
  A latency-by-miss-error-status section right after it is the failure-vs-confusion split of the
  misses — one row per error-status group among the misses only, errored first (a record is errored
  when it carries an error message at all) — so whether the misses that failed outright run slower
  than the misses that returned a wrong category is visible without scanning the per-scenario table;
  only groups present among the misses render, so the totals sum to the miss count, not the sample
  size, and a group with no recorded latency shows n/a, never a fabricated zero; a run with no
  misses says none.
  A latency-by-miss-error-message section right after it is the per-message refinement of that
  failure-vs-confusion split — one row per distinct error message among the errored misses only,
  most frequent first, ties alphabetical (matching the error-message breakdown's ordering) — so
  whether one failure mode runs slower than another among the misses is visible without scanning
  the per-scenario table; the totals sum to the errored-miss count, not the miss count, since
  misses with no error message appear in no row, and a message with no recorded latency shows n/a,
  never a fabricated zero; a run with no errored miss says none.
  A latency-by-miss-alert-outcome section right after it is the alert-side split of the
  misses — one row per alert-outcome group among the misses only, in fixed order true positive,
  true negative, false positive, false negative (using alert_expected / alert_fired only, matching
  the alert-outcome definition) — so whether the misses that fired an alert run slower than the
  misses that stayed silent is visible without scanning the per-scenario table; only groups present
  among the misses render, so the totals sum to the miss count, not the sample size, and a group with
  no recorded latency shows n/a, never a fabricated zero; a run with no misses says none.
  A latency-by-miss-alert-correctness section right after it is the collapsed alert-side split of
  the misses — one row per alert-correctness group among the misses only, in fixed order alert
  correct, alert error (using the validated alert_correct field, matching the alert-correctness
  definition) — so whether the misses whose alert was right run slower than the misses whose alert
  was wrong is visible without scanning the per-scenario table; only groups present among the
  misses render, so the totals sum to the miss count, not the sample size, and a group with no
  recorded latency shows n/a, never a fabricated zero; a run with no misses says none.
  A latency-by-miss-alert-expectation section right after it is the row collapse of the misses'
  alert split — one row per alert-expectation group among the misses only, in fixed order alert
  expected, alert not expected (using the validated alert_expected field, matching the
  alert-expectation definition) — so whether the misses where an alert was expected run slower
  than the misses where none was is visible without scanning the per-scenario table; only groups
  present among the misses render, so the totals sum to the miss count, not the sample size, and
  a group with no recorded latency shows n/a, never a fabricated zero; a run with no misses says none.
  A latency-by-miss-alert-fired section right after it is the column collapse of the misses'
  alert split — one row per alert-fired group among the misses only, in fixed order alert fired,
  alert not fired (using the validated alert_fired field, matching the alert-fired definition) —
  so whether the misses that fired an alert run slower than the misses that stayed silent is
  visible in two rows without adding the four alert-outcome rows above; only groups present
  among the misses render, so the totals sum to the miss count, not the sample size, and
  a group with no recorded latency shows n/a, never a fabricated zero; a run with no misses says none.
  A latency-by-miss-assessed section right after it is the collapse of the misses' assessed split —
  one row per assessed-status group among the misses only, in fixed order assessed, unassessed (using
  the validated actual_category field, matching the assessed definition) — so whether the misses that
  returned a wrong category run slower than the misses that returned nothing is visible in two rows
  without adding the correct records the latency-by-assessed section includes; only groups present
  among the misses render, so the totals sum to the miss count, not the sample size, and a group with
  no recorded latency shows n/a, never a fabricated zero; a run with no misses says none.
  A latency-by-miss-outcome section right after it is the outcome split of the misses —
  one row per outcome group among the misses only, in fixed order miss, unassessed (the correct row
  of latency by outcome cannot occur among the misses, using the validated actual_category field,
  matching the outcome definition) — so whether the misses that returned a wrong category run slower
  than the misses that returned nothing is visible in two rows without adding the correct records
  the latency-by-outcome section includes; only groups present among the misses render, so the totals
  sum to the miss count, not the sample size, and a group with no recorded latency shows n/a, never
  a fabricated zero; a run with no misses says none.
  A latency-by-miss-confusable-negative-status section right after it is the confusable-negative
  split of the misses — one row per confusable-negative-status group among the misses only, in fixed
  order confusable negative, other non-alert, alert (using the ground-truth label, matching the
  confusable-negative-status definition) — so whether the misses on the false-alarm-prone scenes run
  slower than the misses on other scenes is visible without adding the correct records the
  latency-by-confusable-negative-status section includes; only groups present among the misses render,
  so the totals sum to the miss count, not the sample size, and a group with no recorded latency shows
  n/a, never a fabricated zero; a run with no misses says none.
  A latency-distribution-among-misses section right after it expands the miss sections' means into
  min, quartiles and p90 over the misses alone — the same quantiles as the full-run latency
  distribution, but without the correct records pulling the numbers down — so whether the misses
  cluster fast or drag a slow tail is visible at a glance; the recorded count is out of the miss
  count, not the sample size, records with no latency take no part, a run whose misses carry no
  latency says so instead of inventing a distribution, and a run with no misses says none.
  A latency-outliers-among-misses section right after it names the misses whose latency is
  more than twice the misses' median recorded latency — the same strict rule as the
  full-run latency outliers, but judged against the failures' own typical latency, so a
  slow failure is visible without the correct records moving the median or threshold;
  each outlier carries its latency, the misses' median, and the threshold, a run with
  fewer than two recorded miss latencies or a zero miss median flags nothing, a run
  whose misses carry no latency says so instead of naming one, and a run with no misses
  says none.
  A slowest-miss section right after it names the single slowest miss by harness wall-clock
  latency — the same slowest-scenario rule as the headline finding, but over the misses
  alone, so the slowest failure is visible without a correct record's slow latency hiding
  it; ties break by scenario id alphabetically, a run whose misses carry no latency says
  so instead of naming one, and a run with no misses says none.
  A fastest-miss section right after it names the single fastest miss by harness wall-clock
  latency — the mirror of the slowest miss, over the misses alone, so the quickest failure
  is visible without a correct record's fast latency hiding it; ties break by scenario id
  alphabetically, a run whose misses carry no latency says so instead of naming one, and
  a run with no misses says none.
  A latency-by-correct-category section right after it breaks the correct records' latencies down by
  category — one row per category among the correct records only, most frequent first — so whether one
  category's successes as a class run slower than another's is visible without scanning the per-scenario
  table; for a correct record truth and predicted coincide, so a single category column covers both
  sides, the scenario totals sum to the correct count, not the sample size, a category with no recorded
  latency shows n/a, never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-alert-outcome section right after it breaks the correct records' latencies down by
  alert outcome — one row per alert-outcome group among the correct records only, in fixed order true
  positive, true negative, false positive, false negative — so whether the successes that fired an alert
  run slower than the successes that stayed silent is visible without scanning the per-scenario table; for a
  genuine correct record truth and predicted coincide, so only true positives and true negatives occur and
  the false rows cover hand-built records that claim correctness with mismatched alert flags, only groups
  present among the correct records render, the scenario totals sum to the correct count, not the sample size,
  a group with no recorded latency shows n/a, never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-alert-correctness section right after it collapses those four outcomes into two —
  alert correct versus alert error — among the correct records only, in fixed order alert correct, alert error,
  so whether the successes whose alert was right run slower than the successes whose alert was wrong is visible
  without scanning the per-scenario table; both groups occur for genuine correct records, since a correctly
  categorized scene can still carry a wrong alert, only groups present among the correct records render, the
  scenario totals sum to the correct count, not the sample size, a group with no recorded latency shows n/a,
  never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-alert-expectation section right after it splits the correct records' latencies by
  alert expectation — one row per alert-expectation group among the correct records only, in fixed order alert
  expected, alert not expected — so whether the successes where an alert was expected run slower than the
  successes where none was is visible without scanning the per-scenario table; both groups occur for genuine
  correct records, since a correctly categorized scene may or may not expect an alert, only groups present
  among the correct records render, the scenario totals sum to the correct count, not the sample size, a group
  with no recorded latency shows n/a, never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-alert-fired section right after it collapses the correct records' alert-outcome split
  by column — one row per alert-fired group among the correct records only, in fixed order alert fired, alert
  not fired — so whether the successes that fired an alert run slower than the successes that stayed silent is
  visible in two rows even for hand-built records that claim correctness with mismatched alert flags; both groups
  occur for genuine correct records, since a correctly categorized scene may or may not fire an alert, only groups
  present among the correct records render, the scenario totals sum to the correct count, not the sample size, a
  group with no recorded latency shows n/a, never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-assessed section right after it splits the correct records' latencies by whether an
  assessment was returned — one row per assessed-status group among the correct records only, in fixed order
  assessed, unassessed — so whether the successes that returned a category run slower than the successes that
  returned nothing is visible in two rows without adding the misses the latency-by-assessed section includes;
  only the assessed row occurs for genuine correct records, since a correct record returned its category, and
  the unassessed row covers hand-built records that claim correctness with no assessment returned, only groups
  present among the correct records render, the scenario totals sum to the correct count, not the sample size, a
  group with no recorded latency shows n/a, never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-outcome section right after it splits the correct records' latencies by outcome — one row per outcome group among the correct records only, in fixed order correct, miss, unassessed — so whether the successes that returned the matching category run slower than the successes that claim correctness with a wrong category or no assessment is visible in three rows without adding the misses the latency-by-outcome section includes; only the correct row occurs for genuine correct records, since a correct record returned its matching category, and the miss and unassessed rows cover hand-built records that claim correctness with a wrong category returned or no assessment returned, only groups present among the correct records render, the scenario totals sum to the correct count, not the sample size, a group with no recorded latency shows n/a, never a fabricated zero, and a run with no correct records says none.
  A latency-by-correct-confusable-negative-status section right after it splits the correct records' latencies by
  confusable-negative status — one row per status group among the correct records only, in fixed order confusable
  negative, other non-alert, alert (using the ground-truth label, matching the confusable-negative-status definition) —
  so whether the successes on the false-alarm-prone scenes run slower than the successes on other scenes is visible
  in three rows without adding the misses the latency-by-miss-confusable-negative-status section includes; all three
  groups occur for genuine correct records, since a correctly categorized confusable-negative scene, other non-alert
  scene, or alert scene each lands in its own group, only groups present among the correct records render, the scenario
  totals sum to the correct count, not the sample size, a group with no recorded latency shows n/a, never a fabricated
  zero, and a run with no correct records says none.
  A latency-distribution-among-correct section right after it expands the correct sections' means into
  min, quartiles and p90 over the correct records alone — the same quantiles as the full-run latency
  distribution, but without the misses pulling the numbers up — so whether the successes cluster fast
  or drag a slow tail is visible at a glance; the recorded count is out of the correct count, not the
  sample size, records with no latency take no part, a run whose correct records carry no latency says
  so instead of inventing a distribution, and a run with no correct records says none.
  A latency-outliers-among-correct section right after it names the correct records whose latency is
  more than twice the correct records' median recorded latency — the same strict rule as the
  full-run latency outliers, but judged against the successes' own typical latency, so a
  slow success is visible without the misses moving the median or threshold;
  each outlier carries its latency, the correct records' median, and the threshold, a run with
  fewer than two recorded correct latencies or a zero correct median flags nothing, a run
  whose correct records carry no latency says so instead of naming one, and a run with no correct
  records says none.
  A slowest-correct section right after it names the single slowest correct record by harness
  wall-clock latency — the same slowest-scenario rule as the headline finding, but over the
  correct records alone, so the slowest success is visible without a miss's slow latency hiding
  it; ties break by scenario id alphabetically, a run whose correct records carry no latency says
  so instead of naming one, and a run with no correct records says none.
  A fastest-correct section right after it names the single fastest correct record by harness
  wall-clock latency — the mirror of the slowest correct, over the correct records alone, so the
  quickest success is visible without a miss's fast latency hiding it; ties break by scenario id
  alphabetically, a run whose correct records carry no latency says so instead of naming one,
  and a run with no correct records says none.
  An alert-errors section names the
  scenarios behind the summary line's FP/FN counts — false
  positives (an alert fired where none was expected) and false
  negatives (an expected alert that never fired), each with truth
  and predicted category — distinct from the category Misses, since
  it asks whether an alert fired at all, not which category was
  predicted; a clean run says none. An alert-correct section
  completes the alert-confusion set with the scenarios behind the
  summary line's TP/TN counts — true positives (an expected alert
  fired, even when the category is wrong) and true negatives (no
  alert expected, none fired); its counts match TP/TN exactly by
  the same fired-versus-expected definition, so an unassessed
  non-alert record reads as a true negative with ERROR; a run with
  no alert-correct scenario says none. A category-correct section
  after the miss-pair counts completes the category set the same
  way: the scenarios whose predicted category matched the ground
  truth exactly, so correct plus misses accounts for every scenario
  in the run; a run with no correct scenario says none.
- `report.test.mjs` — renderer tests: fixture/held/live-shaped
  classification (including assessments beating a stale held label),
  baseline comparison verdicts, per-category confusion and
  confusable-negative breakdowns, misses detail and miss-pair counts,
  error-message breakdown grouping and rendering, latency
  distribution, latency-outlier flagging and section rendering,
  latency-by-category breakdown and rendering, alert-error FP/FN
  splitting and rendering, alert-correct TP/TN splitting and
  rendering, category-correct listing and rendering, run-JSON validation, trio protection, and the CLI end to end.
- `adapter.test.mjs` — adapter tests: label loading, alert-definition
  consistency, metric math, alert-correctness logic,
  malformed-input containment, the held-state refusal, and the
  baseline's exact full-set numbers.
- `fixture-run-report.md` — the measured output of the last fixture
  run (`run.mjs --stub`), labeled as a fixture run.
- `held-state-run-report.md` — the measured output of the last
  held-state run (`run.mjs` with no flag), labeled as a held-state
  run: every scenario records the server adapter's refusal, and its
  numbers describe source availability, not model performance.
- `baseline-run-report.md` — the measured output of the last
  baseline run (`run.mjs --baseline`), labeled as a baseline run:
  the always-no-hazard source's scores, which are the bar a real
  source must beat, not model performance. With the fixture and
  held-state reports, this completes the report trio.

## The contract the adapter reads

One v2 assessment object per scenario, product `"ignis"`:

```json
{
  "product": "ignis",
  "timestamp": "ISO-8601",
  "observations": [{ "category": "...", "description": "...", "evidence": "...", "confidence": null }],
  "assessment": { "category": "...", "summary": "...", "uncertainty": ["..."], "requires_human_review": true },
  "processing": { "model": "...", "latency_ms": null }
}
```

An assessment "fires an alert" when `assessment.category` is
`visible smoke` or `visible flame`. `obscured or distant hazard`
never fires an alert on its own — a distant or partially hidden
hazard warrants human review, recorded separately — and neither do
`steam or fog`, `flame-like lighting`, `no hazard visible`, or
`indeterminate`. The label validator enforces this: a scenario whose
`alert_expected` contradicts the alert definition is rejected, not run.
Per-scenario records carry: scenario ID, expected condition,
ground-truth label, actual output, alert fired, alert correct,
evidence reference, latency (harness wall clock, never a reported
field), and any error.

## The wired source, and the Spark rule

`assessViaModelAdapter` delegates to the real server model adapter
(`../../server/model.mjs`). Del's ruling (2026-10-28): **Spark stays
off until the build is complete and Del green-lights the test phase.
No live calls during the build.** While that holds, the adapter throws
the held refusal and every scenario in a run records it as its error.
When the test phase lands the Spark transport, this same function
returns real assessments and the same harness scores them — no adapter
change, no new wiring, and no fabricated assessment in between.

## The baseline, and the bar it sets

`node eval/ignis/run.mjs --baseline` runs the 20 labeled scenarios
against `assessBaseline` and measures, honestly, what a do-nothing
source scores. Measured 2026-10-28 (fixture numbers, not model
performance):

- Sample size: 20 scenarios
- Confusion (alert): TP=0 FP=0 TN=15 FN=5
- Precision: n/a (no alert ever predicted; denominator zero)
- Recall: 0.000, false-positive rate: 0.000, false-negative rate: 1.000
- Category accuracy: 0.150 (the 3 "no hazard visible" scenarios only)
- Errors: 0

A future real source must beat this baseline on recall and category
accuracy to claim value. Beating it on precision alone proves
nothing, since the baseline never fires a false alarm by
construction — the same bar the Sanitas set applies to its
always-clean baseline. The full measured run, including the
baseline-vs-held distinction, is documented in
`baseline-run-report.md`, completing the report trio alongside the
fixture and held-state reports.

## The stub, and the comparison it enables

`node eval/ignis/run.mjs --stub` runs the 20 labeled scenarios
against `assessStub` and then the baseline on the same set.
Measured 2026-10-28 (fixture numbers, not model performance):

- Stub: TP=4 FP=3 TN=12 FN=1, precision 0.571, recall 0.800,
  false-positive rate 0.200, false-negative rate 0.200,
  category accuracy 0.700, errors 0
- Baseline: TP=0 FP=0 TN=15 FN=5, precision n/a, recall 0.000,
  false-positive rate 0.000, false-negative rate 1.000,
  category accuracy 0.150, errors 0

Documented stub misses: IGN-003 predicted indeterminate (a missed
alert); IGN-007, IGN-010, IGN-018 predicted an alert category on a
confusable negative (false alarms); IGN-012 and IGN-015 predicted a
wrong non-alert category. The stub beats the baseline on recall
(0.800 vs 0.000) and category accuracy (0.700 vs 0.150) — the
comparison exercises the harness on a source that sometimes alerts
and sometimes misses, which the do-nothing baseline cannot do.
Neither number describes a model.

## The held-state run, and why it is not the baseline

`node eval/ignis/run.mjs` (no flag) runs the 20 labeled scenarios
against the real server model adapter. Measured 2026-10-28 (held
numbers, not model performance):

- Held: TP=0 FP=0 TN=15 FN=5, precision n/a, recall 0.000,
  false-positive rate 0.000, false-negative rate 1.000,
  category accuracy 0.000, errors 20 (every scenario, same refusal)

The confusion counts match the baseline's, but the runs are not
equivalent: the baseline predicts "no hazard visible" everywhere
(category accuracy 0.150, 0 errors), while the held run predicts
nothing (category accuracy 0.000, 20 errors). The held run proves
the default runner refuses honestly under the Spark hold instead
of fabricating assessments; it proves nothing about detection.

## Run it

```sh
node eval/ignis/run.mjs
node eval/ignis/run.mjs --baseline
node eval/ignis/run.mjs --stub
node eval/ignis/run.mjs --out eval/ignis/last-run.json
npm test   # runs the whole repo suite, including eval/ignis/adapter.test.mjs and report.test.mjs
```

## Reporting a run (the test-phase path, built now, no live call)

When Del green-lights the test phase, a live run is reported in two
steps, with no new wiring and no edit to the trio:

```sh
node eval/ignis/run.mjs --out eval/ignis/live-run.json
node eval/ignis/run.mjs --baseline --out eval/ignis/baseline-run.json
node eval/ignis/report.mjs eval/ignis/live-run.json \
  --baseline eval/ignis/baseline-run.json \
  --out eval/ignis/live-run-report.md
```

The renderer classifies by record evidence and refuses a trio
filename as `--out`, so the live numbers land in their own file
with the baseline verdict (recall and category accuracy, never
precision alone) attached. Until the test phase, the same command
on a held `--out` JSON renders a held-state report, not a live one
— the classification, not the filename, decides what a run is.

## What is unproven (do not claim otherwise)

- Live Spark: no live model call has been made by this lane; the
  held-state run records refusals, not assessments.
- Real-hardware camera: scenarios here are labeled descriptions run
  against the server adapter, not camera frames.
- Real imagery: no photographs are bundled; the scenario set describes
  scenes to be sourced as prerecorded footage or safe visual
  demonstrations before a live evaluation run. Never create a real
  fire to test this product.
