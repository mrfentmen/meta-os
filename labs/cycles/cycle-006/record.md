# Cycle 006 — record (Delaney rerun WITH the live literature pass)

- Question: does the Delaney (2004) published ESOL equation, implemented
  from scratch with RDKit Wildman-Crippen cLogP, reproduce the
  repo-recorded error statistics on the archived 1,128-compound set
  when the paper's identity is pinned through the LIVE MCP-GATEWAY?
- Target: the Delaney solubility cross-check under labs/delaney-xcheck
  (xcheck.py, selfcheck 5/5; README notes the expected systematic shift
  vs the paper's Daylight CLOGP), rerun of cycle-001 with the added
  live literature pass.
- Source: Delaney, J. S. (2004). ESOL: Estimating Aqueous Solubility
  Directly from Molecular Structure. J. Chem. Inf. Comput. Sci. 44(3),
  1000-1005. doi:10.1021/ci034243x. Archived compound set:
  os/worlds/science-lab/gate/delaney/delaney-processed.csv, sha256
  8c06a76f0c6487d29ab0f903e6a7a7139f189ab3c1178f59c8be8964602f189
  (gate/delaney/SOURCES.md). Live-pinned identifiers: OpenAlex
  https://openalex.org/W2076498053, DOI 10.1021/ci034243x, title ESOL,
  year 2004, venue J. Chem. Inf. Comput. Sci., author John S. Delaney
  (raw/gateway/read.json, verbatim text payload).
- Expected value (pre-registered, same repo-recorded band as cycle-001):
  RMSE 1.099, tolerance 0.05, i.e. MATCH iff observed RMSE in
  [1.049, 1.149]. Context values from the same repo note: R2 0.725,
  MAE 0.844 (reported alongside, scored as context, not pass/fail).
- Headline metric: RMSE of paper-equation predicted logS vs measured
  log solubility (mols per litre, log units).
- Method: run.py (deterministic; no fitting; paper coefficients
  0.16 / -0.63 / -0.0062 / +0.066 / -0.74 applied to RDKit
  descriptors MolWt, Crippen MolLogP, Lipinski RB, aromatic proportion).
  Literature pass first: 2 live calls (openalex search + get_work read)
  via Gateway(cycle-006, backend="mcp-gateway", agent
  literature-researcher); quarantined envelopes pinned by explicit
  DOI/title/year match (pin.json); stable identifiers only enter
  result.json (no volatile citation counts).
- Gateway notes (live-read gotchas, handled at call time in run.py,
  shared infra untouched): openalex get_work rejects DOI locators
  (live 404), so the read used the OpenAlex-id locator resolved from
  the public api.openalex.org DOI lookup BEFORE running (disclosed in
  prereg.md; the search and read themselves are live gateway calls).
  The gbif string-key gotcha does not apply to the openalex id map.
  No SERVER_SPECS edit was needed on this call path.
- Transport record: 2 calls, both status ok, backend=MCP-GATEWAY,
  cost 0.0 each (raw/gateway-calls.jsonl). No transport errors, no
  retries, no degraded path.
- Seed: 500006 (recorded; computation is closed-form, seed governs
  no sampling and is filed for ledger completeness).
- Falsifier: the claim is killed if the observed RMSE falls outside
  [1.049, 1.149], or if the frozen input hash differs from the
  archived sha, or if any compound row is skipped silently (every
  skipped row must be named in the raw output), or if the literature
  pin check fails (unpinned sources stay leads, never evidence), or
  if any gateway transport error is hidden.
- Ladder level earned: Level 3 (independently reproduced): MATCH on the pre-registered band plus a bit-for-bit clean-directory re-run from frozen inputs.
- Ledger entry id: fba607902198c2fdb9980eb332dfaa473417c4ace23e5369f37516d71f1a15de (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.00 (no model calls; keyless public servers, no credentials; receipts: none).
