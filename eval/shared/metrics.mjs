// Shared eval metrics (Medicus pivot, Oct 30): the metric core both
// products import. Moved verbatim from the Medicus harness so no
// product imports metrics from another product's harness. Product
// agnostic: it scores alert/category correctness from run records
// only, never categories, prompts, or model calls.

function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function computeMetrics(records) {
  let tp = 0;
  let fp = 0;
  let tn = 0;
  let fn = 0;
  let categoryCorrect = 0;
  const latencies = [];
  const errorIds = [];
  for (const r of records) {
    if (r.alert_fired && r.alert_expected) tp += 1;
    else if (r.alert_fired && !r.alert_expected) fp += 1;
    else if (!r.alert_fired && !r.alert_expected) tn += 1;
    else fn += 1;
    if (r.category_correct) categoryCorrect += 1;
    if (typeof r.latency_ms === "number") latencies.push(r.latency_ms);
    if (r.error !== null) errorIds.push(r.scenario_id);
  }
  const ratio = (num, den) => (den > 0 ? num / den : null);
  const mean = latencies.length > 0
    ? latencies.reduce((a, b) => a + b, 0) / latencies.length
    : null;
  return {
    sample_size: records.length,
    true_positives: tp,
    false_positives: fp,
    true_negatives: tn,
    false_negatives: fn,
    precision: ratio(tp, tp + fp),
    recall: ratio(tp, tp + fn),
    false_positive_rate: ratio(fp, fp + tn),
    false_negative_rate: ratio(fn, fn + tp),
    category_accuracy: records.length > 0 ? categoryCorrect / records.length : null,
    latency_ms: {
      n: latencies.length,
      mean,
      median: median(latencies),
      max: latencies.length > 0 ? Math.max(...latencies) : null,
    },
    errors: { count: errorIds.length, scenario_ids: errorIds },
  };
}
