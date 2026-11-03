# Cycle 001 — critic

## Objection (verbatim, runner-authored second pass; no model was called
for this cycle, so no model text exists)

"Your MATCH is circular. The expected RMSE 1.099 comes from a repo note
that was itself produced by this same code path (RDKit Wildman-Crippen
plus the paper equation), so observing 1.0994 proves the code is stable,
not that it is right. Worse, Wildman-Crippen is not the paper's Daylight
CLOGP, so even a perfect reproduction of the repo number says nothing
about Delaney (2004) itself. You checked arithmetic, not science."

## Response (with evidence)

Conceded in part, answered in part. Conceded: this cycle reproduces the
repo-recorded cross-check numbers, not the paper's training statistics;
the cLogP method difference (Daylight vs Wildman-Crippen) is real and is
stated in the record, the README, and the gate notes. It bounds the
claim: what MATCHed is "the from-scratch implementation of the
published equation reproduces the repo-recorded error on the archived
set". Not conceded: circularity of execution. The expectation was
written from labs/delaney-xcheck/README.md BEFORE running; the equation
coefficients come from the paper text (gate/run_gate.py PAPER table);
the 5-molecule hand-computed selfcheck in labs/delaney-xcheck/xcheck.py
passes 5/5 independently of this run; the input hash matches the archive
byte-for-byte; zero rows were skipped. Verdict MATCH stands at the
stated scope. No summary claims more.
