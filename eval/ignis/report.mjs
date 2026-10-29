// Meta Ignis run-report renderer (Rowan's lane).
//
// Turns a run JSON file produced by `node eval/ignis/run.mjs --out <path>`
// into the markdown report format used by the report trio
// (fixture-run-report.md, held-state-run-report.md,
// baseline-run-report.md). This file makes NO model call and reads NO
// key: it only renders numbers already measured by a run.
//
// Classification is by record evidence, not by the run's labels alone,
// because run.mjs labels predate the test phase and a stale label must
// never upgrade or downgrade a run:
//   1. every record errors with the held refusal -> "held-state"
//   2. source/generated names a fixture, baseline, or stub -> "fixture"
//   3. any record carries an actual category -> "live-model"
//   4. every record errors (some other way) -> "errored"
//   5. otherwise -> "unlabelled"
// Rule 3 is what lets a future live run render as live even if it was
// produced by an older run.mjs whose source string still says "held":
// assessments in the records beat a stale label. Rule 2 is what keeps
// a stub run a fixture even though it also carries assessments: a
// named fixture source is explicit, a stale held label is not.
//
// The renderer never rewrites the trio reports: --out to one of the
// trio filenames is refused, so a live run lands in its own file
// (live-run-report.md) and never edits a fixture/held/baseline record.
//
// Alert-level metrics hide which categories are confused: a run can
// look respectable while systematically swapping one category for
// another (the stub swaps steam/fog for smoke and flame-like lighting
// for flame). The report therefore also renders a truth-vs-predicted
// category table, and a confusable-negative breakdown counting the
// non-alert scenes (steam or fog, flame-like lighting) that were
// predicted as an alert category (visible smoke, visible flame).
// Errored records appear in the table under ERROR: they are failures,
// not confusions. Above the full table, a headline finding names the
// weakest truth category and the most-confused pair, so the single
// biggest failure mode is visible without reading the whole matrix.
// It also names the slowest scenario by harness wall-clock latency,
// so the run's latency tail is visible without scanning the
// per-scenario table; a run with no recorded latency says so instead
// of inventing one.
// A per-category rate table backs the headline: one correct/total
// rate per truth category, so the weakest claim is checkable without
// counting the confusion matrix. The Misses section names each miss
// as truth -> predicted, so a miss is diagnosable without
// cross-referencing the per-scenario table; unassessed records show
// ERROR, matching the confusion table's convention. A miss-pair
// counts table right after the Misses section aggregates those same
// misses by truth -> predicted pair, so the dominant swap is visible
// without counting the Misses list. A category-correct section after
// the miss-pair counts names the scenarios behind category accuracy,
// completing the category set the Misses section starts: the correct
// scenarios are the complement of the misses, so the two lists
// together account for every scenario in the run. The per-scenario table carries
// each record's harness wall-clock latency, so a slow scenario is
// visible without reading the summary statistics — and a record
// that carries no latency shows n/a rather than a fabricated zero.
// The same table flags latency outliers: a scenario whose latency
// is more than twice the median recorded latency for the run. A run
// with fewer than two recorded latencies, or a median recorded
// latency of zero, flags nothing — there is no typical latency to
// compare against, so no scenario is singled out on a zero baseline.
// A run's numbers are only ever compared against a baseline run the
// caller supplies; the bar is recall AND category accuracy, never
// precision alone (the baseline never fires a false alarm by
// construction, so its precision is vacuous, not perfect). The
// comparison renders signed deltas for both bar metrics, so the size
// of the margin is visible without subtracting the two lines above.
// An error-message breakdown splits the summary line's error total
// by exact message, so a run that fails in several different ways
// reads as a failure profile, not one lump — and a held-state run's
// single shared refusal reads as one row, not a list of ids.
// A latency distribution section expands the summary line's
// mean/median/max into min, quartiles and p90 over the recorded
// harness latencies, so the tail is visible without scanning the
// per-scenario table — and a run with no recorded latency says so
// instead of inventing one. A latency-outliers section right after
// the distribution names the scenarios the per-scenario table flags
// (latency more than twice the median recorded latency), with each
// outlier's latency, the run median, and the threshold, so the tail
// needs no scan of that table either. A latency-by-category section
// right after the outliers breaks the recorded latencies down by
// ground-truth category — count, mean, median, max — so a slow
// category is visible without scanning the per-scenario table; a
// category with no recorded latency shows n/a, never a fabricated
// zero. A latency-by-outcome section right after it breaks the
// recorded latencies down by outcome — correct, miss, unassessed —
// so a slow failure mode is visible without scanning the
// per-scenario table; all three rows always render, so the scenario
// totals sum to the sample size, and a group with no recorded
// latency shows n/a, never a fabricated zero. A latency-by-alert-
// outcome section right after it breaks the recorded latencies down
// by alert outcome — true positive, true negative, false positive,
// false negative — so a slow alert failure mode is visible without
// scanning the per-scenario table; all four rows always render, so
// the totals sum to the sample size, and a group with no recorded
// latency shows n/a, never a fabricated zero. A latency-by-alert-
// correctness section right after it collapses those four outcomes
// into two — alert correct (true positives plus true negatives)
// versus alert error (false positives plus false negatives) — so
// whether alert failures as a whole run slower than alert successes
// is visible without adding the four rows above; both rows always
// render, so the totals sum to the sample size, and a group with no
// recorded latency shows n/a, never a fabricated zero.
// An alert-errors section names the scenarios behind the summary
// line's FP/FN counts: false positives (an alert fired where none
// was expected) and false negatives (an expected alert that never
// fired), each with truth and predicted category. This is distinct
// from the category Misses: an alert error is about whether an
// alert fired at all, not which category was predicted — a missed
// alert on an unassessed record reads as ERROR, a failure, not a
// wrong category.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { basename, dirname } from "node:path";

export const PROTECTED_REPORT_NAMES = [
  "fixture-run-report.md",
  "held-state-run-report.md",
  "baseline-run-report.md",
];

const KIND_TITLES = {
  fixture: "fixture",
  "held-state": "held-state",
  "live-model": "live-model",
  errored: "errored",
  unlabelled: "unlabelled",
};

const KIND_INTRO = {
  fixture:
    "This is a FIXTURE run: the source is a local stand-in, not a model. " +
    "No number here describes model performance, and none may be quoted as such.",
  "held-state":
    "This is a HELD-STATE run: every scenario records the server adapter's " +
    "refusal, because live model calls are held. These numbers describe source " +
    "availability, not model performance: the run predicts nothing.",
  "live-model":
    "This is a LIVE-MODEL run: the source returned real assessments for these " +
    "scenarios. Its numbers describe this scenario set against the wired source " +
    "only — not real-hardware camera input, and not photographs, unless the run " +
    "itself was produced from real frames.",
  errored:
    "This run ERRORED on every scenario and produced no assessment. It cannot " +
    "be quoted as a model result, and its confusion counts describe the failure, " +
    "not detection.",
  unlabelled:
    "This run is UNLABELLED: it carries neither a named fixture source nor " +
    "assessments that would make it a live run. Do not quote it as a model " +
    "result until its source is identified.",
};

function isObject(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function isNumberOrNull(v) {
  return v === null || typeof v === "number";
}

export function validateRunJson(run) {
  const errors = [];
  if (!isObject(run)) return ["run is not an object"];
  if (!Array.isArray(run.records) || run.records.length === 0) {
    errors.push("records: missing or empty");
  } else {
    run.records.forEach((r, i) => {
      const prefix = `records[${i}]`;
      if (!isObject(r)) {
        errors.push(`${prefix}: not an object`);
        return;
      }
      if (typeof r.scenario_id !== "string" || r.scenario_id.length === 0) {
        errors.push(`${prefix}.scenario_id: missing or not a string`);
      }
      if (typeof r.ground_truth_label !== "string" || r.ground_truth_label.length === 0) {
        errors.push(`${prefix}.ground_truth_label: missing or not a string`);
      }
      if (typeof r.alert_expected !== "boolean") errors.push(`${prefix}.alert_expected: not a boolean`);
      if (typeof r.alert_fired !== "boolean") errors.push(`${prefix}.alert_fired: not a boolean`);
      if (typeof r.alert_correct !== "boolean") errors.push(`${prefix}.alert_correct: not a boolean`);
      if (typeof r.category_correct !== "boolean") errors.push(`${prefix}.category_correct: not a boolean`);
      if (!(typeof r.actual_category === "string" || r.actual_category === null)) {
        errors.push(`${prefix}.actual_category: neither a string nor null`);
      }
      if (!(typeof r.error === "string" || r.error === null)) {
        errors.push(`${prefix}.error: neither a string nor null`);
      }
      if ("latency_ms" in r && typeof r.latency_ms !== "number") {
        errors.push(`${prefix}.latency_ms: present but not a number`);
      }
    });
  }
  if (!isObject(run.metrics)) {
    errors.push("metrics: missing or not an object");
  } else {
    const m = run.metrics;
    for (const field of [
      "sample_size",
      "true_positives",
      "false_positives",
      "true_negatives",
      "false_negatives",
    ]) {
      if (typeof m[field] !== "number") errors.push(`metrics.${field}: missing or not a number`);
    }
    for (const field of ["recall", "false_positive_rate", "false_negative_rate", "category_accuracy"]) {
      if (!isNumberOrNull(m[field])) errors.push(`metrics.${field}: neither a number nor null`);
    }
    if (!isNumberOrNull(m.precision)) errors.push("metrics.precision: neither a number nor null");
    if (!isObject(m.latency_ms)) {
      errors.push("metrics.latency_ms: missing or not an object");
    } else {
      if (typeof m.latency_ms.n !== "number") errors.push("metrics.latency_ms.n: missing or not a number");
      for (const field of ["mean", "median", "max"]) {
        if (!isNumberOrNull(m.latency_ms[field])) errors.push(`metrics.latency_ms.${field}: neither a number nor null`);
      }
    }
    if (!isObject(m.errors) || typeof m.errors.count !== "number" || !Array.isArray(m.errors.scenario_ids)) {
      errors.push("metrics.errors: missing count or scenario_ids");
    }
    if (Array.isArray(run.records) && typeof m.sample_size === "number" && m.sample_size !== run.records.length) {
      errors.push(`metrics.sample_size ${m.sample_size} does not match ${run.records.length} records`);
    }
  }
  return errors;
}

export function classifyRunKind(run) {
  const records = Array.isArray(run.records) ? run.records : [];
  const labelText = `${run.source || ""} ${run.generated || ""}`;
  const allHeld =
    records.length > 0 &&
    records.every((r) => typeof r.error === "string" && /Live model calls are held/.test(r.error));
  if (allHeld) return "held-state";
  if (/fixture|baseline|stub/i.test(labelText)) return "fixture";
  if (records.some((r) => r.actual_category !== null)) return "live-model";
  if (records.length > 0 && records.every((r) => r.error !== null)) return "errored";
  return "unlabelled";
}

// The headline finding names the single biggest failure mode before
// the full table, so a reader need not read the whole matrix: the
// truth category with the lowest category-correct rate, and the
// most-confused truth -> predicted pair. Rates are correct / total
// for the truth category, matching category-accuracy semantics —
// errored records count as misses, not as excused. A truth category
// is only ranked when at least one of its scenarios was assessed;
// when nothing in the run was assessed at all there is no weakest
// category to name, and the headline says so instead of inventing
// one. The most-confused pair counts only real predicted categories:
// ERROR is a failure, not a confusion, so a run whose misses are all
// errors has no most-confused pair. Ties break deterministically —
// weakest by most misses then truth name, pair by truth then
// predicted name — so the headline never depends on record order.
export function computeCategoryHeadline(records) {
  const perCategory = {};
  for (const r of records) {
    perCategory[r.ground_truth_label] ??= { truth: r.ground_truth_label, total: 0, correct: 0, assessed: 0 };
    const entry = perCategory[r.ground_truth_label];
    entry.total += 1;
    if (r.actual_category !== null) entry.assessed += 1;
    if (r.actual_category === r.ground_truth_label) entry.correct += 1;
  }
  const ranked = Object.values(perCategory)
    .filter((e) => e.assessed > 0)
    .map((e) => ({ ...e, rate: e.total === 0 ? 0 : e.correct / e.total }))
    .sort((a, b) => {
      if (a.rate !== b.rate) return a.rate - b.rate;
      const missesA = a.total - a.correct;
      const missesB = b.total - b.correct;
      if (missesA !== missesB) return missesB - missesA;
      return a.truth < b.truth ? -1 : a.truth > b.truth ? 1 : 0;
    });
  const weakest = ranked.length > 0 ? ranked[0] : null;
  const pairCounts = {};
  for (const r of records) {
    if (r.actual_category === null || r.actual_category === r.ground_truth_label) continue;
    pairCounts[r.ground_truth_label] ??= {};
    pairCounts[r.ground_truth_label][r.actual_category] ??= [];
    pairCounts[r.ground_truth_label][r.actual_category].push(r.scenario_id);
  }
  const pairs = [];
  for (const truth of Object.keys(pairCounts).sort()) {
    for (const predicted of Object.keys(pairCounts[truth]).sort()) {
      pairs.push({ truth, predicted, count: pairCounts[truth][predicted].length, scenarioIds: pairCounts[truth][predicted] });
    }
  }
  pairs.sort((a, b) => {
    if (a.count !== b.count) return b.count - a.count;
    if (a.truth !== b.truth) return a.truth < b.truth ? -1 : 1;
    return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
  });
  return { weakest, mostConfused: pairs.length > 0 ? pairs[0] : null, perCategory: ranked };
}

// The slowest scenario by harness wall-clock latency: the record
// carrying the largest numeric latency_ms. Records with no latency
// are ignored, never treated as zero; when no record carries one
// there is no slowest scenario to name and the result is null, so
// the render says so instead of inventing a value. Ties break by
// scenario id alphabetically, so the result never depends on record
// order. This is harness wall clock, not a reported model field.
export function computeSlowestScenario(records) {
  let slowest = null;
  for (const r of records) {
    if (typeof r.latency_ms !== "number") continue;
    if (
      slowest === null ||
      r.latency_ms > slowest.latencyMs ||
      (r.latency_ms === slowest.latencyMs && r.scenario_id < slowest.scenarioId)
    ) {
      slowest = { scenarioId: r.scenario_id, truth: r.ground_truth_label, latencyMs: r.latency_ms };
    }
  }
  return slowest;
}

// The fastest scenario by harness wall-clock latency: the mirror of
// computeSlowestScenario — the record carrying the smallest numeric
// latency_ms. Records with no latency are ignored, never treated as
// zero; when no record carries one there is no fastest scenario to
// name and the result is null, so the render says so instead of
// inventing a value. Ties break by scenario id alphabetically, so
// the result never depends on record order. This is harness wall
// clock, not a reported model field.
export function computeFastestScenario(records) {
  let fastest = null;
  for (const r of records) {
    if (typeof r.latency_ms !== "number") continue;
    if (
      fastest === null ||
      r.latency_ms < fastest.latencyMs ||
      (r.latency_ms === fastest.latencyMs && r.scenario_id < fastest.scenarioId)
    ) {
      fastest = { scenarioId: r.scenario_id, truth: r.ground_truth_label, latencyMs: r.latency_ms };
    }
  }
  return fastest;
}

// One rate row per truth category present in the records, sorted
// alphabetically by truth name: correct predictions over all of that
// category's scenarios. The rate uses the headline's definition —
// correct / total, with records that produced no assessment counting
// as misses, matching category-accuracy semantics — so the headline's
// weakest category is the lowest row of this table (headline ties
// break by most misses, then truth name). The assessed count is
// carried alongside so a held-state row of 0.000 reads as "nothing
// assessed", not as a measured zero.
// Latency outliers: records whose harness wall-clock latency is
// strictly more than twice the median recorded latency for the run.
// Only records carrying a numeric latency take part, both in the
// median and in the flagging — a record with no latency is ignored,
// never treated as zero. The threshold is strict: a latency exactly
// twice the median is typical-scale, not an outlier. With fewer
// than two recorded latencies, or a median of zero, there is no
// typical latency to compare against, so nothing is flagged rather
// than flagging on a zero baseline. Results sort by scenario id, so
// the flag set never depends on record order. This is harness wall
// clock, not a reported model field.
export function computeLatencyOutliers(records) {
  const latencies = records
    .filter((r) => typeof r.latency_ms === "number")
    .map((r) => r.latency_ms)
    .sort((a, b) => a - b);
  if (latencies.length < 2) return [];
  const mid = Math.floor(latencies.length / 2);
  const median =
    latencies.length % 2 === 1 ? latencies[mid] : (latencies[mid - 1] + latencies[mid]) / 2;
  if (median <= 0) return [];
  const threshold = 2 * median;
  return records
    .filter((r) => typeof r.latency_ms === "number" && r.latency_ms > threshold)
    .map((r) => ({
      scenarioId: r.scenario_id,
      truth: r.ground_truth_label,
      latencyMs: r.latency_ms,
      medianMs: median,
      thresholdMs: threshold,
    }))
    .sort((a, b) => (a.scenarioId < b.scenarioId ? -1 : a.scenarioId > b.scenarioId ? 1 : 0));
}

// Latency distribution over the recorded harness wall-clock
// latencies: min, quartiles and p90, by linear interpolation on
// the sorted values. The p50 of this definition is the
// averaged-middle median, so it matches the summary line's median
// and the outlier threshold's median exactly. Records with no
// latency are ignored, never treated as zero; with no recorded
// latency there is no distribution and the result is null, so the
// render says so instead of inventing one.
export function computeLatencyDistribution(records) {
  const latencies = records
    .filter((r) => typeof r.latency_ms === "number")
    .map((r) => r.latency_ms)
    .sort((a, b) => a - b);
  if (latencies.length === 0) return null;
  const quantile = (p) => {
    const pos = p * (latencies.length - 1);
    const lo = Math.floor(pos);
    const hi = Math.ceil(pos);
    return latencies[lo] + (pos - lo) * (latencies[hi] - latencies[lo]);
  };
  return {
    count: latencies.length,
    minMs: latencies[0],
    p25Ms: quantile(0.25),
    medianMs: quantile(0.5),
    p75Ms: quantile(0.75),
    p90Ms: quantile(0.9),
    maxMs: latencies[latencies.length - 1],
  };
}

// Latency distribution among the misses only: the same min,
// quartiles and p90 as computeLatencyDistribution, but over the
// recorded harness wall-clock latencies of the misses alone (same
// miss definition as computeMisses: category_correct false, so an
// unassessed record counts as a miss here too). The full-run
// distribution answers how slow the run was; this one answers how
// slow its failures were, without the correct records pulling the
// quantiles down. Records with no latency are ignored, never
// treated as zero; with no recorded miss latency there is no
// distribution and the result is null, so the render says so
// instead of inventing one — and a run with no misses at all says
// none, which the render distinguishes by counting the misses.
export function computeMissLatencyDistribution(records) {
  return computeLatencyDistribution(records.filter((r) => !r.category_correct));
}

// Latency outliers among the misses only: the same strict
// more-than-twice-the-median rule as computeLatencyOutliers, but
// over the recorded harness wall-clock latencies of the misses
// alone (same miss definition as computeMisses: category_correct
// false, so an unassessed record counts as a miss here too, but
// carries no latency and never enters the median or the
// flagging). The full-run outliers answer which scenarios ran
// slow for the run; this one answers which failures ran slow for
// the failures, judged against the failures' own typical latency
// — a correct record's fast or slow latency never moves the
// misses' median or threshold. With fewer than two recorded miss
// latencies, or a median miss latency of zero, nothing is
// flagged, exactly as the full-run rule.
export function computeMissLatencyOutliers(records) {
  return computeLatencyOutliers(records.filter((r) => !r.category_correct));
}

// Slowest miss: the slowest scenario among the misses only, by the
// same rule as computeSlowestScenario — largest numeric latency_ms,
// ties alphabetical by scenario id, records with no latency ignored,
// null when no miss carries one — but over the misses alone (same
// miss definition as computeMisses: category_correct false, so an
// unassessed record counts as a miss here too, but carries no latency
// and can never be named). The full-run slowest answers which
// scenario ran slowest overall; this one answers which failure ran
// slowest, without a correct record's slow latency hiding it.
export function computeSlowestMiss(records) {
  return computeSlowestScenario(records.filter((r) => !r.category_correct));
}

// Fastest miss: the fastest scenario among the misses only, by the
// same rule as computeFastestScenario — smallest numeric latency_ms,
// ties alphabetical by scenario id, records with no latency ignored,
// null when no miss carries one — but over the misses alone (same
// miss definition as computeMisses: category_correct false, so an
// unassessed record counts as a miss here too, but carries no latency
// and can never be named). The slowest miss answers which failure
// dragged; this one answers which failure was quickest, so a fast
// failure is visible without a correct record's fast latency hiding
// it, and without scanning the per-scenario table.
export function computeFastestMiss(records) {
  return computeFastestScenario(records.filter((r) => !r.category_correct));
}

// Latency by ground-truth category: one row per truth category
// present in the records, sorted alphabetically, with the count of
// recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. Records with no latency take no part in a category's numbers
// but still count toward its scenario total, so a category whose
// scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero. A category with no
// recorded latency has null mean/median/max, so the render says n/a
// instead of inventing a value.
export function computeLatencyByCategory(records) {
  const byTruth = {};
  for (const r of records) {
    byTruth[r.ground_truth_label] ??= { truth: r.ground_truth_label, total: 0, latencies: [] };
    const entry = byTruth[r.ground_truth_label];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byTruth)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { truth: e.truth, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median =
        sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        truth: e.truth,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => (a.truth < b.truth ? -1 : a.truth > b.truth ? 1 : 0));
}

// Latency by outcome: one row per outcome group, in fixed order
// correct, miss, unassessed, with the count of recorded harness
// wall-clock latencies, their mean, their median (averaged-middle,
// matching the distribution's median), and their max. Correct means
// the predicted category matched the ground truth exactly; miss
// means an assessment was returned but differed; unassessed means
// no assessment was returned. All three rows always render, so the
// scenario totals sum to the sample size and a run with no misses
// (or no unassessed records) still shows that group explicitly.
// Records with no latency take no part in a group's numbers but
// still count toward its scenario total, so a group whose scenarios
// carry no latency reads as recorded 0 with n/a statistics — never
// as a fabricated zero.
export function computeLatencyByOutcome(records) {
  const groups = {
    correct: { outcome: "correct", total: 0, latencies: [] },
    miss: { outcome: "miss", total: 0, latencies: [] },
    unassessed: { outcome: "unassessed", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome =
      r.actual_category === null
        ? "unassessed"
        : r.actual_category === r.ground_truth_label
          ? "correct"
          : "miss";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["correct", "miss", "unassessed"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by alert outcome: one row per alert-outcome group, in
// fixed order true positive, true negative, false positive, false
// negative, with the count of recorded harness wall-clock latencies,
// their mean, their median (averaged-middle, matching the
// distribution's median), and their max. The split uses
// alert_expected / alert_fired only, matching the metrics
// definition, so the four scenario totals always sum to the sample
// size and a run with no alert errors still shows the error groups
// explicitly. Records with no latency take no part in a group's
// numbers but still count toward its scenario total, so a group
// whose scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero.
export function computeLatencyByAlertOutcome(records) {
  const groups = {
    "true positive": { outcome: "true positive", total: 0, latencies: [] },
    "true negative": { outcome: "true negative", total: 0, latencies: [] },
    "false positive": { outcome: "false positive", total: 0, latencies: [] },
    "false negative": { outcome: "false negative", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome =
      r.alert_expected && r.alert_fired
        ? "true positive"
        : !r.alert_expected && !r.alert_fired
          ? "true negative"
          : !r.alert_expected && r.alert_fired
            ? "false positive"
            : "false negative";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["true positive", "true negative", "false positive", "false negative"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by alert correctness: one row per alert-correctness
// group, in fixed order alert correct, alert error, with the count
// of recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. Alert correct collapses the alert-outcome split: a record is
// alert correct when the fired outcome matched expectation (true
// positives plus true negatives), and an alert error otherwise
// (false positives plus false negatives), using the validated
// alert_correct field, so the two scenario totals always sum to the
// sample size. Records with no latency take no part in a group's
// numbers but still count toward its scenario total, so a group
// whose scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero.
export function computeLatencyByAlertCorrectness(records) {
  const groups = {
    "alert correct": { outcome: "alert correct", total: 0, latencies: [] },
    "alert error": { outcome: "alert error", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = r.alert_correct ? "alert correct" : "alert error";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["alert correct", "alert error"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by alert expectation: one row per alert-expectation
// group, in fixed order alert expected, alert not expected, with
// the count of recorded harness wall-clock latencies, their mean,
// their median (averaged-middle, matching the distribution's
// median), and their max. Alert expected collapses the
// alert-outcome split the other way from alert correctness: a
// record is alert expected when an alert was expected at all (true
// positives plus false negatives), and alert not expected otherwise
// (true negatives plus false positives), using the validated
// alert_expected field, so the two scenario totals always sum to
// the sample size. Records with no latency take no part in a
// group's numbers but still count toward its scenario total, so a
// group whose scenarios carry no latency reads as recorded 0 with
// n/a statistics — never as a fabricated zero.
export function computeLatencyByAlertExpectation(records) {
  const groups = {
    "alert expected": { outcome: "alert expected", total: 0, latencies: [] },
    "alert not expected": { outcome: "alert not expected", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = r.alert_expected ? "alert expected" : "alert not expected";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["alert expected", "alert not expected"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by alert fired: one row per alert-fired
// group, in fixed order alert fired, alert not fired, with
// the count of recorded harness wall-clock latencies, their mean,
// their median (averaged-middle, matching the distribution's
// median), and their max. Alert fired collapses the
// alert-outcome split by column, completing the three two-way
// collapses with alert correctness (diagonal) and alert
// expectation (row): a record is alert fired when an alert fired
// at all (true positives plus false positives), and alert not
// fired otherwise (true negatives plus false negatives), using
// the validated alert_fired field, so the two scenario totals
// always sum to the sample size. Records with no latency take
// no part in a group's numbers but still count toward its
// scenario total, so a group whose scenarios carry no latency
// reads as recorded 0 with n/a statistics — never as a
// fabricated zero.
export function computeLatencyByAlertFired(records) {
  const groups = {
    "alert fired": { outcome: "alert fired", total: 0, latencies: [] },
    "alert not fired": { outcome: "alert not fired", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = r.alert_fired ? "alert fired" : "alert not fired";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["alert fired", "alert not fired"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by assessed: one row per assessed-status
// group, in fixed order assessed, unassessed, with
// the count of recorded harness wall-clock latencies, their mean,
// their median (averaged-middle, matching the distribution's
// median), and their max. Assessed collapses the outcome split:
// a record is assessed when an assessment was returned at all
// (correct plus miss), and unassessed otherwise (no assessment
// returned), using the validated actual_category field, so the
// two scenario totals always sum to the sample size. Records
// with no latency take no part in a group's numbers but still
// count toward its scenario total, so a group whose scenarios
// carry no latency reads as recorded 0 with n/a statistics —
// never as a fabricated zero.
export function computeLatencyByAssessed(records) {
  const groups = {
    assessed: { outcome: "assessed", total: 0, latencies: [] },
    unassessed: { outcome: "unassessed", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = r.actual_category === null ? "unassessed" : "assessed";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["assessed", "unassessed"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by category correctness: one row per category-correctness
// group, in fixed order category correct, category incorrect, with
// the count of recorded harness wall-clock latencies, their mean,
// their median (averaged-middle, matching the distribution's
// median), and their max. Category correctness collapses the
// outcome split the other way from assessed: a record is category
// correct when the predicted category matched the ground truth
// exactly, and category incorrect otherwise (a miss plus every
// unassessed record), using the validated category_correct field,
// so the two scenario totals always sum to the sample size.
// Records with no latency take no part in a group's numbers but
// still count toward its scenario total, so a group whose scenarios
// carry no latency reads as recorded 0 with n/a statistics —
// never as a fabricated zero.
export function computeLatencyByCategoryCorrectness(records) {
  const groups = {
    "category correct": { outcome: "category correct", total: 0, latencies: [] },
    "category incorrect": { outcome: "category incorrect", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = r.category_correct ? "category correct" : "category incorrect";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["category correct", "category incorrect"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by miss status: one row per miss-status
// group, in fixed order miss, non-miss, with the count of recorded
// harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. Miss status collapses the outcome split the third way,
// completing the set with assessed and category correctness: a
// record is a miss when an assessment was returned but differed
// from the ground truth, and non-miss otherwise (the exact match
// plus every unassessed record), using the validated
// actual_category field against the ground truth, so the two
// scenario totals always sum to the sample size. Records with no
// latency take no part in a group's numbers but still count toward
// its scenario total, so a group whose scenarios carry no latency
// reads as recorded 0 with n/a statistics — never as a fabricated
// zero.
export function computeLatencyByMissStatus(records) {
  const groups = {
    miss: { outcome: "miss", total: 0, latencies: [] },
    "non-miss": { outcome: "non-miss", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome =
      r.actual_category !== null && r.actual_category !== r.ground_truth_label
        ? "miss"
        : "non-miss";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["miss", "non-miss"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by predicted category: one row per predicted category
// present in the records, sorted alphabetically with ERROR last
// (matching the confusion table's ordering), with the count of
// recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. This is the predicted-side mirror of latency by category:
// a record's predicted category is its actual_category, or ERROR
// when no assessment was returned, using the same convention as
// the confusion table, so the scenario totals sum to the sample
// size. Records with no latency take no part in a category's
// numbers but still count toward its scenario total, so a category
// whose scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero.
export function computeLatencyByPredictedCategory(records) {
  const byPredicted = {};
  for (const r of records) {
    const predicted = r.actual_category === null ? ERROR_PREDICTED : r.actual_category;
    byPredicted[predicted] ??= { predicted, total: 0, latencies: [] };
    const entry = byPredicted[predicted];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byPredicted)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { predicted: e.predicted, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median =
        sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        predicted: e.predicted,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.predicted === ERROR_PREDICTED) return 1;
      if (b.predicted === ERROR_PREDICTED) return -1;
      return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
    });
}

// Latency by error status: one row per error-status
// group, in fixed order errored, no error, with the count of
// recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. A record is errored when it carries an error message at
// all, using the validated error field — the same definition the
// error-message breakdown groups by, so a record that carries both
// an assessment and an error message still counts as errored —
// and no error otherwise, so the two scenario totals always sum
// to the sample size. Records with no latency take no part in a
// group's numbers but still count toward its scenario total, so
// a group whose scenarios carry no latency reads as recorded 0
// with n/a statistics — never as a fabricated zero.
export function computeLatencyByErrorStatus(records) {
  const groups = {
    errored: { outcome: "errored", total: 0, latencies: [] },
    "no error": { outcome: "no error", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = r.error !== null ? "errored" : "no error";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["errored", "no error"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by error message: one row per distinct error message,
// in the same grouping the error-message breakdown uses — most
// frequent first, ties alphabetical — with the count of recorded
// harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and
// their max. Only records carrying an error message appear, so
// the scenario totals sum to the error count, not the sample
// size — the no-error records are already covered by the
// latency-by-error-status section this one refines. Records with
// no latency take no part in a message's numbers but still count
// toward its scenario total, so a message whose scenarios carry
// no latency reads as recorded 0 with n/a statistics — never as
// a fabricated zero.
export function computeLatencyByErrorMessage(records) {
  const byMessage = {};
  for (const r of records) {
    if (r.error === null) continue;
    byMessage[r.error] ??= { message: r.error, total: 0, latencies: [] };
    const entry = byMessage[r.error];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byMessage)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { message: e.message, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        message: e.message,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.total !== b.total) return b.total - a.total;
      return a.message < b.message ? -1 : a.message > b.message ? 1 : 0;
    });
}

// Latency by truth -> predicted pair: one row per pair present in
// the records, sorted by truth alphabetically then predicted
// alphabetically with ERROR last (matching the confusion table's
// ordering), with the count of recorded harness wall-clock
// latencies, their mean, their median (averaged-middle, matching
// the distribution's median), and their max. This is the joint
// breakdown the two one-sided breakdowns imply: latency by
// category (truth alone) and latency by predicted category
// (predicted alone) cannot say whether one particular swap runs
// slower than another, and this table can — including the diagonal
// correct pairs, so the scenario totals sum to the sample size.
// An unassessed record reads as ERROR, matching the confusion
// table's convention. Records with no latency take no part in a
// pair's numbers but still count toward its scenario total, so a
// pair whose scenarios carry no latency reads as recorded 0 with
// n/a statistics — never as a fabricated zero.
export function computeLatencyByTruthPredictedPair(records) {
  const byPair = {};
  for (const r of records) {
    const predicted = r.actual_category === null ? ERROR_PREDICTED : r.actual_category;
    const key = `${r.ground_truth_label}\0${predicted}`;
    byPair[key] ??= { truth: r.ground_truth_label, predicted, total: 0, latencies: [] };
    const entry = byPair[key];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byPair)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { truth: e.truth, predicted: e.predicted, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        truth: e.truth,
        predicted: e.predicted,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.truth !== b.truth) return a.truth < b.truth ? -1 : 1;
      if (a.predicted === ERROR_PREDICTED) return 1;
      if (b.predicted === ERROR_PREDICTED) return -1;
      return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
    });
}

// Latency by confusable-negative status: one row per status group,
// in fixed order confusable negative, other non-alert, alert, with
// the count of recorded harness wall-clock latencies, their mean,
// their median (averaged-middle, matching the distribution's
// median), and their max. A record is a confusable negative when
// its ground truth is one of the confusable-negative categories
// (steam or fog, flame-like lighting — the same list the
// confusable-negatives breakdown counts), an alert when its ground
// truth is an alert category (visible smoke, visible flame), and
// other non-alert otherwise (no hazard visible, indeterminate,
// obscured or distant hazard, or any truth outside both lists —
// non-alert by the alert list's definition, so the three scenario
// totals always sum to the sample size). This is the latency side
// of the confusable-negatives question: latency by category can
// say steam runs slow, but only this split says whether the
// false-alarm-prone scenes as a class run slower than the scenes
// that should never fire. Records with no latency take no part in
// a group's numbers but still count toward its scenario total, so
// a group whose scenarios carry no latency reads as recorded 0
// with n/a statistics — never as a fabricated zero.
export function computeLatencyByConfusableStatus(records) {
  const groups = {
    "confusable negative": { outcome: "confusable negative", total: 0, latencies: [] },
    "other non-alert": { outcome: "other non-alert", total: 0, latencies: [] },
    alert: { outcome: "alert", total: 0, latencies: [] },
  };
  for (const r of records) {
    const outcome = CONFUSABLE_NEGATIVE_CATEGORIES.includes(r.ground_truth_label)
      ? "confusable negative"
      : IGNIS_ALERT_CATEGORIES.includes(r.ground_truth_label)
        ? "alert"
        : "other non-alert";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["confusable negative", "other non-alert", "alert"].map((outcome) => {
    const e = groups[outcome];
    const sorted = e.latencies.sort((a, b) => a - b);
    if (sorted.length === 0) {
      return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
    }
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    return {
      outcome,
      total: e.total,
      recorded: sorted.length,
      meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
      medianMs: median,
      maxMs: sorted[sorted.length - 1],
    };
  });
}

// Latency by miss pair: one row per truth -> predicted pair among
// the misses only (same miss definition as computeMisses:
// category_correct false; an unassessed record reads as ERROR,
// matching the confusion table's convention), sorted most
// frequent first, then truth alphabetically, then predicted
// alphabetically with ERROR last (matching the miss-pair counts'
// ordering), with the count of recorded harness wall-clock
// latencies, their mean, their median (averaged-middle, matching
// the distribution's median), and their max. This is the latency
// side of the dominant-swap question: the miss-pair counts say
// which swap happens most, but only this table says whether that
// swap also runs slower than the others — and latency by truth ->
// predicted pair, which includes the diagonal correct pairs,
// cannot isolate the misses. The scenario totals sum to the miss
// count, not the sample size. Records with no latency take no
// part in a pair's numbers but still count toward its scenario
// total, so a pair whose scenarios carry no latency reads as
// recorded 0 with n/a statistics — never as a fabricated zero.
export function computeLatencyByMissPair(records) {
  const byPair = {};
  for (const r of records) {
    if (r.category_correct) continue;
    const predicted = r.actual_category === null ? ERROR_PREDICTED : r.actual_category;
    const key = `${r.ground_truth_label}\0${predicted}`;
    byPair[key] ??= { truth: r.ground_truth_label, predicted, total: 0, latencies: [] };
    const entry = byPair[key];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byPair)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { truth: e.truth, predicted: e.predicted, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        truth: e.truth,
        predicted: e.predicted,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.total !== b.total) return b.total - a.total;
      if (a.truth !== b.truth) return a.truth < b.truth ? -1 : 1;
      if (a.predicted === ERROR_PREDICTED) return 1;
      if (b.predicted === ERROR_PREDICTED) return -1;
      return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
    });
}

// Latency by miss truth category: one row per ground-truth category
// among the misses only (same miss definition as computeMisses:
// category_correct false), sorted most frequent first, then truth
// alphabetically, with the count of recorded harness wall-clock
// latencies, their mean, their median (averaged-middle, matching
// the distribution's median), and their max. This is the coarser
// misses-only marginal behind the miss-pair table: the pair table
// says which swap runs slowest, but only this table says whether
// one truth category's misses as a class run slower than another's
// — and latency by category, which includes the correct pairs,
// cannot isolate the misses. The scenario totals sum to the miss
// count, not the sample size. Records with no latency take no
// part in a category's numbers but still count toward its scenario
// total, so a category whose scenarios carry no latency reads as
// recorded 0 with n/a statistics — never as a fabricated zero.
export function computeLatencyByMissTruth(records) {
  const byTruth = {};
  for (const r of records) {
    if (r.category_correct) continue;
    const entry = (byTruth[r.ground_truth_label] ??= {
      truth: r.ground_truth_label,
      total: 0,
      latencies: [],
    });
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byTruth)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { truth: e.truth, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        truth: e.truth,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.total !== b.total) return b.total - a.total;
      return a.truth < b.truth ? -1 : a.truth > b.truth ? 1 : 0;
    });
}

// Latency by miss predicted category: one row per predicted category
// among the misses only (same miss definition as computeMisses:
// category_correct false; an unassessed record reads as ERROR,
// matching the confusion table's convention), sorted most
// frequent first, then predicted alphabetically with ERROR last
// (matching the miss-pair counts' ordering), with the count of
// recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and
// their max. This is the predicted-side misses-only marginal
// behind the miss-pair table: the pair table says which swap runs
// slowest, but only this table says whether one predicted
// category's misses as a class run slower than another's — and
// latency by predicted category, which includes the correct
// pairs, cannot isolate the misses. The scenario totals sum to
// the miss count, not the sample size. Records with no latency
// take no part in a category's numbers but still count toward
// its scenario total, so a category whose scenarios carry no
// latency reads as recorded 0 with n/a statistics — never as a
// fabricated zero.
export function computeLatencyByMissPredicted(records) {
  const byPredicted = {};
  for (const r of records) {
    if (r.category_correct) continue;
    const predicted = r.actual_category === null ? ERROR_PREDICTED : r.actual_category;
    const entry = (byPredicted[predicted] ??= {
      predicted,
      total: 0,
      latencies: [],
    });
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byPredicted)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { predicted: e.predicted, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        predicted: e.predicted,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.total !== b.total) return b.total - a.total;
      if (a.predicted === ERROR_PREDICTED) return 1;
      if (b.predicted === ERROR_PREDICTED) return -1;
      return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
    });
}

// Latency by miss error status: one row per error-status group
// among the misses only (same miss definition as computeMisses:
// category_correct false), in fixed order errored, no error
// (same definition as computeLatencyByErrorStatus: a record is
// errored when it carries an error message at all), with the count
// of recorded harness wall-clock latencies, their mean, their
// median (averaged-middle, matching the distribution's median),
// and their max. This is the failure-vs-confusion split of the
// misses: the miss-pair table says which swap runs slowest, but
// only this table says whether the misses that failed outright
// run slower than the misses that returned a wrong category —
// and latency by error status, which includes the correct
// records, cannot isolate the misses. Only groups present among
// the misses render, so the scenario totals sum to the miss
// count, not the sample size. Records with no latency take no
// part in a group's numbers but still count toward its scenario
// total, so a group whose scenarios carry no latency reads as
// recorded 0 with n/a statistics — never as a fabricated zero.
export function computeLatencyByMissErrorStatus(records) {
  const groups = {
    errored: { outcome: "errored", total: 0, latencies: [] },
    "no error": { outcome: "no error", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = r.error !== null ? "errored" : "no error";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["errored", "no error"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss error message: one row per distinct error message
// among the misses only (same miss definition as computeMisses:
// category_correct false), in the same grouping the error-message
// breakdown uses — most frequent first, ties alphabetical — with
// the count of recorded harness wall-clock latencies, their mean,
// their median (averaged-middle, matching the distribution's
// median), and their max. This is the per-message refinement of
// latency by miss error status: the error-status split says the
// misses that failed outright run slower or faster than the misses
// that returned a wrong category, but only this table says whether
// one failure mode runs slower than another — and latency by error
// message, which includes the correct records, cannot isolate the
// misses. Only misses carrying an error message appear, so the
// scenario totals sum to the errored-miss count, not the miss
// count and not the sample size. Records with no latency take no
// part in a message's numbers but still count toward its scenario
// total, so a message whose scenarios carry no latency reads as
// recorded 0 with n/a statistics — never as a fabricated zero.
export function computeLatencyByMissErrorMessage(records) {
  const byMessage = {};
  for (const r of records) {
    if (r.category_correct) continue;
    if (r.error === null) continue;
    byMessage[r.error] ??= { message: r.error, total: 0, latencies: [] };
    const entry = byMessage[r.error];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return Object.values(byMessage)
    .map((e) => {
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { message: e.message, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        message: e.message,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    })
    .sort((a, b) => {
      if (a.total !== b.total) return b.total - a.total;
      return a.message < b.message ? -1 : a.message > b.message ? 1 : 0;
    });
}

// Latency by miss alert outcome: one row per alert-outcome group
// among the misses only (same miss definition as computeMisses:
// category_correct false), in the same fixed order the
// latency-by-alert-outcome section uses — true positive, true
// negative, false positive, false negative — derived from
// alert_expected / alert_fired only, with the count of recorded
// harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and
// their max. This is the alert-side split of the misses: the
// error-status split says whether the misses that failed outright
// run slower than the misses that returned a wrong category, but
// only this table says whether the misses that fired an alert run
// slower than the misses that stayed silent — and latency by
// alert outcome, which includes the correct records, cannot
// isolate the misses. Only groups present among the misses
// render, so the scenario totals sum to the miss count, not the
// sample size. Records with no latency take no part in a group's
// numbers but still count toward its scenario total, so a group
// whose scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero.
export function computeLatencyByMissAlertOutcome(records) {
  const groups = {
    "true positive": { outcome: "true positive", total: 0, latencies: [] },
    "true negative": { outcome: "true negative", total: 0, latencies: [] },
    "false positive": { outcome: "false positive", total: 0, latencies: [] },
    "false negative": { outcome: "false negative", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome =
      r.alert_expected && r.alert_fired
        ? "true positive"
        : !r.alert_expected && !r.alert_fired
          ? "true negative"
          : !r.alert_expected && r.alert_fired
            ? "false positive"
            : "false negative";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["true positive", "true negative", "false positive", "false negative"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss alert correctness: one row per alert-correctness
// group among the misses only (same miss definition as computeMisses:
// category_correct false), in the same fixed order the
// latency-by-alert-correctness section uses — alert correct, alert
// error — derived from the validated alert_correct field, with the
// count of recorded harness wall-clock latencies, their mean, their
// median (averaged-middle, matching the distribution's median), and
// their max. This is the collapsed alert-side split of the misses:
// the alert-outcome split says whether the misses that fired an
// alert run slower than the misses that stayed silent, but only this
// table says whether the misses whose alert was right run slower
// than the misses whose alert was wrong — and latency by alert
// correctness, which includes the correct records, cannot isolate
// the misses. Only groups present among the misses render, so the
// scenario totals sum to the miss count, not the sample size.
// Records with no latency take no part in a group's numbers but
// still count toward its scenario total, so a group whose scenarios
// carry no latency reads as recorded 0 with n/a statistics — never
// as a fabricated zero.
export function computeLatencyByMissAlertCorrectness(records) {
  const groups = {
    "alert correct": { outcome: "alert correct", total: 0, latencies: [] },
    "alert error": { outcome: "alert error", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = r.alert_correct ? "alert correct" : "alert error";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["alert correct", "alert error"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss alert expectation: one row per alert-expectation
// group among the misses only (same miss definition as computeMisses:
// category_correct false), in the same fixed order the
// latency-by-alert-expectation section uses — alert expected, alert
// not expected — derived from the validated alert_expected field, with
// the count of recorded harness wall-clock latencies, their mean, their
// median (averaged-middle, matching the distribution's median), and
// their max. This is the row collapse of the misses' alert split: the
// alert-outcome split says whether the misses that fired an alert run
// slower than the misses that stayed silent, but only this table says
// whether the misses where an alert was expected run slower than the
// misses where none was — and latency by alert expectation, which
// includes the correct records, cannot isolate the misses. Only groups
// present among the misses render, so the scenario totals sum to the
// miss count, not the sample size. Records with no latency take no part
// in a group's numbers but still count toward its scenario total, so a
// group whose scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero.
export function computeLatencyByMissAlertExpectation(records) {
  const groups = {
    "alert expected": { outcome: "alert expected", total: 0, latencies: [] },
    "alert not expected": { outcome: "alert not expected", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = r.alert_expected ? "alert expected" : "alert not expected";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["alert expected", "alert not expected"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss alert fired: one row per alert-fired
// group among the misses only (same miss definition as computeMisses:
// category_correct false), in the same fixed order the
// latency-by-alert-fired section uses — alert fired, alert
// not fired — derived from the validated alert_fired field, with
// the count of recorded harness wall-clock latencies, their mean, their
// median (averaged-middle, matching the distribution's median), and
// their max. This is the column collapse of the misses' alert split: the
// alert-outcome split says whether the misses that fired an alert run
// slower than the misses that stayed silent only through four rows, but
// only this table says so in two — fired (true positives plus false
// positives) versus not fired (true negatives plus false negatives) —
// and latency by alert fired, which includes the correct records,
// cannot isolate the misses. Only groups present among the misses
// render, so the scenario totals sum to the miss count, not the sample
// size. Records with no latency take no part in a group's numbers but
// still count toward its scenario total, so a group whose scenarios
// carry no latency reads as recorded 0 with n/a statistics — never as
// a fabricated zero.
export function computeLatencyByMissAlertFired(records) {
  const groups = {
    "alert fired": { outcome: "alert fired", total: 0, latencies: [] },
    "alert not fired": { outcome: "alert not fired", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = r.alert_fired ? "alert fired" : "alert not fired";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["alert fired", "alert not fired"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss assessed: one row per assessed-status
// group among the misses only (same miss definition as computeMisses:
// category_correct false), in the same fixed order the
// latency-by-assessed section uses — assessed, unassessed — derived
// from the validated actual_category field, with the count of
// recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. This is the collapse of the misses' assessed split: the
// outcome split says whether the misses that returned an assessment
// run slower than the misses that returned none only through the
// assessed rows mixed with correct records, but only this table says
// so in two rows — assessed misses (a wrong category returned)
// versus unassessed misses (the ERROR rows of the Misses list, no
// assessment returned) — and latency by assessed, which includes the
// correct records, cannot isolate the misses. Only groups present
// among the misses render, so the scenario totals sum to the miss
// count, not the sample size. Records with no latency take no part
// in a group's numbers but still count toward its scenario total, so
// a group whose scenarios carry no latency reads as recorded 0 with
// n/a statistics — never as a fabricated zero.
export function computeLatencyByMissAssessed(records) {
  const groups = {
    assessed: { outcome: "assessed", total: 0, latencies: [] },
    unassessed: { outcome: "unassessed", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = r.actual_category === null ? "unassessed" : "assessed";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["assessed", "unassessed"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss outcome: one row per outcome group among the
// misses only (same miss definition as computeMisses:
// category_correct false), in the same fixed order the
// latency-by-outcome section uses minus the correct row, which
// cannot occur among the misses — miss, unassessed — derived
// from the validated actual_category field, with the count of
// recorded harness wall-clock latencies, their mean, their median
// (averaged-middle, matching the distribution's median), and their
// max. This is the outcome split of the misses: a miss is a wrong
// category returned, an unassessed miss is the ERROR row of the
// Misses list, no assessment returned — and latency by outcome,
// which includes the correct records, cannot isolate the misses.
// Only groups present among the misses render, so the scenario
// totals sum to the miss count, not the sample size. Records with
// no latency take no part in a group's numbers but still count
// toward its scenario total, so a group whose scenarios carry no
// latency reads as recorded 0 with n/a statistics — never as a
// fabricated zero.
export function computeLatencyByMissOutcome(records) {
  const groups = {
    miss: { outcome: "miss", total: 0, latencies: [] },
    unassessed: { outcome: "unassessed", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = r.actual_category === null ? "unassessed" : "miss";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["miss", "unassessed"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

// Latency by miss confusable-negative status: one row per
// confusable-negative-status group among the misses only (same miss
// definition as computeMisses: category_correct false), in the same
// fixed order the latency-by-confusable-negative-status section uses
// — confusable negative, other non-alert, alert — derived from the
// ground-truth label, with the count of recorded harness wall-clock
// latencies, their mean, their median (averaged-middle, matching the
// distribution's median), and their max. This is the
// false-alarm-prone split of the misses: a miss on a confusable
// negative (steam or fog, flame-like lighting) is the scene a source
// plausibly mistakes for an alert, and latency by
// confusable-negative status, which includes the correct records,
// cannot isolate the misses. Only groups present among the misses
// render, so the scenario totals sum to the miss count, not the
// sample size. Records with no latency take no part in a group's
// numbers but still count toward its scenario total, so a group
// whose scenarios carry no latency reads as recorded 0 with n/a
// statistics — never as a fabricated zero.
export function computeLatencyByMissConfusableStatus(records) {
  const groups = {
    "confusable negative": { outcome: "confusable negative", total: 0, latencies: [] },
    "other non-alert": { outcome: "other non-alert", total: 0, latencies: [] },
    alert: { outcome: "alert", total: 0, latencies: [] },
  };
  for (const r of records) {
    if (r.category_correct) continue;
    const outcome = CONFUSABLE_NEGATIVE_CATEGORIES.includes(r.ground_truth_label)
      ? "confusable negative"
      : IGNIS_ALERT_CATEGORIES.includes(r.ground_truth_label)
        ? "alert"
        : "other non-alert";
    const entry = groups[outcome];
    entry.total += 1;
    if (typeof r.latency_ms === "number") entry.latencies.push(r.latency_ms);
  }
  return ["confusable negative", "other non-alert", "alert"]
    .filter((outcome) => groups[outcome].total > 0)
    .map((outcome) => {
      const e = groups[outcome];
      const sorted = e.latencies.sort((a, b) => a - b);
      if (sorted.length === 0) {
        return { outcome, total: e.total, recorded: 0, meanMs: null, medianMs: null, maxMs: null };
      }
      const mid = Math.floor(sorted.length / 2);
      const median = sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
      return {
        outcome,
        total: e.total,
        recorded: sorted.length,
        meanMs: sorted.reduce((n, v) => n + v, 0) / sorted.length,
        medianMs: median,
        maxMs: sorted[sorted.length - 1],
      };
    });
}

export function computeCategoryRates(records) {
  const perCategory = {};
  for (const r of records) {
    perCategory[r.ground_truth_label] ??= { truth: r.ground_truth_label, total: 0, correct: 0, assessed: 0 };
    const entry = perCategory[r.ground_truth_label];
    entry.total += 1;
    if (r.actual_category !== null) entry.assessed += 1;
    if (r.actual_category === r.ground_truth_label) entry.correct += 1;
  }
  return Object.values(perCategory)
    .map((e) => ({ ...e, rate: e.total === 0 ? 0 : e.correct / e.total }))
    .sort((a, b) => (a.truth < b.truth ? -1 : a.truth > b.truth ? 1 : 0));
}

// Alert categories for the Ignis product (from scenarios.json and
// adapter.mjs: only visible smoke and visible flame fire an alert).
// Confusable negatives are the non-alert categories a source most
// plausibly mistakes for an alert: steam or fog for smoke, flame-like
// lighting for flame.
export const IGNIS_ALERT_CATEGORIES = ["visible smoke", "visible flame"];
export const CONFUSABLE_NEGATIVE_CATEGORIES = ["steam or fog", "flame-like lighting"];
const ERROR_PREDICTED = "ERROR";

// One entry per category miss, in record order: the scenario id with
// the truth category and the predicted category, so a miss is
// diagnosable without cross-referencing the per-scenario table.
// Records that produced no assessment show ERROR, matching the
// confusion table's convention — a failure, not a wrong category.
// The filter is category_correct, the same definition the old bare
// id list used, so the section's count does not change — only the
// detail per miss does.
export function computeMisses(records) {
  return records
    .filter((r) => !r.category_correct)
    .map((r) => ({
      scenarioId: r.scenario_id,
      truth: r.ground_truth_label,
      predicted: r.actual_category === null ? ERROR_PREDICTED : r.actual_category,
    }));
}

// Miss-pair counts: the Misses list aggregated by truth -> predicted
// pair, so the dominant swap is visible without counting that list.
// Same miss definition as computeMisses (category_correct false),
// same ERROR convention for unassessed records — a held run's pairs
// are all ERROR, which reads as a failure profile, not confusions.
// Sorting is count descending, then truth alphabetically, then
// predicted alphabetically with ERROR last (matching the confusion
// table's convention), so the table never depends on record order.
export function computeMissPairs(records) {
  const counts = {};
  for (const m of computeMisses(records)) {
    counts[m.truth] ??= {};
    counts[m.truth][m.predicted] ??= [];
    counts[m.truth][m.predicted].push(m.scenarioId);
  }
  const pairs = [];
  for (const truth of Object.keys(counts).sort()) {
    for (const predicted of Object.keys(counts[truth]).sort((a, b) => {
      if (a === ERROR_PREDICTED) return 1;
      if (b === ERROR_PREDICTED) return -1;
      return a < b ? -1 : a > b ? 1 : 0;
    })) {
      pairs.push({ truth, predicted, count: counts[truth][predicted].length, scenarioIds: counts[truth][predicted] });
    }
  }
  pairs.sort((a, b) => {
    if (a.count !== b.count) return b.count - a.count;
    if (a.truth !== b.truth) return a.truth < b.truth ? -1 : 1;
    if (a.predicted === ERROR_PREDICTED) return 1;
    if (b.predicted === ERROR_PREDICTED) return -1;
    return a.predicted < b.predicted ? -1 : a.predicted > b.predicted ? 1 : 0;
  });
  return pairs;
}

// Category-level correct outcomes: the scenarios behind category
// accuracy, completing the set computeMisses starts. A correct
// scenario predicted the exact ground-truth category; the filter is
// category_correct, the same definition the Misses section negates,
// so the correct list and the Misses list together account for every
// record in the run, with no scenario in both and none in neither.
// Predicted is the actual category (never ERROR for a genuine
// correct record, since a correct prediction is an assessment); the
// ERROR fallback only covers a hand-built record that claims
// category_correct with no assessment. The list sorts by scenario
// id, so the section never depends on record order.
export function computeCategoryCorrect(records) {
  const byId = (a, b) => (a.scenarioId < b.scenarioId ? -1 : a.scenarioId > b.scenarioId ? 1 : 0);
  return records
    .filter((r) => r.category_correct)
    .map((r) => ({
      scenarioId: r.scenario_id,
      truth: r.ground_truth_label,
      predicted: r.actual_category === null ? ERROR_PREDICTED : r.actual_category,
    }))
    .sort(byId);
}

// Truth-vs-predicted category counts for a run's records. Only the
// two record fields the table needs are read, so hand-built record
// lists work as well as full run JSON. Truth categories sort
// alphabetically; predicted categories sort alphabetically with
// ERROR last, so a held-state run's all-ERROR column never sorts
// ahead of a real category. Errored records (actual_category null)
// count under ERROR: they produced no prediction, so they are
// failures, not confusions.
export function computeCategoryConfusion(records) {
  const counts = {};
  for (const r of records) {
    const predicted = r.actual_category === null ? ERROR_PREDICTED : r.actual_category;
    counts[r.ground_truth_label] ??= {};
    counts[r.ground_truth_label][predicted] = (counts[r.ground_truth_label][predicted] || 0) + 1;
  }
  const truthCategories = Object.keys(counts).sort();
  const predictedSet = new Set();
  for (const truth of truthCategories) {
    for (const predicted of Object.keys(counts[truth])) predictedSet.add(predicted);
  }
  const predictedCategories = [...predictedSet].sort((a, b) => {
    if (a === ERROR_PREDICTED) return 1;
    if (b === ERROR_PREDICTED) return -1;
    return a < b ? -1 : a > b ? 1 : 0;
  });
  return { truthCategories, predictedCategories, counts };
}

// For each confusable-negative truth category present in the
// records: how many of its scenarios there are, how many were
// assessed at all, and how many were predicted as an alert category
// (a confusable false alarm), grouped by the predicted alert category
// with scenario ids. A truth category with no assessed scenarios
// reports zero assessed rather than zero false alarms, so a
// held-state run never reads as "no confusable problem" — it reads
// as "nothing assessed".
export function computeConfusableNegatives(records) {
  return CONFUSABLE_NEGATIVE_CATEGORIES.map((truth) => {
    const truthRecords = records.filter((r) => r.ground_truth_label === truth);
    const assessed = truthRecords.filter((r) => r.actual_category !== null);
    const falseAlarms = {};
    for (const r of assessed) {
      if (!IGNIS_ALERT_CATEGORIES.includes(r.actual_category)) continue;
      falseAlarms[r.actual_category] ??= [];
      falseAlarms[r.actual_category].push(r.scenario_id);
    }
    const falseAlarmCount = Object.values(falseAlarms).reduce((n, ids) => n + ids.length, 0);
    return { truth, total: truthRecords.length, assessed: assessed.length, falseAlarmCount, falseAlarms };
  }).filter((entry) => entry.total > 0);
}

// Error-message breakdown: records carrying an error message,
// grouped by the exact message string, so a run that fails in
// several different ways reads as a failure profile, not one lump.
// The summary line's count + id list stays the total; this section
// splits it. Sorting is count descending, then message
// alphabetically, so the section never depends on record order.
// A record that carries both an assessment and an error message is
// still grouped here: the message is evidence of a failure mode,
// not a claim that no assessment exists. Records with no error
// message are excluded, never counted as a blank-message group.
export function computeErrorBreakdown(records) {
  const groups = {};
  for (const r of records) {
    if (r.error === null) continue;
    groups[r.error] ??= [];
    groups[r.error].push(r.scenario_id);
  }
  return Object.entries(groups)
    .map(([message, scenarioIds]) => ({ message, count: scenarioIds.length, scenarioIds }))
    .sort((a, b) => {
      if (a.count !== b.count) return b.count - a.count;
      return a.message < b.message ? -1 : a.message > b.message ? 1 : 0;
    });
}

// Alert-level errors: the scenarios behind the summary line's
// FP/FN counts, split from the category Misses. A false positive
// fired an alert where none was expected; a false negative missed
// an expected alert. The split uses alert_expected/alert_fired
// only, so it stays meaningful when the category view does not: a
// source can fire the right alert with the wrong category (an alert
// success, a category miss) or the wrong alert outcome with the
// right non-alert category. Predicted is ERROR for unassessed
// records, matching the confusion table's convention. Each list
// sorts by scenario id, so the section never depends on record
// order. Records whose alert outcome matched expectation appear in
// neither list.
export function computeAlertErrors(records) {
  const byId = (a, b) => (a.scenarioId < b.scenarioId ? -1 : a.scenarioId > b.scenarioId ? 1 : 0);
  const entry = (r) => ({
    scenarioId: r.scenario_id,
    truth: r.ground_truth_label,
    predicted: r.actual_category === null ? ERROR_PREDICTED : r.actual_category,
  });
  const falsePositives = records
    .filter((r) => r.alert_fired && !r.alert_expected)
    .map(entry)
    .sort(byId);
  const falseNegatives = records
    .filter((r) => r.alert_expected && !r.alert_fired)
    .map(entry)
    .sort(byId);
  return { falsePositives, falseNegatives };
}

// Alert-level correct outcomes: the scenarios behind the summary
// line's TP/TN counts, completing the set computeAlertErrors starts.
// A true positive fired an expected alert; a true negative fired no
// alert where none was expected. The split uses alert_expected /
// alert_fired only, matching the metrics definition, so the two list
// lengths always equal the summary line's TP and TN counts. That
// also fixes the edge cases honestly: a right-alert, wrong-category
// record is a true positive (an alert success, a category miss),
// and an unassessed record on a non-alert scenario is a true
// negative — no alert fired, none expected — even though no
// assessment was produced, so it reads as ERROR. Each list sorts by
// scenario id, so the section never depends on record order.
// Records whose alert outcome missed expectation appear in neither
// list; they are the alert errors.
export function computeAlertCorrect(records) {
  const byId = (a, b) => (a.scenarioId < b.scenarioId ? -1 : a.scenarioId > b.scenarioId ? 1 : 0);
  const entry = (r) => ({
    scenarioId: r.scenario_id,
    truth: r.ground_truth_label,
    predicted: r.actual_category === null ? ERROR_PREDICTED : r.actual_category,
  });
  const truePositives = records
    .filter((r) => r.alert_expected && r.alert_fired)
    .map(entry)
    .sort(byId);
  const trueNegatives = records
    .filter((r) => !r.alert_expected && !r.alert_fired)
    .map(entry)
    .sort(byId);
  return { truePositives, trueNegatives };
}

export function assertWritableReportPath(outPath) {
  if (PROTECTED_REPORT_NAMES.includes(basename(outPath))) {
    throw new Error(
      `refusing to overwrite protected report "${basename(outPath)}": ` +
        "the fixture/held/baseline trio are historical records — write a live run to live-run-report.md instead",
    );
  }
}

function fmt(v) {
  return v === null ? "n/a" : v.toFixed(3);
}

function fmtLatency(v) {
  return v === null ? "n/a" : v.toFixed(1);
}

// Signed deltas against a supplied baseline run's metrics: run minus
// baseline for the two bar metrics, recall and category accuracy. A
// delta is null when either side is null (e.g. recall on a run that
// never fired an alert is n/a, not zero), so a null delta never reads
// as "no change". The beats flags reuse the verdict's definition:
// strictly greater on BOTH metrics, never precision alone.
export function computeBaselineDeltas(runMetrics, baselineMetrics) {
  const delta = (a, b) => (a === null || b === null ? null : a - b);
  const recallDelta = delta(runMetrics.recall, baselineMetrics.recall);
  const categoryAccuracyDelta = delta(runMetrics.category_accuracy, baselineMetrics.category_accuracy);
  const recallBeats = recallDelta !== null && recallDelta > 0;
  const accuracyBeats = categoryAccuracyDelta !== null && categoryAccuracyDelta > 0;
  return { recallDelta, categoryAccuracyDelta, recallBeats, accuracyBeats, beats: recallBeats && accuracyBeats };
}

export function renderRunReport(run, baselineRun = null) {
  const errors = validateRunJson(run);
  if (errors.length > 0) throw new Error(`invalid run JSON: ${errors.join("; ")}`);
  let baseline = null;
  if (baselineRun !== null) {
    const baselineErrors = validateRunJson(baselineRun);
    if (baselineErrors.length > 0) {
      throw new Error(`invalid baseline run JSON: ${baselineErrors.join("; ")}`);
    }
    baseline = baselineRun;
  }
  const kind = classifyRunKind(run);
  const m = run.metrics;
  const lines = [
    `# Meta Ignis ${KIND_TITLES[kind]} run report`,
    "",
    KIND_INTRO[kind],
    "",
  ];
  if (run.source) lines.push(`- Source: ${run.source}`);
  if (run.generated) lines.push(`- Generated: ${run.generated}`);
  lines.push(
    `- Sample size: ${m.sample_size} scenarios`,
    `- Confusion (alert): TP=${m.true_positives} FP=${m.false_positives} TN=${m.true_negatives} FN=${m.false_negatives}`,
    `- Precision: ${fmt(m.precision)}${m.precision === null ? " (no alert ever predicted; denominator zero)" : ""}`,
    `- Recall: ${fmt(m.recall)}`,
    `- False-positive rate: ${fmt(m.false_positive_rate)}`,
    `- False-negative rate: ${fmt(m.false_negative_rate)}`,
    `- Category accuracy: ${fmt(m.category_accuracy)}`,
    `- Latency (harness wall clock): mean ${fmtLatency(m.latency_ms.mean)} ms, median ${fmtLatency(m.latency_ms.median)} ms, max ${fmtLatency(m.latency_ms.max)} ms`,
    `- Errors: ${m.errors.count}${m.errors.scenario_ids.length > 0 ? ` (${m.errors.scenario_ids.join(", ")})` : ""}`,
    "",
  );
  const headline = computeCategoryHeadline(run.records);
  lines.push("## Headline finding", "");
  if (headline.weakest === null) {
    lines.push(
      "No category finding: nothing in this run was assessed, so no weakest category " +
        "or confused pair can be named. This run's numbers describe source availability, not detection.",
    );
  } else if (headline.weakest.rate === 1) {
    lines.push("No category misses: every assessed scenario matched its ground truth.");
  } else {
    const w = headline.weakest;
    lines.push(`- Weakest category: ${w.truth} — ${w.correct} of ${w.total} correct (${w.rate.toFixed(3)}).`);
    if (headline.mostConfused === null) {
      lines.push("- Most confused pair: none — every category miss in this run produced no assessment (ERROR), not a wrong category.");
    } else {
      const p = headline.mostConfused;
      lines.push(`- Most confused pair: ${p.truth} -> ${p.predicted} — ${p.count} scenario(s) (${p.scenarioIds.join(", ")}).`);
    }
  }
  const slowest = computeSlowestScenario(run.records);
  if (slowest === null) {
    lines.push("- Slowest scenario: none recorded — no record in this run carries a latency measurement.");
  } else {
    lines.push(`- Slowest scenario: ${slowest.scenarioId} (${slowest.truth}) — ${fmtLatency(slowest.latencyMs)} ms (harness wall clock).`);
  }
  const rates = computeCategoryRates(run.records);
  lines.push(
    "",
    "## Per-category rates",
    "",
    "Each row is one ground-truth category: correct predictions over all of its scenarios. " +
      "Records that produced no assessment count as misses, matching category-accuracy semantics " +
      "and the headline's definition — so the headline's weakest category is the lowest row here " +
      "(headline ties break by most misses, then truth name). The assessed column keeps a held-state " +
      "row of 0.000 honest: it means nothing was assessed, not that a source scored zero.",
    "",
    "| Truth | Correct | Total | Assessed | Rate |",
    "| --- | --- | --- | --- | --- |",
  );
  for (const row of rates) {
    lines.push(`| ${row.truth} | ${row.correct} | ${row.total} | ${row.assessed} | ${row.rate.toFixed(3)} |`);
  }
  const outlierIds = new Set(computeLatencyOutliers(run.records).map((o) => o.scenarioId));
  lines.push(
    "",
    "## Per-scenario records",
    "",
    "A scenario is flagged as a latency outlier when its harness wall-clock latency is more than " +
      "twice the median recorded latency for this run. Runs with fewer than two recorded latencies, " +
      "or a median recorded latency of zero, flag nothing — there is no typical latency to compare " +
      "against, so no scenario is singled out on a zero baseline.",
    "",
    "| Scenario | Truth | Actual | Alert correct | Category correct | Latency (ms) | Outlier | Error |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
  );
  for (const r of run.records) {
    // Harness wall clock per scenario, never a reported model field;
    // a record that carries no latency renders n/a, not zero.
    const latency = typeof r.latency_ms === "number" ? fmtLatency(r.latency_ms) : "n/a";
    lines.push(
      `| ${r.scenario_id} | ${r.ground_truth_label} | ${r.actual_category === null ? "ERROR" : r.actual_category} | ` +
        `${r.alert_correct} | ${r.category_correct} | ${latency} | ${outlierIds.has(r.scenario_id) ? "yes" : ""} | ${r.error === null ? "" : r.error} |`,
    );
  }
  const latencyDist = computeLatencyDistribution(run.records);
  lines.push(
    "",
    "## Latency distribution",
    "",
    "Harness wall-clock latencies for this run, expanding the summary line's mean/median/max " +
      "into min, quartiles and p90. Quantiles use linear interpolation on the sorted recorded " +
      "latencies, so the median here is the same averaged-middle median as the summary line " +
      "and the outlier threshold above. Records with no latency take no part.",
    "",
  );
  if (latencyDist === null) {
    lines.push("No latency distribution: no record in this run carries a latency measurement.");
  } else {
    lines.push(
      `- Recorded latencies: ${latencyDist.count} of ${run.records.length} scenario(s).`,
      `- Minimum: ${fmtLatency(latencyDist.minMs)} ms.`,
      `- 25th percentile: ${fmtLatency(latencyDist.p25Ms)} ms.`,
      `- Median: ${fmtLatency(latencyDist.medianMs)} ms.`,
      `- 75th percentile: ${fmtLatency(latencyDist.p75Ms)} ms.`,
      `- 90th percentile: ${fmtLatency(latencyDist.p90Ms)} ms.`,
      `- Maximum: ${fmtLatency(latencyDist.maxMs)} ms.`,
    );
  }
  const latencyOutliers = computeLatencyOutliers(run.records);
  lines.push(
    "",
    "## Latency outliers",
    "",
    "The scenarios whose harness wall-clock latency is more than twice the median recorded " +
      "latency for this run — the same scenarios the per-scenario table flags with \"yes\" in " +
      "the Outlier column, named here so the latency tail needs no scan of that table. " +
      "Runs with fewer than two recorded latencies, or a median recorded latency of zero, " +
      "flag nothing — there is no typical latency to compare against.",
    "",
  );
  if (latencyOutliers.length === 0) {
    lines.push(
      run.records.some((r) => typeof r.latency_ms === "number")
        ? "None: no scenario's latency is more than twice the run's median recorded latency."
        : "None recorded: no record in this run carries a latency measurement, so no outlier can be named.",
    );
  } else {
    lines.push(
      "| Scenario | Truth | Latency (ms) | Median (ms) | Threshold (ms) |",
      "| --- | --- | --- | --- | --- |",
    );
    for (const o of latencyOutliers) {
      lines.push(`| ${o.scenarioId} | ${o.truth} | ${fmtLatency(o.latencyMs)} | ${fmtLatency(o.medianMs)} | ${fmtLatency(o.thresholdMs)} |`);
    }
  }
  const latencyByCategory = computeLatencyByCategory(run.records);
  lines.push(
    "",
    "## Latency by category",
    "",
    "Harness wall-clock latencies broken down by ground-truth category, so a slow category is " +
      "visible without scanning the per-scenario table. Mean and median are over the recorded " +
      "latencies only; a category with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Truth | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByCategory) {
    lines.push(
      `| ${row.truth} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByOutcome = computeLatencyByOutcome(run.records);
  lines.push(
    "",
    "## Latency by outcome",
    "",
    "Harness wall-clock latencies broken down by outcome — correct (predicted category matched " +
      "the ground truth), miss (an assessment was returned but differed), unassessed (no " +
      "assessment was returned) — so a slow failure mode is visible without scanning the " +
      "per-scenario table. Mean and median are over the recorded latencies only; all three " +
      "rows always render, so the scenario totals sum to the sample size, and a group with " +
      "no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Outcome | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByOutcome) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByAlertOutcome = computeLatencyByAlertOutcome(run.records);
  lines.push(
    "",
    "## Latency by alert outcome",
    "",
    "Harness wall-clock latencies broken down by alert outcome — true positive (an expected alert " +
      "fired), true negative (no alert fired where none was expected), false positive (an alert " +
      "fired where none was expected), false negative (an expected alert never fired) — so a slow " +
      "alert failure mode is visible without scanning the per-scenario table. Mean and median are " +
      "over the recorded latencies only; all four rows always render, so the scenario totals sum " +
      "to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Alert outcome | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByAlertOutcome) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByAlertCorrectness = computeLatencyByAlertCorrectness(run.records);
  lines.push(
    "",
    "## Latency by alert correctness",
    "",
    "Harness wall-clock latencies collapsed from the alert-outcome split above into two " +
      "groups — alert correct (an expected alert fired, or no alert fired where none was " +
      "expected: true positives plus true negatives) versus alert error (an alert fired " +
      "where none was expected, or an expected alert never fired: false positives plus " +
      "false negatives) — so whether alert failures as a whole run slower than alert " +
      "successes is visible without adding the four rows above. Mean and median are over " +
      "the recorded latencies only; both rows always render, so the scenario totals sum " +
      "to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Alert correctness | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByAlertCorrectness) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByAlertExpectation = computeLatencyByAlertExpectation(run.records);
  lines.push(
    "",
    "## Latency by alert expectation",
    "",
    "Harness wall-clock latencies split by whether an alert was expected at all — alert " +
      "expected (an expected alert fired, or an expected alert never fired: true positives " +
      "plus false negatives) versus alert not expected (no alert fired where none was " +
      "expected, or an alert fired where none was expected: true negatives plus false " +
      "positives) — so whether alert-bearing scenarios run slower than non-alert ones is " +
      "visible without adding the four alert-outcome rows above. Mean and median are over " +
      "the recorded latencies only; both rows always render, so the scenario totals sum " +
      "to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Alert expectation | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByAlertExpectation) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByAlertFired = computeLatencyByAlertFired(run.records);
  lines.push(
    "",
    "## Latency by alert fired",
    "",
    "Harness wall-clock latencies split by whether an alert fired at all — alert " +
      "fired (an expected alert fired, or an alert fired where none was expected: true " +
      "positives plus false positives) versus alert not fired (no alert fired where none " +
      "was expected, or an expected alert never fired: true negatives plus false " +
      "negatives) — so whether alert-firing scenarios run slower than quiet ones is " +
      "visible without adding the four alert-outcome rows above. Mean and median are over " +
      "the recorded latencies only; both rows always render, so the scenario totals sum " +
      "to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Alert fired | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByAlertFired) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByAssessed = computeLatencyByAssessed(run.records);
  lines.push(
    "",
    "## Latency by assessed",
    "",
    "Harness wall-clock latencies split by whether an assessment was returned at all — " +
      "assessed (a category was returned, right or wrong: correct plus miss) versus " +
      "unassessed (no assessment was returned) — so whether scenarios that fail to " +
      "produce an assessment run slower than ones that do is visible without adding " +
      "the three outcome rows above. Mean and median are over the recorded latencies " +
      "only; both rows always render, so the scenario totals sum to the sample size, " +
      "and a group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Assessed | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByAssessed) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByCategoryCorrectness = computeLatencyByCategoryCorrectness(run.records);
  lines.push(
    "",
    "## Latency by category correctness",
    "",
    "Harness wall-clock latencies split by whether the predicted category matched the " +
      "ground truth — category correct (the exact match) versus category incorrect (a " +
      "miss plus every unassessed record) — so whether scenarios that get the category " +
      "wrong run slower than ones that get it right is visible without adding the three " +
      "outcome rows above. Mean and median are over the recorded latencies only; both " +
      "rows always render, so the scenario totals sum to the sample size, and a group " +
      "with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Category correctness | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByCategoryCorrectness) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByMissStatus = computeLatencyByMissStatus(run.records);
  lines.push(
    "",
    "## Latency by miss status",
    "",
    "Harness wall-clock latencies split by whether the record is a miss — miss (an " +
      "assessment was returned but differed from the ground truth) versus non-miss (the " +
      "exact match plus every unassessed record) — completing the three two-way collapses " +
      "of the outcome split with assessed and category correctness, so whether scenarios " +
      "that return a wrong category run slower than ones that do not is visible without " +
      "adding the three outcome rows above. Mean and median are over the recorded latencies " +
      "only; both rows always render, so the scenario totals sum to the sample size, and a " +
      "group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Miss status | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByMissStatus) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByPredictedCategory = computeLatencyByPredictedCategory(run.records);
  lines.push(
    "",
    "## Latency by predicted category",
    "",
    "Harness wall-clock latencies broken down by predicted category — the predicted-side " +
      "mirror of latency by category, so a slow predicted category is visible without " +
      "scanning the per-scenario table. An unassessed record reads as ERROR, matching the " +
      "confusion table's convention, and predicted categories sort alphabetically with " +
      "ERROR last. Mean and median are over the recorded latencies only; a category with " +
      "no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Predicted | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByPredictedCategory) {
    lines.push(
      `| ${row.predicted} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByErrorStatus = computeLatencyByErrorStatus(run.records);
  lines.push(
    "",
    "## Latency by error status",
    "",
    "Harness wall-clock latencies split by whether the record carries an error message — " +
      "errored (a record that failed in some way, whether or not it also returned an " +
      "assessment) versus no error — so whether failing scenarios run slower than clean " +
      "ones is visible without scanning the per-scenario table. Mean and median are over " +
      "the recorded latencies only; both rows always render, so the scenario totals sum " +
      "to the sample size, and a group with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Error status | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByErrorStatus) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByErrorMessage = computeLatencyByErrorMessage(run.records);
  lines.push(
    "",
    "## Latency by error message",
    "",
    "Harness wall-clock latencies for the errored records only, split by the distinct error " +
      "message each record carries — the per-message refinement of latency by error status, " +
      "so whether one failure mode runs slower than another is visible without scanning the " +
      "per-scenario table. Rows sort most frequent first, ties alphabetical, matching the " +
      "error-message breakdown's order; the scenario totals sum to the error count, not the " +
      "sample size, since records with no error message appear in neither row. Mean and " +
      "median are over the recorded latencies only; a message with no recorded latency " +
      "shows n/a, never a fabricated zero.",
    "",
  );
  if (latencyByErrorMessage.length === 0) {
    lines.push("None: no record carried an error message.");
  } else {
    lines.push(
      "| Error message | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByErrorMessage) {
      lines.push(
        `| ${row.message} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByTruthPredictedPair = computeLatencyByTruthPredictedPair(run.records);
  lines.push(
    "",
    "## Latency by truth -> predicted pair",
    "",
    "Harness wall-clock latencies broken down by ground-truth -> predicted pair — the joint " +
      "breakdown behind latency by category and latency by predicted category, so whether " +
      "one particular swap runs slower than another is visible without scanning the " +
      "per-scenario table. Rows sort by truth alphabetically, then predicted alphabetically " +
      "with ERROR last, matching the confusion table's ordering; an unassessed record reads " +
      "as ERROR. The diagonal correct pairs are included, so the scenario totals sum to the " +
      "sample size. Mean and median are over the recorded latencies only; a pair with no " +
      "recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Truth | Predicted | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByTruthPredictedPair) {
    lines.push(
      `| ${row.truth} | ${row.predicted} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByConfusableStatus = computeLatencyByConfusableStatus(run.records);
  lines.push(
    "",
    "## Latency by confusable-negative status",
    "",
    "Harness wall-clock latencies broken down by confusable-negative status — confusable negative " +
      "(ground truth steam or fog, or flame-like lighting: the scenes a source plausibly mistakes " +
      "for an alert), other non-alert (every other non-alert truth), alert (ground truth visible " +
      "smoke or visible flame) — so whether the false-alarm-prone scenes as a class run slower " +
      "than the scenes that should never fire is visible without scanning the per-scenario table. " +
      "All three rows always render, so the scenario totals sum to the sample size, and a group " +
      "with no recorded latency shows n/a, never a fabricated zero.",
    "",
    "| Status | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
    "| --- | --- | --- | --- | --- | --- |",
  );
  for (const row of latencyByConfusableStatus) {
    lines.push(
      `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
    );
  }
  const latencyByMissPair = computeLatencyByMissPair(run.records);
  lines.push(
    "",
    "## Latency by miss pair",
    "",
    "Harness wall-clock latencies broken down by miss pair — one row per truth -> predicted pair " +
      "among the misses only, most frequent first, so whether the dominant swap runs slower than " +
      "the other misses is visible without scanning the per-scenario table. The scenario totals " +
      "sum to the miss count, not the sample size, and a pair with no recorded latency shows n/a, " +
      "never a fabricated zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissPair.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Truth | Predicted | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissPair) {
      lines.push(
        `| ${row.truth} | ${row.predicted} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissTruth = computeLatencyByMissTruth(run.records);
  lines.push(
    "",
    "## Latency by miss truth category",
    "",
    "Harness wall-clock latencies broken down by ground-truth category — one row per truth category " +
      "among the misses only, most frequent first, so whether one truth category's misses as a class " +
      "run slower than another's is visible without scanning the per-scenario table. The scenario totals " +
      "sum to the miss count, not the sample size, and a category with no recorded latency shows n/a, " +
      "never a fabricated zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissTruth.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Truth | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissTruth) {
      lines.push(
        `| ${row.truth} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissPredicted = computeLatencyByMissPredicted(run.records);
  lines.push(
    "",
    "## Latency by miss predicted category",
    "",
    "Harness wall-clock latencies broken down by predicted category — one row per predicted category " +
      "among the misses only, most frequent first, so whether one predicted category's misses as a class " +
      "run slower than another's is visible without scanning the per-scenario table. The scenario totals " +
      "sum to the miss count, not the sample size, and a category with no recorded latency shows n/a, " +
      "never a fabricated zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissPredicted.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Predicted | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissPredicted) {
      lines.push(
        `| ${row.predicted} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissErrorStatus = computeLatencyByMissErrorStatus(run.records);
  lines.push(
    "",
    "## Latency by miss error status",
    "",
    "Harness wall-clock latencies broken down by error status — one row per error-status group " +
      "among the misses only, errored first, so whether the misses that failed outright run slower " +
      "than the misses that returned a wrong category is visible without scanning the per-scenario " +
      "table. The scenario totals sum to the miss count, not the sample size, and a group with no " +
      "recorded latency shows n/a, never a fabricated zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissErrorStatus.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Status | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissErrorStatus) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissErrorMessage = computeLatencyByMissErrorMessage(run.records);
  lines.push(
    "",
    "## Latency by miss error message",
    "",
    "Harness wall-clock latencies for the errored misses only, split by the distinct error " +
      "message each miss carries — the per-message refinement of latency by miss error status, " +
      "so whether one failure mode runs slower than another among the misses is visible " +
      "without scanning the per-scenario table. Rows sort most frequent first, ties " +
      "alphabetical, matching the error-message breakdown's order; the scenario totals sum " +
      "to the errored-miss count, not the miss count, since misses with no error message " +
      "appear in no row. A message with no recorded latency shows n/a, never a fabricated " +
      "zero; a run with no errored miss says none.",
    "",
  );
  if (latencyByMissErrorMessage.length === 0) {
    lines.push("None: no miss carried an error message.");
  } else {
    lines.push(
      "| Error message | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissErrorMessage) {
      lines.push(
        `| ${row.message} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissAlertOutcome = computeLatencyByMissAlertOutcome(run.records);
  lines.push(
    "",
    "## Latency by miss alert outcome",
    "",
    "Harness wall-clock latencies broken down by alert outcome — one row per alert-outcome group " +
      "among the misses only, in fixed order true positive, true negative, false positive, false " +
      "negative, so whether the misses that fired an alert run slower than the misses that stayed " +
      "silent is visible without scanning the per-scenario table. Only groups present among the " +
      "misses render, so the scenario totals sum to the miss count, not the sample size, and a " +
      "group with no recorded latency shows n/a, never a fabricated zero; a run with no misses " +
      "says none.",
    "",
  );
  if (latencyByMissAlertOutcome.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Alert outcome | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissAlertOutcome) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissAlertCorrectness = computeLatencyByMissAlertCorrectness(run.records);
  lines.push(
    "",
    "## Latency by miss alert correctness",
    "",
    "Harness wall-clock latencies broken down by alert correctness — one row per alert-correctness group " +
      "among the misses only, in fixed order alert correct, alert error, so whether the misses whose alert " +
      "was right run slower than the misses whose alert was wrong is visible without scanning the " +
      "per-scenario table. Only groups present among the misses render, so the scenario totals sum to the " +
      "miss count, not the sample size, and a group with no recorded latency shows n/a, never a fabricated " +
      "zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissAlertCorrectness.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Alert correctness | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissAlertCorrectness) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissAlertExpectation = computeLatencyByMissAlertExpectation(run.records);
  lines.push(
    "",
    "## Latency by miss alert expectation",
    "",
    "Harness wall-clock latencies broken down by alert expectation — one row per alert-expectation group " +
      "among the misses only, in fixed order alert expected, alert not expected, so whether the misses where an " +
      "alert was expected run slower than the misses where none was is visible without scanning the " +
      "per-scenario table. Only groups present among the misses render, so the scenario totals sum to the " +
      "miss count, not the sample size, and a group with no recorded latency shows n/a, never a fabricated " +
      "zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissAlertExpectation.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Alert expectation | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissAlertExpectation) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissAlertFired = computeLatencyByMissAlertFired(run.records);
  lines.push(
    "",
    "## Latency by miss alert fired",
    "",
    "Harness wall-clock latencies broken down by whether an alert fired at all — one row per alert-fired group " +
      "among the misses only, in fixed order alert fired, alert not fired, so whether the misses that fired an " +
      "alert run slower than the misses that stayed silent is visible in two rows without adding the four " +
      "alert-outcome rows above. Only groups present among the misses render, so the scenario totals sum to the " +
      "miss count, not the sample size, and a group with no recorded latency shows n/a, never a fabricated " +
      "zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissAlertFired.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Alert fired | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissAlertFired) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissAssessed = computeLatencyByMissAssessed(run.records);
  lines.push(
    "",
    "## Latency by miss assessed",
    "",
    "Harness wall-clock latencies broken down by whether an assessment was returned at all — one row per " +
      "assessed-status group among the misses only, in fixed order assessed, unassessed, so whether the misses " +
      "that returned a wrong category run slower than the misses that returned nothing is visible in two rows " +
      "without adding the correct records the latency-by-assessed section includes. Only groups present among " +
      "the misses render, so the scenario totals sum to the miss count, not the sample size, and a group with " +
      "no recorded latency shows n/a, never a fabricated zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissAssessed.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Assessed | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissAssessed) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissOutcome = computeLatencyByMissOutcome(run.records);
  lines.push(
    "",
    "## Latency by miss outcome",
    "",
    "Harness wall-clock latencies broken down by outcome among the misses only — one row per " +
      "outcome group, in fixed order miss, unassessed, so whether the misses that returned a wrong category " +
      "run slower than the misses that returned nothing is visible in two rows without adding the correct " +
      "records the latency-by-outcome section includes. Only groups present among the misses render, so the " +
      "scenario totals sum to the miss count, not the sample size, and a group with no recorded latency " +
      "shows n/a, never a fabricated zero; a run with no misses says none.",
    "",
  );
  if (latencyByMissOutcome.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Outcome | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissOutcome) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const latencyByMissConfusableStatus = computeLatencyByMissConfusableStatus(run.records);
  lines.push(
    "",
    "## Latency by miss confusable-negative status",
    "",
    "Harness wall-clock latencies broken down by confusable-negative status among the misses only — one row per " +
      "status group, in fixed order confusable negative, other non-alert, alert, so whether the misses on the " +
      "false-alarm-prone scenes run slower than the misses on other scenes is visible without scanning the " +
      "per-scenario table. Only groups present among the misses render, so the scenario totals sum to the miss " +
      "count, not the sample size, and a group with no recorded latency shows n/a, never a fabricated zero; " +
      "a run with no misses says none.",
    "",
  );
  if (latencyByMissConfusableStatus.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Status | Scenarios | Recorded | Mean (ms) | Median (ms) | Max (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const row of latencyByMissConfusableStatus) {
      lines.push(
        `| ${row.outcome} | ${row.total} | ${row.recorded} | ${fmtLatency(row.meanMs)} | ${fmtLatency(row.medianMs)} | ${fmtLatency(row.maxMs)} |`,
      );
    }
  }
  const missLatencyDist = computeMissLatencyDistribution(run.records);
  const missCount = run.records.filter((r) => !r.category_correct).length;
  lines.push(
    "",
    "## Latency distribution among misses",
    "",
    "Harness wall-clock latencies for the misses only, expanding the miss sections' means into min, " +
      "quartiles and p90 — the same quantiles as the full-run latency distribution, but over the failures " +
      "alone, so whether the misses cluster fast or drag a slow tail is visible without the correct " +
      "records pulling the numbers down. Records with no latency take no part.",
    "",
  );
  if (missCount === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else if (missLatencyDist === null) {
    lines.push("No latency distribution among the misses: no miss in this run carries a latency measurement.");
  } else {
    lines.push(
      `- Recorded latencies: ${missLatencyDist.count} of ${missCount} miss(es).`,
      `- Minimum: ${fmtLatency(missLatencyDist.minMs)} ms.`,
      `- 25th percentile: ${fmtLatency(missLatencyDist.p25Ms)} ms.`,
      `- Median: ${fmtLatency(missLatencyDist.medianMs)} ms.`,
      `- 75th percentile: ${fmtLatency(missLatencyDist.p75Ms)} ms.`,
      `- 90th percentile: ${fmtLatency(missLatencyDist.p90Ms)} ms.`,
      `- Maximum: ${fmtLatency(missLatencyDist.maxMs)} ms.`,
    );
  }
  const missLatencyOutliers = computeMissLatencyOutliers(run.records);
  lines.push(
    "",
    "## Latency outliers among misses",
    "",
    "The misses whose harness wall-clock latency is more than twice the median recorded " +
      "latency among the misses alone — the same strict rule as the full-run latency " +
      "outliers, but judged against the failures' own typical latency, so a slow failure " +
      "is visible without the correct records pulling the median up or down. A run with " +
      "fewer than two recorded miss latencies, or a median miss latency of zero, flags " +
      "nothing — there is no typical miss latency to compare against.",
    "",
  );
  if (missCount === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else if (missLatencyOutliers.length === 0) {
    lines.push(
      run.records.some((r) => !r.category_correct && typeof r.latency_ms === "number")
        ? "None: no miss's latency is more than twice the misses' median recorded latency."
        : "None recorded: no miss in this run carries a latency measurement, so no outlier can be named.",
    );
  } else {
    lines.push(
      "| Scenario | Truth | Latency (ms) | Median (ms) | Threshold (ms) |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const o of missLatencyOutliers) {
      lines.push(`| ${o.scenarioId} | ${o.truth} | ${fmtLatency(o.latencyMs)} | ${fmtLatency(o.medianMs)} | ${fmtLatency(o.thresholdMs)} |`);
    }
  }
  const slowestMiss = computeSlowestMiss(run.records);
  lines.push(
    "",
    "## Slowest miss",
    "",
    "The slowest miss by harness wall-clock latency — the same slowest-scenario rule as the headline " +
      "finding, but over the misses alone, so the slowest failure is visible without a correct record's " +
      "slow latency hiding it, and without scanning the per-scenario table. Records with no latency " +
      "take no part, never treated as zero; ties break by scenario id alphabetically.",
    "",
  );
  if (missCount === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else if (slowestMiss === null) {
    lines.push("None recorded: no miss in this run carries a latency measurement, so no slowest miss can be named.");
  } else {
    lines.push(`- Slowest miss: ${slowestMiss.scenarioId} (${slowestMiss.truth}) — ${fmtLatency(slowestMiss.latencyMs)} ms (harness wall clock).`);
  }
  const fastestMiss = computeFastestMiss(run.records);
  lines.push(
    "",
    "## Fastest miss",
    "",
    "The fastest miss by harness wall-clock latency — the mirror of the slowest miss, over the " +
      "misses alone, so the quickest failure is visible without a correct record's fast latency " +
      "hiding it, and without scanning the per-scenario table. Records with no latency " +
      "take no part, never treated as zero; ties break by scenario id alphabetically.",
    "",
  );
  if (missCount === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else if (fastestMiss === null) {
    lines.push("None recorded: no miss in this run carries a latency measurement, so no fastest miss can be named.");
  } else {
    lines.push(`- Fastest miss: ${fastestMiss.scenarioId} (${fastestMiss.truth}) — ${fmtLatency(fastestMiss.latencyMs)} ms (harness wall clock).`);
  }
  const misses = computeMisses(run.records);
  lines.push("", `## Misses (${misses.length})`, "");
  lines.push(
    misses.length > 0
      ? misses
          .map(
            (m) =>
              `- ${m.scenarioId}: ${m.truth} -> ${m.predicted}` +
              (m.predicted === ERROR_PREDICTED ? " (no assessment)" : ""),
          )
          .join("\n")
      : "None: every scenario's predicted category matched its ground truth.",
  );
  const missPairs = computeMissPairs(run.records);
  lines.push("", "## Miss-pair counts", "");
  lines.push(
    "The misses above, aggregated by truth -> predicted pair: one row " +
      "per pair, most frequent first, so the dominant swap is visible " +
      "without counting the Misses list. ERROR rows are failures, not " +
      "confusions — a run whose misses are all errors has no dominant swap.",
    "",
  );
  if (missPairs.length === 0) {
    lines.push("None: every scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      "| Truth | Predicted | Count | Scenarios |",
      "| --- | --- | --- | --- |",
    );
    for (const p of missPairs) {
      lines.push(`| ${p.truth} | ${p.predicted} | ${p.count} | ${p.scenarioIds.join(", ")} |`);
    }
  }
  const categoryCorrect = computeCategoryCorrect(run.records);
  lines.push(
    "",
    "## Category correct",
    "",
    "The scenarios behind category accuracy, completing the category set the Misses section " +
      "starts: these are the scenarios whose predicted category matched the ground truth exactly. " +
      "Together with the Misses list above, this list accounts for every scenario in the run — " +
      "no scenario appears in both, and none appears in neither — so the count here plus the " +
      `Misses count equals the sample size (${categoryCorrect.length} correct of ${run.records.length}).`,
    "",
  );
  if (categoryCorrect.length === 0) {
    lines.push("None: no scenario's predicted category matched its ground truth.");
  } else {
    lines.push(
      ...categoryCorrect.map(
        (e) =>
          `- ${e.scenarioId}: ${e.truth} -> ${e.predicted}` +
          (e.predicted === ERROR_PREDICTED ? " (no assessment)" : ""),
      ),
    );
  }
  const confusion = computeCategoryConfusion(run.records);
  lines.push("", "## Per-category confusion", "");
  lines.push(
    "Rows are ground-truth categories, columns are predicted categories. " +
      "Diagonal cells are correct predictions; off-diagonal cells are category misses. " +
      "The ERROR column counts records that produced no assessment — failures, not confusions.",
    "",
    `| Truth \ Predicted | ${confusion.predictedCategories.join(" | ")} | Total |`,
    `| --- | ${confusion.predictedCategories.map(() => "---").join(" | ")} | --- |`,
  );
  for (const truth of confusion.truthCategories) {
    const cells = confusion.predictedCategories.map((p) => confusion.counts[truth][p] || 0);
    const total = cells.reduce((n, c) => n + c, 0);
    lines.push(`| ${truth} | ${cells.join(" | ")} | ${total} |`);
  }
  const confusables = computeConfusableNegatives(run.records);
  const confusableTotal = confusables.reduce((n, e) => n + e.total, 0);
  const confusableFalseAlarms = confusables.reduce((n, e) => n + e.falseAlarmCount, 0);
  lines.push("", "## Confusable negatives", "");
  lines.push(
    "Confusable negatives are non-alert scenes a source plausibly mistakes for an alert: " +
      "steam or fog for smoke, flame-like lighting for flame. This section counts, per confusable " +
      "truth category, how many scenarios were predicted as an alert category (visible smoke, visible flame).",
    "",
  );
  if (confusables.length === 0) {
    lines.push("- No confusable-negative scenarios in this run.");
  }
  for (const entry of confusables) {
    if (entry.assessed === 0) {
      lines.push(`- ${entry.truth}: ${entry.total} scenario(s), none assessed — no confusable false alarm could occur.`);
    } else if (entry.falseAlarmCount === 0) {
      lines.push(`- ${entry.truth}: 0 of ${entry.total} predicted as an alert category.`);
    } else {
      const byPredicted = Object.entries(entry.falseAlarms)
        .map(([predicted, ids]) => `${predicted}: ${ids.length} (${ids.join(", ")})`)
        .join("; ");
      lines.push(`- ${entry.truth}: ${entry.falseAlarmCount} of ${entry.total} predicted as an alert category — ${byPredicted}.`);
    }
  }
  lines.push(
    "",
    `Total: ${confusableFalseAlarms} of ${confusableTotal} confusable-negative scenarios predicted as an alert category.`,
  );
  const errorBreakdown = computeErrorBreakdown(run.records);
  lines.push(
    "",
    "## Error breakdown",
    "",
    "Records carrying an error message, grouped by the exact message, so a run that fails in " +
      "several different ways reads as a failure profile, not one lump. The summary line above " +
      "carries the total; this section splits it. Most frequent first, ties alphabetical.",
    "",
  );
  if (errorBreakdown.length === 0) {
    lines.push("None: no record in this run carries an error message.");
  } else {
    lines.push(
      "| Error | Count | Scenarios |",
      "| --- | --- | --- |",
    );
    for (const e of errorBreakdown) {
      // Escape pipes so a message containing one cannot break the table.
      lines.push(`| ${e.message.replaceAll("|", "\\|")} | ${e.count} | ${e.scenarioIds.join(", ")} |`);
    }
  }
  const alertErrors = computeAlertErrors(run.records);
  lines.push(
    "",
    "## Alert errors",
    "",
    "The scenarios behind the summary line's false-positive and false-negative counts, " +
      "so an alert-level failure is diagnosable without cross-referencing the per-scenario table. " +
      "This is distinct from the category Misses above: it asks whether an alert fired at all, " +
      "not which category was predicted. ERROR rows are failures, not wrong categories — " +
      "an unassessed record on an alert-expected scenario is a false negative, not a confusion.",
    "",
  );
  if (alertErrors.falsePositives.length === 0 && alertErrors.falseNegatives.length === 0) {
    lines.push("None: every scenario's alert outcome matched its expectation.");
  } else {
    const renderList = (label, list) =>
      list.length === 0
        ? `- ${label} (0): none.`
        : [
            `- ${label} (${list.length}):`,
            ...list.map(
              (e) =>
                `  - ${e.scenarioId}: ${e.truth} -> ${e.predicted}` +
                (e.predicted === ERROR_PREDICTED ? " (no assessment)" : ""),
            ),
          ].join("\n");
    lines.push(
      renderList("False positives", alertErrors.falsePositives),
      renderList("False negatives", alertErrors.falseNegatives),
    );
  }
  const alertCorrect = computeAlertCorrect(run.records);
  lines.push(
    "",
    "## Alert correct",
    "",
    "The scenarios behind the summary line's true-positive and true-negative counts, " +
      "completing the alert-confusion set the Alert errors section starts. This is the " +
      "same alert-fired-versus-expected question, not a category claim: a true positive " +
      "may still be a category miss (right alert, wrong category). Counts here match the " +
      "summary line's TP and TN exactly, by the same definition — so an unassessed record " +
      "on a non-alert scenario appears as a true negative (no alert fired, none expected) " +
      "even though no assessment was produced, and reads as ERROR.",
    "",
  );
  if (alertCorrect.truePositives.length === 0 && alertCorrect.trueNegatives.length === 0) {
    lines.push("None: no scenario's alert outcome matched its expectation.");
  } else {
    const renderList = (label, list) =>
      list.length === 0
        ? `- ${label} (0): none.`
        : [
            `- ${label} (${list.length}):`,
            ...list.map(
              (e) =>
                `  - ${e.scenarioId}: ${e.truth} -> ${e.predicted}` +
                (e.predicted === ERROR_PREDICTED ? " (no assessment)" : ""),
            ),
          ].join("\n");
    lines.push(
      renderList("True positives", alertCorrect.truePositives),
      renderList("True negatives", alertCorrect.trueNegatives),
    );
  }
  if (baseline !== null) {
    const b = baseline.metrics;
    const deltas = computeBaselineDeltas(m, b);
    const fmtDelta = (d) => (d === null ? "n/a" : `${d >= 0 ? "+" : ""}${d.toFixed(3)}`);
    lines.push(
      "",
      "## Comparison against the baseline",
      "",
      `Baseline (always-no-hazard): recall ${fmt(b.recall)}, category accuracy ${fmt(b.category_accuracy)}.`,
      `This run: recall ${fmt(m.recall)}, category accuracy ${fmt(m.category_accuracy)}.`,
      `Recall delta: ${fmtDelta(deltas.recallDelta)} (this run minus baseline; n/a when either side's recall is n/a).`,
      `Category-accuracy delta: ${fmtDelta(deltas.categoryAccuracyDelta)} (this run minus baseline).`,
      deltas.beats
        ? "Verdict: this run BEATS the baseline on recall and category accuracy — the bar a real source must clear."
        : "Verdict: this run does NOT beat the baseline on both recall and category accuracy. " +
          "Beating it on precision alone proves nothing, since the baseline never fires a false alarm by construction.",
    );
  } else {
    lines.push(
      "",
      "## Comparison against the baseline",
      "",
      "No baseline run supplied: pass `--baseline <baseline-run.json>` to render the " +
        "recall-and-category-accuracy verdict. A source must beat the baseline on both to claim value.",
    );
  }
  lines.push(
    "",
    "## What this run does not prove",
    "",
    kind === "live-model"
      ? "A live-model run on labeled descriptions proves the wired source scores this scenario set; " +
        "it does not prove real-hardware camera performance, real photographs, or performance on scenes outside this set."
      : "This run is not a model result, and its numbers must not be quoted as one. " +
        "A live run belongs in its own live-run-report.md file, never as an edit to the fixture, held-state, or baseline trio.",
    "",
  );
  return lines.join("\n");
}

// CLI: node eval/ignis/report.mjs <run.json> [--baseline <baseline-run.json>] [--out <report.md>]
// No model call, no key, no network: it only reads run JSON files.
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  try {
    const args = process.argv.slice(2);
    // Parse sequentially so a flag's value (e.g. --out <path>) is never
    // mistaken for the positional run JSON.
    let runPath = null;
    let baselinePath = null;
    let outPath = null;
    for (let i = 0; i < args.length; i += 1) {
      if (args[i] === "--baseline" && i + 1 < args.length) baselinePath = args[++i];
      else if (args[i] === "--out" && i + 1 < args.length) outPath = args[++i];
      else if (args[i].startsWith("--")) throw new Error(`unknown or incomplete flag "${args[i]}"`);
      else if (runPath === null) runPath = args[i];
      else throw new Error(`unexpected extra argument "${args[i]}"`);
    }
    if (runPath === null) {
      throw new Error("usage: node eval/ignis/report.mjs <run.json> [--baseline <baseline-run.json>] [--out <report.md>]");
    }
    const run = JSON.parse(readFileSync(runPath, "utf8"));
    const baselineRun = baselinePath !== null ? JSON.parse(readFileSync(baselinePath, "utf8")) : null;
    const report = renderRunReport(run, baselineRun);
    if (outPath !== null) {
      assertWritableReportPath(outPath);
      writeFileSync(outPath, report);
      console.log(`Wrote ${outPath}`);
    } else {
      console.log(report);
    }
  } catch (err) {
    console.error(`report.mjs: ${err.message}`);
    process.exitCode = 1;
  }
}
