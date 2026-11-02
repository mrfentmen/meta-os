// Meta Nervus — the contract layer (NEURON_SURGERY_SPEC.md, first build C1/C3).
//
// What is here: the five operations as data, the ledger record shape, and the two rules the
// spec calls non-negotiable — probe dependence and the dose window. What is NOT here: a model,
// a tensor, or a claim that any of this has touched one. The runner is a stub, labelled STUB
// in its own output, because the machine with the model is not this one.
//
// The spec's discipline, quoted into code:
//   "Probe dependence: results belong to (neuron, probe) pairs. Nervus refuses to report a
//    neuron without its probe."
//   "Dose windows are real: inert, persona, collapse. Nervus labels which zone a steer landed
//    in; it never calls a dose 'a little' or 'a lot' without the window."
//   "The subspace correction: when the effect is a low-dimensional subspace, the record says
//    subspace, never 'a neuron'."
export const OPERATIONS = {
  sweep: {
    requires: ["model_hash", "layer_from", "layer_to"],
    produces: ["neurons", "results"],
    why: "measure every neuron in a layer range before claiming one matters",
  },
  steer: {
    requires: ["model_hash", "layer", "neuron", "dose", "zone", "probe"],
    produces: ["output", "result"],
    why: "a single-neuron intervention with a dose and a probe",
  },
  ablate: {
    requires: ["model_hash", "layer", "neuron", "probe"],
    produces: ["output", "result"],
    why: "remove a neuron and measure what the model no longer does",
  },
  evaluate_delta: {
    requires: ["model_hash", "before_hash", "after_hash", "probe"],
    produces: ["delta", "result"],
    why: "the before/after receipt; nothing ships without one",
  },
  map_layers: {
    requires: ["model_hash"],
    produces: ["layers"],
    why: "the layer curve, before any single-layer story",
  },
};

export const DOSE_ZONES = ["inert", "persona", "collapse"];

// The window BOUNDARIES are the boss's repo's numbers, and they are not in this file. A
// contract that invented thresholds would make every later measurement look like it agreed
// with them. The runner loads boundaries from dose-windows.json, whose `source` field must
// name where they came from before a steer record is accepted as measured.
export const DOSE_WINDOW_SOURCE_REQUIRED = true;

export const RECORD_FIELDS = ["model_hash", "operation", "probe", "result"];

const HEX = /^[0-9a-f]{8,64}$/i;

function isInt(v) { return Number.isInteger(v); }
function isNum(v) { return typeof v === "number" && Number.isFinite(v); }

// Returns an array of errors. Empty means the record can be written.
export function validateRecord(rec, { doseWindows = null } = {}) {
  const e = [];
  if (!rec || typeof rec !== "object") return ["record must be an object"];

  if (!rec.model_hash) e.push("model_hash required");
  else if (!HEX.test(String(rec.model_hash))) e.push("model_hash must be 8-64 hex characters (a hash, not a path)");

  const op = OPERATIONS[rec.operation];
  if (!op) e.push("operation must be one of " + Object.keys(OPERATIONS).join(", "));
  else for (const field of op.requires) {
    // A subspace effect has no single neuron to name, so the neuron requirement is waived
    // exactly when the record says the effect is low-dimensional. Without this the two rules
    // contradicted each other and a correct subspace record could not validate.
    if (field === "neuron" && rec.scope === "subspace") continue;
    if (rec[field] == null) e.push(field + " required for " + rec.operation);
  }

  // Probe dependence applies to every operation that reports an effect. A sweep reports a map,
  // not an effect, so it is exempt -- the spec's rule is about results, not inventories.
  if (["steer", "ablate", "evaluate_delta"].includes(rec.operation)) {
    if (typeof rec.probe !== "string" || !rec.probe.trim()) e.push("probe required: a result belongs to a (neuron, probe) pair");
  }

  if (["sweep", "steer", "ablate"].includes(rec.operation)) {
    if (!isInt(rec.layer) && rec.operation !== "sweep") e.push("layer must be an integer");
    if (!isInt(rec.neuron) && rec.operation !== "sweep" && rec.scope !== "subspace") e.push("neuron must be an integer");
  }

  if (rec.operation === "sweep") {
    if (!isInt(rec.layer_from) || !isInt(rec.layer_to)) e.push("layer_from and layer_to must be integers");
    else if (rec.layer_from > rec.layer_to) e.push("layer_from must not exceed layer_to");
  }

  if (rec.operation === "steer") {
    if (!isNum(rec.dose) || rec.dose <= 0) e.push("dose must be a positive number");
    if (!DOSE_ZONES.includes(rec.zone)) e.push("zone must be one of " + DOSE_ZONES.join(", ") + " -- a dose without its window is not reportable");
    if (DOSE_WINDOW_SOURCE_REQUIRED && doseWindows && !doseWindows.source) {
      e.push("dose windows have no named source; the steer cannot be called measured");
    }
    if (doseWindows && doseWindows.source && isNum(rec.dose)) {
      // The zone must agree with the window table when one is loaded. This is the check that
      // makes "landed in the persona zone" a claim about the numbers, not a label.
      const w = doseWindows.zones && doseWindows.zones[rec.zone];
      if (w && (rec.dose < w.min || rec.dose > w.max)) {
        e.push("dose " + rec.dose + " is outside the " + rec.zone + " window [" + w.min + ", " + w.max + "] recorded from " + doseWindows.source);
      }
    }
  }

  if (rec.operation === "evaluate_delta") {
    if (!rec.before_hash || !HEX.test(String(rec.before_hash))) e.push("before_hash required (a hash)");
    if (!rec.after_hash || !HEX.test(String(rec.after_hash))) e.push("after_hash required (a hash)");
  }

  // The subspace correction, enforced: an effect that is low-dimensional cannot be filed as a
  // neuron. `scope` defaults to neuron for a single unit and must be explicit otherwise.
  if (rec.scope != null && !["neuron", "subspace", "layer"].includes(rec.scope)) e.push("scope must be neuron, subspace or layer");
  if (rec.scope === "subspace") {
    if (rec.neuron != null) e.push("a subspace effect must not name a single neuron");
    if (!isInt(rec.subspace_dim) || rec.subspace_dim < 2) e.push("subspace_dim (>= 2) required when scope is subspace");
  }

  if (rec.result == null) e.push("result required: the operation's outcome, even when the outcome is null (a null is a result)");
  return e;
}

// The tray manifest names the boss's tools; this refuses a manifest that names a tool the
// gateway does not serve, because a named tool that does not exist is a finding, not a footnote.
export function validateTray(tray, backends) {
  const prefixes = new Set((backends.backends || []).map((b) => b.prefix));
  const missing = [];
  const seen = new Set();
  const duplicates = [];
  for (const t of tray.tools || []) {
    if (!t.prefix) { missing.push({ tool: t.tool, prefix: null, reason: "no gateway prefix" }); continue; }
    if (!prefixes.has(t.prefix)) missing.push({ tool: t.tool, prefix: t.prefix, reason: "not in the gateway's backend list" });
    if (seen.has(t.prefix)) duplicates.push(t.prefix);
    seen.add(t.prefix);
  }
  return { ok: missing.length === 0 && duplicates.length === 0, missing, duplicates, count: (tray.tools || []).length };
}
