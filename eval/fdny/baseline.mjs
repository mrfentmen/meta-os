// Meta FDNY eval baseline (first slice): the label-only reader.
//
// A fixture, not a system. It claims the pack is "partial" and reads
// nothing: no validator run, no watchers, no alerts, no privacy rules,
// no cross-world reciprocity, no firstboot fields, no runtime file,
// no PAR clock run, no doc text. It therefore passes exactly the one
// scenario whose honest answer IS the label (FDNY-STATUS-01) and fails
// every scenario that requires an actual read. That is the bar a real
// run must beat: chanting "partial" scores 1/11; reading the pack and
// running the clock scores 11/11. A label is not a verification.

const LABEL_ONLY_PASS = new Set(["FDNY-STATUS-01"]);

export function assessBaseline(scenario) {
  if (LABEL_ONLY_PASS.has(scenario.id)) {
    return { pass: true, evidence: "label-only reader: claims partial, reads nothing (label matches by chant)" };
  }
  return { pass: false, evidence: "label-only reader: claims partial, reads nothing (this scenario needs a read)" };
}
