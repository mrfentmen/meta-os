# OC2B science cycles — cross-cycle comparison (cycles 1–5)

## Five-cycle table

| cycle | department | target | metric (observed vs expected) | verdict | level |
| 001 | chemistry | Delaney paper equation on archived 1,128-compound set (labs/delaney-xcheck) | RMSE 1.0994 vs 1.099 ±0.05 | MATCH | 3 |
| 002 | physics | drag-free projectile range, v0=25 m/s @30°, NIST g (compute.run_physics) | range 55.193759 m vs 55.1938 ±0.001 | MATCH | 3 |
| 003 | materials | rule-of-mixtures Al/Cu density, model-directed (compute.run_materials) | density 5.204000 vs 5.204 ±0.001 | MATCH | 3 |
| 004 | physics-math (shelf) | photon energy E=hc/λ at 500 nm, exact SI constants (shelf target) | E 3.972892e-19 J vs same ±1e-24 | MATCH | 3 |
| 005 | chemistry | held-out Delaney slice rows 31–130 vs paper training se=0.97 | RMSE 1.0752 vs 0.97 ±0.06 | DIFFER | 2 |

Every MATCH carries a bit-for-bit clean-directory re-run agreement
(comparison blocks in each score.md). The level-3 rungs rest on
pre-registered bands, frozen inputs, and independent reproduction —
no physical experiments, so nothing exceeds the automated ceiling.
Cycle-003's four model calls (Spark director, Wonder figure read, SAM
segmentation, Wonder critic) were each tried once and fell back to
documented OFFLINE templates with no retries; they changed nothing
(model/impact.md) at a totaled spend of $0.005358. All other cycles:
$0.00, no model calls.

## DIFFER honour roll

- cycle-005 DIFFER: held-out 100-compound slice RMSE 1.0752 vs the
  paper-anchored band [0.91, 1.03] around the paper's training
  se = 0.97 (miss by 0.0452). Stable under bit-for-bit re-run.
  First divergence: the paper's training error does not transfer to
  this compound set under the RDKit Wildman-Crippen cLogP method
  (paper used Daylight CLOGP on 2,874 training compounds); ranking
  transfers (slice R2 0.7432 vs paper 0.72) while calibration shifts.
  Filed at level 2 per the mismatch rule. Full analysis:
  labs/cycles/cycle-005/failure.md.
- No other DIFFERs and no failed reproductions across cycles 1–4.
  Nothing edited, nothing hidden.
