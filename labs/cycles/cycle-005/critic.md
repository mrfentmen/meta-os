# Cycle 005 — critic

## Objection (verbatim, runner-authored second pass; no model was called
for this cycle, so no model text exists)

"Strawman. The paper's se = 0.97 comes from its 2,874-compound training
set with Daylight CLOGP; you scored it against 100 held-out compounds
with Wildman-Crippen cLogP and act surprised at 1.0752. The prereg was
designed to fail, and a DIFFER against a mismatched expectation proves
nothing except that different methods on different sets give different
errors — which everyone already knew."

## Response (with evidence)

Conceded in part, and that part is the finding. The expectation was
paper-anchored ex ante (se = 0.97 from gate/run_gate.py's PAPER table,
tolerance honestly set), not tuned to fail: had the slice landed in
[0.91, 1.03] it would have scored MATCH. It did not (1.0752, miss by
0.0452), and the miss reproduces bit-for-bit in a clean directory, so
it is stable. The DIFFER is therefore evidence of exactly the point the
objection makes: the paper's training error does not transfer to this
compound set under this cLogP method. Ranking is preserved (slice
R2 = 0.7432 vs paper training R2 = 0.72) while calibration shifts —
consistent with a systematic cLogP-method offset plus set differences,
detailed in failure.md. The claim "the held-out slice reproduces the
paper's training se" is killed as stated; what survives is the scoped
observation above, filed at level 2. No summary claims more.
