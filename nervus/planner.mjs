// Meta Nervus — the reduction planner (R11-264).
//
// A plan is not a promise that the model still works. Each proposed cut names the layers it
// removes and the before/after proof that would have to exist before anyone could call the cut
// safe: two hashes and one named probe. The plan deliberately says "proposed" in every row.
export class PlannerError extends Error {}

export function planReduction(layerMap, { keepLayers = null, minLayers = 1 } = {}) {
  if (!layerMap || !Number.isInteger(layerMap.layer_count) || layerMap.layer_count < 1) {
    throw new PlannerError("planner: a layer map with a layer count is required");
  }
  if (!Number.isInteger(minLayers) || minLayers < 1) throw new PlannerError("planner: minLayers must be >= 1");
  const target = keepLayers == null ? Math.max(minLayers, Math.floor(layerMap.layer_count / 2)) : keepLayers;
  if (!Number.isInteger(target) || target < minLayers || target >= layerMap.layer_count) {
    throw new PlannerError("planner: keepLayers must be between " + minLayers + " and " + (layerMap.layer_count - 1));
  }

  const cuts = [];
  for (let keep = layerMap.layer_count - 1; keep >= target; keep--) {
    const removed = Array.from({ length: layerMap.layer_count - keep }, (_, i) => keep + i);
    cuts.push({
      id: "cut-" + removed[0] + "-" + removed[removed.length - 1],
      removes: removed,
      before: { layers: layerMap.layer_count, model_hash: layerMap.model_hash },
      after: { layers: keep, model_hash: null },
      status: "proposed",
      proof_required: [
        "evaluate_delta record with the before_hash and after_hash of the two runs",
        "one named probe that the cut is judged against",
        "the result filed with scope=layer; this plan is not evidence",
      ],
    });
  }
  return {
    v: 1,
    plan_for: layerMap.model_hash,
    source_map: layerMap.source,
    keep: target,
    cuts,
    note: "proposals only: no cut has been made and no result is claimed",
  };
}

export function validatePlan(plan) {
  const errors = [];
  if (!plan || !Array.isArray(plan.cuts)) return ["plan must have cuts"];
  for (const c of plan.cuts) {
    if (!Array.isArray(c.removes) || c.removes.length === 0) errors.push(c.id + ": removes must be non-empty");
    if (!c.after || !("layers" in c.after)) errors.push(c.id + ": after.layers required");
    if (!Array.isArray(c.proof_required) || c.proof_required.length === 0) errors.push(c.id + ": proof_required must name the proof");
  }
  return errors;
}
