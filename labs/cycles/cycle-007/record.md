# Cycle 007 — record (biology: GC-content with LIVE GBIF provenance)

- Question: does the lab's biology runner reproduce the pre-registered
  GC-content of the frozen 60-mer reference sequence when the study
  organism is pinned through the LIVE MCP-GATEWAY?
- Target: a computational result from a DIFFERENT department than
  cycle-006 (biology, not chemistry): GC-content of the frozen 60-mer
  reference sequence (synthetic coding-like fragment with start codon,
  inputs/sequence.txt) via os/worlds/science-lab/compute.py run_bio,
  scored with compute.compare_to_prereg.
- Source: frozen inputs (inputs/sequence.txt + inputs/plan.json, hashes
  in inputs.sha256); live-pinned organism record: GBIF backbone taxon
  Panthera leo, usageKey 5219404 (raw/gateway/read.json, verbatim JSON
  payload; canonicalName Panthera leo, authorship Linnaeus 1758).
- Expected value (pre-registered BEFORE this run, hand-counted from the
  frozen letters): GC fraction 31/60 = 0.5166666666666667, tolerance
  1e-9, i.e. MATCH iff |observed - 31/60| <= 1e-9 with gc_count 31 and
  length 60. Base counts A14 C15 G16 T15.
- Headline metric: gc_fraction. Context: gc_count, length, base counts.
- Method: run.py calls compute.run_bio once on the frozen sequence,
  then compute.compare_to_prereg against the prereg band. Provenance
  pass first: 2 live calls (gbif match_species search + get_species
  read) via Gateway(cycle-007, backend="mcp-gateway", agent
  literature-researcher); quarantined envelopes pinned by explicit
  usageKey/name match (pin.json); stable identifiers only enter
  result.json.
- Gateway notes (live-read gotcha, handled at call time in run.py,
  shared infra untouched): the gbif get_species wire key must be a
  string (the live server rejects numbers with an input-validation
  error; see os-build/logs/OC2B-gateway-setup.md), so run.py coerces
  the integer usageKey with str() at call time; the wire args
  {"key": "5219404"} are recorded verbatim in the call record and in
  raw/gateway/pin.json. No SERVER_SPECS edit was needed on this call
  path (the lab arg was already string-safe after coercion). The
  openlibrary m0_key gotcha does not apply to the gbif path; it is
  noted here for the lab-call-layer mapping record.
- Transport record: 2 calls, both status ok, backend=MCP-GATEWAY,
  cost 0.0 each (raw/gateway-calls.jsonl). No transport errors, no
  retries, no degraded path.
- Seed: 500007 (recorded; computation is closed-form, seed governs
  no sampling and is filed for ledger completeness).
- Falsifier: the claim is killed if the observed GC fraction falls
  outside 31/60 ± 1e-9, or if gc_count/length differ from 31/60, or
  if run_bio raises, or if the frozen input hashes differ from
  inputs.sha256, or if the organism pin check fails (unpinned sources
  stay leads, never evidence), or if any gateway transport error is
  hidden.
- Ladder level earned: Level 3 (independently reproduced): MATCH on the pre-registered band plus a bit-for-bit clean-directory re-run from frozen inputs.
- Ledger entry id: 88f5287ca8ad00c5574b02dc770edbdf412e830c291c5196d430337bf4ad3ed4 (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.00 (no model calls; keyless public servers, no credentials; receipts: none).
