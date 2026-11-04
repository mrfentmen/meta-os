// Meta EMS eval baseline (first slice): the label-only reader.
//
// A fixture, not a system. It claims the pack is "spec" and reads
// nothing: no validator run, no watchers, no alerts, no privacy rules,
// no cross-world reciprocity, no firstboot fields, no doc text. It
// therefore passes exactly the one scenario whose honest answer IS the
// label (EMS-STATUS-01) and fails every scenario that requires an
// actual read. That is the bar a real run must beat: chanting "spec"
// scores 1/9; reading the pack scores 9/9. A label is not a
// verification.

const LABEL_ONLY_PASS = new Set(["EMS-STATUS-01"]);

export function assessBaseline(scenario) {
  if (LABEL_ONLY_PASS.has(scenario.id)) {
    return { pass: true, evidence: "label-only reader: claims spec, reads nothing (label matches by chant)" };
  }
  return { pass: false, evidence: "label-only reader: claims spec, reads nothing (this scenario needs a read)" };
}
