// Meta Nervus — the layer-map record (R11-263).
//
// The shape the face draws: one row per layer, with the model's identity and the provenance of
// the numbers. The inspector measures total size, not per-layer size, so a layer row's `bytes`
// is null unless a caller supplies it. Filling it with total/layers would look like a
// measurement and be an average; the record says `shape-only` instead.
export const LAYERMAP_VERSION = 1;

export function buildLayerMap(inspection, { source = "nervus/inspect.mjs", perLayer = null } = {}) {
  if (!inspection || !inspection.inspection_hash) throw new Error("layermap: an inspection record is required");
  if (!Number.isInteger(inspection.layer_count) || inspection.layer_count < 1) {
    throw new Error("layermap: the inspection has no usable layer count");
  }
  if (perLayer && perLayer.length !== inspection.layer_count) {
    throw new Error("layermap: perLayer must have exactly " + inspection.layer_count + " entries");
  }
  const layers = Array.from({ length: inspection.layer_count }, (_, i) => ({
    index: i,
    bytes: perLayer ? perLayer[i] : null,
    params: null,
  }));
  return {
    v: LAYERMAP_VERSION,
    model_hash: inspection.inspection_hash,
    architecture: inspection.architecture,
    layer_count: inspection.layer_count,
    total_bytes: inspection.total_bytes,
    layers,
    source,
    completeness: perLayer ? "per-layer sizes supplied by caller" : "shape-only: per-layer sizes were not measured",
  };
}

export function validateLayerMap(map) {
  const errors = [];
  if (!map || typeof map !== "object") return ["layer map must be an object"];
  if (!/^[0-9a-f]{8,64}$/i.test(String(map.model_hash || ""))) errors.push("model_hash required (8-64 hex)");
  if (!Number.isInteger(map.layer_count) || map.layer_count < 1) errors.push("layer_count must be a positive integer");
  if (!Array.isArray(map.layers) || map.layers.length !== map.layer_count) errors.push("layers must match layer_count");
  if (Array.isArray(map.layers)) {
    map.layers.forEach((l, i) => { if (l.index !== i) errors.push("layer " + i + " is out of order"); });
  }
  if (!map.source) errors.push("source required: the face must be able to say where the map came from");
  return errors;
}
