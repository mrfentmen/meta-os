# Cycle 007 — summary

The lab biology runner (compute.run_bio) gave GC-content 0.5166666667
(31/60) for the frozen 60-mer reference sequence, matching the
pre-registered hand-counted band 31/60 ± 1e-9 with exact counts
(A14 C15 G16 T15). The live provenance pass (2 gbif calls through the
MCP-GATEWAY backend, both ok, $0.00) pinned the study organism to the
GBIF backbone Panthera leo record (usageKey 5219404) by explicit
identifier match, with the string-key wire coercion handled at call
time; the taxon record stayed quarantined until that check passed. An
independent clean-directory re-run agreed bit-for-bit. The scored
claim is the arithmetic reproduction; the organism attribution is
provenance, not evidence for the number.
