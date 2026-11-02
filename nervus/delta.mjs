// Meta Nervus — signed evaluate-delta (R11-270).
//
// A delta is after minus before, and the sign is part of the claim. This module refuses to render
// a delta as an absolute ("better", "fixed", "solved") because those words drop the comparison
// that produced them. Without both hashes there is no record at all.
const ABSOLUTE = /\b(better|worse|improved|degraded|fixed|solved|superior|inferior|best|worst)\b/i;

export class DeltaError extends Error {}

export function signedDelta(before, after) {
  if (!Number.isFinite(before) || !Number.isFinite(after)) throw new DeltaError("delta: both readings must be finite numbers");
  const delta = after - before;
  return {
    before,
    after,
    delta,
    sign: delta > 0 ? "positive" : delta < 0 ? "negative" : "zero",
    direction: delta > 0 ? "increase" : delta < 0 ? "decrease" : "no-change",
    relative: before === 0 ? null : Number((delta / Math.abs(before)).toFixed(6)),
  };
}

export function renderDelta({ before_hash, after_hash, probe, reading, summary = "" } = {}) {
  if (!before_hash || !after_hash) {
    return { ok: false, reason: "no-before-after-hash", detail: "a delta without both hashes is not a receipt" };
  }
  if (!probe || typeof probe !== "string") {
    return { ok: false, reason: "no-probe", detail: "a delta belongs to a named probe" };
  }
  if (ABSOLUTE.test(summary)) {
    return { ok: false, reason: "absolute-claim", detail: "say the signed change, not that it is better or worse" };
  }
  const d = signedDelta(Number(reading.before), Number(reading.after));
  return {
    ok: true,
    text: probe + ": " + d.before + " -> " + d.after + " (delta " + (d.delta > 0 ? "+" : "") + d.delta + ", " + d.direction + ")",
    ...d,
    before_hash,
    after_hash,
    probe,
  };
}
