# Cycle 005 — failure analysis (REQUIRED: this cycle DIFFERs)

Which input or step diverged first: the scored RMSE itself — the
paper-anchored expectation (training se = 0.97 on the paper's
2,874-compound set with Daylight CLOGP) does not describe the observed
error (RMSE = 1.0752) of the paper equation with RDKit
Wildman-Crippen cLogP on the 100-compound held-out slice
(rows 31-130). No earlier step diverged: the slice hash is frozen,
all 100 rows parsed, zero rows skipped, the equation and descriptors
are byte-identical to the cycle-001 implementation that MATCHed its
own repo-anchored band, and the clean-directory re-run agrees
bit-for-bit.

First-divergence decomposition (evidence, not excuse):
1. cLogP method shift (Daylight CLOGP 4.72 vs Wildman-Crippen) moves
   absolute predictions systematically; the paper's own fit and this
   rerun optimize/score different quantities.
2. Compound-set shift (2,874 training compounds vs 100 held-out
   processed compounds): slice R2 = 0.7432 vs paper training R2 = 0.72
   shows ranking transfers while calibration does not.
3. Slice variance: n = 100 widens the realized error vs a full-set fit.

Honour-roll entry: cycle-005 DIFFER, rmse observed=1.0752 vs paper
training se=0.97 +- 0.06. Filed at ladder level 2 (mismatch caps the
record). Nothing hidden, nothing retried.
