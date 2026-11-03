# Cycle 007 — pre-registration (biology: GC-content + LIVE GBIF provenance)

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: (a) literature/provenance pass through the LIVE MCP-GATEWAY
  backend: gbif match_species search for the study organism
  "Panthera leo", then a get_species read of the matched usageKey,
  via the lab Gateway (backend "mcp-gateway", agent
  literature-researcher, budget 2 calls); pin the retrieved taxon
  identifiers (usageKey, scientific name, rank, status) as this
  cycle's organism source records. The gateway results are
  quarantined leads until pinned by the literature rules (explicit
  identifier match against the usageKey/name stated here).
  (b) compute the GC-content of the frozen 60-mer reference sequence
  (inputs/sequence.txt, synthetic coding-like fragment with start
  codon, attributed to the pinned study organism) via the lab
  compute module run_bio, and score with compute.compare_to_prereg.
- Live-read gotcha handled at call time (NOT in shared infra): the
  gbif get_species wire key must be a string (live server rejects
  numbers; see os-build/logs/OC2B-gateway-setup.md), so run.py coerces
  the integer usageKey to str at call time and records the wire args
  verbatim. Documented here and in record.md.
- Inputs: inputs/sequence.txt (60 nt, frozen); inputs/plan.json
  (sequence + organism + prereg band); frozen hashes in inputs.sha256.
- Method: labs/cycles/cycle-007/run.py, deterministic, seed 500007.
  Gateway calls recorded to raw/gateway-calls.jsonl with
  backend=MCP-GATEWAY; payloads kept verbatim under raw/gateway/.
- Expected value (hand-counted BEFORE this run): GC fraction 31/60 =
  0.5166666666666667, tolerance 1e-9 (MATCH iff |observed - 31/60|
  <= 1e-9 with gc_count 31 and length 60). Base counts: A14 C15 G16
  T15. Source of expectation: direct count of the frozen input
  letters, recorded before running.
- Headline metric: gc_fraction. Context: gc_count, length.
- Falsifier: the claim is killed if the observed GC fraction falls
  outside 31/60 ± 1e-9, or if gc_count/length differ from 31/60, or
  if run_bio raises, or if the frozen input hashes differ from
  inputs.sha256, or if any gateway transport error is hidden (errors
  recorded verbatim; one attempt per call; a failed provenance pass
  is documented as a degraded path, never retried into silence).
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
