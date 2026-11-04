// Meta Nervus eval baseline (first slice): the label-only reader.
//
// A fixture, not a model. It claims every record set is "stub" and reads
// nothing: no counts, no hashes, no ramp, no receipt rows, no dose
// windows, no curve points, no gap text, no registry lane. It therefore
// passes exactly the two scenarios whose honest answer IS the label
// (NER-STUB-01, NER-STUB-02) and fails every scenario that requires an
// actual read. That is the bar a real run must beat: chanting "stub"
// scores 2/10; reading the records scores 10/10. A label is not a
// verification.

const LABEL_ONLY_PASS = new Set(["NER-STUB-01", "NER-STUB-02"]);

export function assessBaseline(scenario) {
  if (LABEL_ONLY_PASS.has(scenario.id)) {
    return { pass: true, evidence: "label-only reader: claims stub, reads nothing (label matches by chant)" };
  }
  return { pass: false, evidence: "label-only reader: claims stub, reads nothing (this scenario needs a read)" };
}
