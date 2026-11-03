# Cycle 006 — pre-registration (Delaney rerun + LIVE literature pass)

Pre-registered BEFORE any run. Parent commits this file (and
prereg.sha256) before any result file. Commit-SHA below is filled by
the parent at commit time; this working copy carries the placeholder.

- Plan: (a) literature pass through the LIVE MCP-GATEWAY backend:
  openalex search for the Delaney (2004) ESOL record, then a get_work
  read of the resolved OpenAlex work record, via the lab Gateway
  (backend "mcp-gateway", agent literature-researcher, budget 2 calls);
  pin the retrieved citation identifiers (OpenAlex id, DOI, title,
  year, venue, authors) as this cycle's source records. The gateway
  results are quarantined leads until pinned by the literature rules
  (explicit identifier match against the DOI/title stated here).
  (b) rerun the Delaney (2004) published equation
  logS = 0.16 - 0.63*cLogP - 0.0062*MWT + 0.066*RB - 0.74*AP
  with RDKit descriptors (Crippen MolLogP, Descriptors MolWt,
  Lipinski NumRotatableBonds, aromatic heavy atoms / heavy atoms)
  over every row of the frozen input copy of
  os/worlds/science-lab/gate/delaney/delaney-processed.csv.
- Work-id resolution note (disclosed, NOT a gateway call): the
  search-shaped openalex tool answers in plain text without work
  ids, and get_work rejects DOI forms (live server 404, recorded in
  os-build/logs/OC2B-gateway-setup.md), so the read locator
  https://openalex.org/W2076498053 was resolved from the public
  api.openalex.org DOI lookup before running; the search AND the read
  themselves go through the live gateway and are recorded there.
- Inputs: inputs/delaney-processed.csv (byte copy of the archived
  file); frozen hashes in inputs.sha256.
- Method: labs/cycles/cycle-006/run.py, deterministic, seed 500006.
  Gateway calls recorded to raw/gateway-calls.jsonl with
  backend=MCP-GATEWAY; payloads kept verbatim under raw/gateway/.
- Expected value: RMSE 1.099, tolerance 0.05 (MATCH iff [1.049, 1.149]).
  Source of expectation: the same repo-recorded band as cycle-001
  (labs/delaney-xcheck/README.md repo numbers R2 0.725 / RMSE 1.099 /
  MAE 0.844), recorded before running.
- Headline metric: RMSE (log units). Context: R2, MAE.
- Falsifier: the claim is killed if the observed RMSE falls outside
  [1.049, 1.149], or if the frozen input hash differs from the
  archived sha, or if any compound row is skipped silently, or if any
  gateway transport error is hidden (errors are recorded verbatim;
  one attempt per call; a failed literature pass is documented as a
  degraded path, never retried into silence).
- Plan-SHA256: see prereg.sha256 (sha256 of this file's bytes with
  the two trailer lines below set to their placeholder values).
- Commit-SHA: TO_BE_COMMITTED_BY_PARENT
